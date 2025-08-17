from log.log import general_logger  # Importa o logger configurado
import time
from .pp import Market, WebhookData, Operations
from datetime import datetime
import re
from .context import get_db_connection
from .exchange_interface import get_exchange_interface
from decimal import Decimal
from .celery_client import get_client
import uuid

class IntervalHandler:
    def __init__(self, interval, symbol, side,instance_id, simultaneus_operation=1):
        self.interval = float(interval)
        self.symbol = symbol
        self.side = side
        self.operations = None
        self.instance_id=instance_id
        self.simultaneus_operation=simultaneus_operation

        # Instancia o Operations com conexão
        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

    def get_last_operations(self,limit):
        #general_logger.info(f"Fetching last {self.simultaneus_operation} operations from DB for symbol: {self.symbol}")
        return self.operations.get_last_operations_from_db(self.instance_id, limit)


    def check_interval(self):
        last_operations = self.get_last_operations(limit=self.simultaneus_operation)

        if last_operations:
            # Verifica se todas as operações possuem o mesmo `side`
            same_side = all(op["side"] == self.side for op in last_operations)
            if same_side:
                return False
            else:
                # Obtém a última operação
                last_operation = last_operations[0] if len(last_operations) > 0 else None
                #general_logger.info(f'{last_operation,{self.side}}')
                if last_operation:
                    if last_operation["side"] != self.side: 
                        return True
                    else:
                        valid_interval = self._interval_logic(last_operation["date"])
                        general_logger.info(f'interval {valid_interval}')
                        return valid_interval
                else:
                    return True
        else:
            return True

    def get_application_interval(self, last_operation_time):
        if last_operation_time:
            current_time = datetime.now()
            return (current_time - last_operation_time).total_seconds() / 60
        return None

    def _interval_logic(self, last_operation_time):
        last_operation_interval = self.get_application_interval(last_operation_time)
        general_logger.info(f"Elapsed interval: {last_operation_interval} minutes")
        if self.interval == 0:
            return True
        else:
            return last_operation_interval >= self.interval

class OperationHandler:
    def __init__(self, market_manager, condition_limit, interval, symbol, side, percent,exchange_id,user_id,api_key,instance_id,share_id=None):
        self.market_manager = market_manager
        self.condition_handler = conditionHandler(condition_limit)
        self.interval = interval
        self.symbol = symbol
        self.side = side
        self.percent = percent
        self.webhook_data_manager = None
        self.instance_id=instance_id
        self.api_key=api_key
        self.share_id=share_id
        self.user_id=user_id
        self.exchange_id=exchange_id

        self.exchange_interface = get_exchange_interface(exchange_id, user_id, api_key)

        # Instancia o WebhookData com conexão
        with get_db_connection() as db_client:
            self.webhook_data_manager = WebhookData(db_client)

        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

    def execute_condition(self, start_date):
        # 1. Crie um ID único para esta execução. Facilita o rastreamento.
        execution_id = uuid.uuid4().hex[:8]
        
        # Crie um prefixo para os logs desta execução
        log_prefix = f"[ExecID: {execution_id}] [Instance: {self.instance_id}] [Symbol: {self.symbol}]"

        general_logger.info(f"{log_prefix} Iniciando execução da condição.")
        
        try:
            data = self.webhook_data_manager.get_market_objects_as_models(
                self.instance_id, self.symbol, self.side, start_date
            )
            # Use DEBUG para logs com muitos dados, que você só precisa ver quando está depurando.
            general_logger.debug(f"{log_prefix} Dados de mercado recebidos: {data}")

            conditions_met = self.check_conditions(data)
            data_is_sufficient = len(data) >= 1

            # 2. Verificação explícita das condições para logs mais claros.
            if conditions_met and data_is_sufficient:
                general_logger.info(f"{log_prefix} Condições atendidas. Executando operação.")

                operation_data= {
                    'user_id':self.user_id,
                    'api_key':self.api_key,
                    'exchange_id':self.exchange_id,
                    'perc_balance_operation':self.percent,
                    'symbol':self.symbol,
                    'side':self.side,
                    'instance_id':self.instance_id
                }
                
                # --- Etapa: Realizar Operação ---
                async_result = get_client().send_task(
                    "trade.execute_operation",
                    kwargs={"data": operation_data},
                    queue="ops"
                )

                operation_task_id = async_result.id
                               
                # --- Etapa: Enviar Tarefa de Compartilhamento ---
                if self.share_id:
                    try:
                        general_logger.info(f"{log_prefix} Enviando tarefa de compartilhamento para share_id={self.share_id}...")
                        get_client().send_task(
                            "process_sharing_operations",
                            kwargs={"data": {
                                "share_id": self.share_id,
                                "user_id": self.user_id,
                                "side": self.side,
                                "symbol": self.symbol
                            }},
                            queue="sharing"
                        )
                        general_logger.info(f"{log_prefix} Tarefa de compartilhamento enviada com sucesso.")
                    except Exception as e:
                        # 5. Logue o erro de forma mais estruturada.
                        general_logger.error(f"{log_prefix} Falha ao enviar tarefa de compartilhamento. Erro: {e}", exc_info=True)

                # --- Etapa: Atualizar Webhook ---
                self.update_webhook_operation(data, operation_task_id)

                return {
                "status": "success",
                "operation_task_id": operation_task_id
                }

            else: 
                # 6. Log muito mais específico sobre o motivo da falha.
                reason = ""
                if not conditions_met:
                    reason += "check_conditions() retornou False. "
                if not data_is_sufficient:
                    reason += f"Não há dados suficientes (len(data) = {len(data)}, esperado >= 1). "
                return {
                "status": "insuficient condition",
                "reason": reason
                }

        except Exception as e:
            # Captura qualquer erro inesperado no processo
            general_logger.error(f"{log_prefix} Ocorreu um erro inesperado na execução da condição. Erro: {e}", exc_info=True)
            return {
                "status": "failed",
                "reason": reason.strip()
            }
        finally:
            # 7. Garante que o fim da execução seja sempre logado.
            general_logger.info(f"{log_prefix} Finalizando execução da condição.")

    def update_webhook_operation(self, filtered_data,operation_task_id):

        for market_object in filtered_data:
            webhook_id=market_object["id"]
            try:
                self.webhook_data_manager.update_market_object_at_index(webhook_id, str(operation_task_id))
                general_logger.info(f"Updated task operation ID {operation_task_id} for object {market_object['id']}")
            except Exception as e:
                general_logger.error(f"Error updating object {market_object['id']}: {e}")

    def check_conditions(self, data):
        return self.condition_handler.check_condition(data)

class conditionHandler:
    def __init__(self, length_condition):
        self.length_condition = length_condition

    def check_condition(self, market_list):
        # Dicionário para armazenar os símbolos e tipos com suas estratégias correspondentes
        symbol_type_dict = {}

        for market in market_list:
            key = (market["symbol"], market["side"])  # Chave combinada de symbol e side

            if key not in symbol_type_dict:
                symbol_type_dict[key] = []  # Inicializa como lista

            # Verifica se a estratégia (indicator) já está na lista, se não estiver, adiciona
            if market["indicator"] not in symbol_type_dict[key]:
                symbol_type_dict[key].append(market["indicator"])

        # Agora verificamos se há pelo menos duas estratégias diferentes para cada combinação de symbol e side
        for key, strategies in symbol_type_dict.items():
            if len(strategies) < int(self.length_condition):
                return False  # Se alguma combinação não tiver pelo menos duas estratégias diferentes, retorna False

        return True # Se todas as combinações tiverem duas ou mais estratégias diferentes, retorna True
