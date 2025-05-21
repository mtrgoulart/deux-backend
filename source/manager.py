from log.log import general_logger  # Importa o logger configurado
import time
from .pp import Market, WebhookData, Operations
from datetime import datetime
import re
from .context import get_db_connection
from .exchange_interface import get_exchange_interface
from decimal import Decimal
from .celery_client import get_client

class TPSLHandler:
    def __init__(self, instance_id, user_id, api_key, symbol, exchange_id, side, trailing_check_interval=None, trailing_percentage=None):
        self.instance_id = instance_id
        self.api_key = api_key
        self.symbol = symbol
        self.user_id = user_id
        self.side = side
        self.exchange_interface = get_exchange_interface(exchange_id, self.user_id, api_key)

        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

        # Definir um valor mínimo único para todas as ordens
        self.min_order_size = 0.00001  # Pode ser ajustado conforme necessário

        # Parâmetros do trailing stop
        self.trailing_check_interval = trailing_check_interval  # tempo (em segundos) entre verificações
        self.trailing_percentage = trailing_percentage          # percentual para atualização do stop loss
        self.last_trailing_check = 0
        self.trailing_high = None

    def get_last_operations(self, limit):
        # Retorna as últimas operações do ativo
        return self.operations.get_last_operations_from_db(self.symbol, limit)

    def check_tp_sl_conditions(self):
        """
        Verifica se o preço atual atingiu o TP, SL ou se é necessário atualizar o trailing stop.
        """
        try:
            # Obtém os valores de TP e SL salvos no banco
            tp_price, sl_price, _, _ = self.operations.get_tp_sl_prices(self.instance_id, self.api_key)
            if tp_price is None and sl_price is None:
                return
            
            last_operations = self.get_last_operations(1)
            last_operation = last_operations[0]
            if last_operation["side"] != self.side:
                self.operations.update_tp_sl_status(self.instance_id, self.api_key, "cancelled", "cancelled")
                return

            # Obtém o preço atual do símbolo
            current_price = self.get_current_price()
            if current_price is None:
                general_logger.error(f"Erro ao obter preço atual para {self.symbol}")
                return

            # Lógica de trailing stop somente se o stop loss estiver definido
            if sl_price is not None and self.trailing_percentage is not None and self.trailing_check_interval is not None:
                # Inicializa o maior preço se ainda não foi definido
                if self.trailing_high is None:
                    self.trailing_high = current_price

                current_time = time.time()
                if current_time - self.last_trailing_check >= self.trailing_check_interval:
                    self.last_trailing_check = current_time
                    # Se o preço atual ultrapassar o máximo registrado, atualiza o trailing high
                    if current_price > self.trailing_high:
                        self.trailing_high = current_price
                        # Calcula o novo stop loss com base no percentual definido
                        new_sl = self.trailing_high * (1 - self.trailing_percentage)
                        # Atualiza o stop loss se o novo valor for maior que o atual
                        if new_sl > sl_price:
                            sl_price = new_sl
                            self.operations.update_sl_price(self.instance_id, self.api_key, new_sl)
                            general_logger.info(f"Trailing stop atualizado para {new_sl} para {self.symbol}")

            # Verifica condição de Take Profit
            if tp_price is not None and current_price >= tp_price:
                general_logger.info(f"Take Profit atingido para {self.symbol} a {current_price}. Executando venda...")
                tp_execution = self.execute_sell_order()
                if tp_execution:
                    general_logger.info(f"Take Profit executado com sucesso para {self.symbol}. Atualizando banco...")
                    self.operations.update_tp_sl_status(self.instance_id, self.api_key, "filled", "tp_executed")

            # Verifica condição de Stop Loss
            elif sl_price is not None and current_price <= sl_price:
                general_logger.info(f"Stop Loss atingido para {self.symbol} a {current_price}. Executando venda...")
                sl_execution = self.execute_sell_order()
                if sl_execution:
                    general_logger.info(f"Stop Loss executado com sucesso para {self.symbol}. Atualizando banco...")
                    self.operations.update_tp_sl_status(self.instance_id, self.api_key, "sl_executed", "filled")

        except Exception as e:
            general_logger.error(f"Erro ao verificar condições de TP/SL: {e}")


    def get_current_price(self):
        """
        Obtém o preço atual do ativo na exchange.
        """
        try:
            return self.exchange_interface.get_current_price(self.symbol)
        except Exception as e:
            general_logger.error(f"Erro ao obter preço atual da exchange: {e}")
            return None

    def execute_sell_order(self):
        """
        Executa uma ordem de venda para fechar a posição, garantindo que o tamanho da ordem não seja muito baixo.
        """
        try:
            match = re.match(r"^([^-]+)-([^-]+)$", self.symbol)
            if not match:
                raise ValueError(f"O símbolo '{self.symbol}' não está no formato esperado 'parte1-parte2'.")

            ccy_symbol, _ = match.groups()
            ccy = ccy_symbol

            actual_size = self.exchange_interface.get_balance(ccy)

            # Validação do tamanho mínimo da ordem
            if actual_size < self.min_order_size:
                general_logger.warning(
                    f"Tamanho da ordem ({actual_size}) é menor que o mínimo permitido ({self.min_order_size}). "
                    f"Simulando execução para {self.symbol}."
                )
                return True  # Simula a execução e segue o fluxo normalmente

            order_response = self.exchange_interface.place_order(
                symbol=self.symbol,
                side="sell",
                order_type="market",
                size=actual_size,
                currency=ccy,
            )

            if order_response:
                general_logger.info(f"Ordem de venda executada para {self.symbol}")
                return True
            else:
                general_logger.error(f"Erro ao executar ordem de venda para {self.symbol}")
                return False
        except Exception as e:
            general_logger.error(f"Erro ao executar ordem de venda: {e}")
            return False

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
        return self.operations.get_last_operations_from_db(self.instance_id,self.symbol, limit)


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
                general_logger.info(f'{last_operation,{self.side}}')
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
    def __init__(self, market_manager, condition_limit, interval, symbol, side, percent,exchange_id,user_id,api_key,instance_id,tp=None,sl=None,share_id=None):
        self.market_manager = market_manager
        self.condition_handler = conditionHandler(condition_limit)
        self.interval = interval
        self.symbol = symbol
        self.side = side
        self.percent = percent
        self.webhook_data_manager = None
        self.instance_id=instance_id
        self.api_key=api_key
        self.perc_tp=tp
        self.perc_sl=sl
        self.share_id=share_id
        self.user_id=user_id

        self.exchange_interface = get_exchange_interface(exchange_id, user_id, api_key)

        # Instancia o WebhookData com conexão
        with get_db_connection() as db_client:
            self.webhook_data_manager = WebhookData(db_client)

        with get_db_connection() as db_client:
            self.operations = Operations(db_client)


    def calculate_tp_sl(self, price, perc_tp, perc_sl):
        """
        Calcula os valores de Take Profit (TP) e Stop Loss (SL) com base no preço de execução e nos percentuais fornecidos.

        :param price: Preço de execução da ordem.
        :param perc_tp: Percentual para calcular o Take Profit.
        :param perc_sl: Percentual para calcular o Stop Loss.
        :return: Tuple contendo os valores calculados de TP e SL.
        """
        if price is None:
            general_logger.error("Preço de execução é None. Não foi possível calcular TP/SL.")
            return None, None

        try:
            price = Decimal(str(price))
            perc_tp = Decimal(str(perc_tp)) if perc_tp not in [None, "", 0] else None
            perc_sl = Decimal(str(perc_sl)) if perc_sl not in [None, "", 0] else None

            # Calcular TP e SL apenas se os percentuais forem válidos
            tp = price * (Decimal('1') + (perc_tp / Decimal('100'))) if perc_tp is not None else None
            sl = price * (Decimal('1') - (perc_sl / Decimal('100'))) if perc_sl is not None else None
            return tp, sl

        except Exception as e:
            general_logger.error(f"Erro ao calcular TP/SL: {e}")
            return None, None
        
    def execute_condition(self,start_date):
        data = self.webhook_data_manager.get_market_objects_as_models(self.instance_id,self.symbol, self.side, start_date)
        #general_logger.info(f'Entrando na execucao da condicao: {data}')
        if self.check_conditions(data) and len(data) >= 1:
            general_logger.info(f'**Filled Condition Performing Operation...**')
            last_market_data = data[-1]
            market_to_operation = Market(
                symbol=self.symbol,
                order_type='market',
                side=self.side
            )
            execution_price, execution_size, execution_status,tp_price,sl_price = self.perform_operation(market_to_operation,self.perc_tp,self.perc_sl)
            if self.share_id and operation_id:
                try:
                    get_client().send_task(
                        "process_sharing_operations",
                        kwargs={"data":{
                            "share_id": self.share_id,
                            "user_id": self.user_id,
                            "side":self.side,
                            "symbol":self.symbol
                            }
                        }
                    )
                    general_logger.info(f"Tarefa de compartilhamento enviada com sucesso para share_id={self.share_id}")
                except Exception as e:
                    general_logger.error(f"Erro ao enviar task de compartilhamento: {e}")
            market_to_operation.size = execution_size
            general_logger.info(f'Operation Executed on: symbol:{last_market_data["symbol"]} price:{execution_price}')
            operation_id,operation_log = self.operations.save_operation_to_db(
                market_to_operation.to_dict(), price=execution_price, status=execution_status, instance_id=self.instance_id
            )
            if tp_price and sl_price:
                self.operations.save_tp_sl_to_db(instance_id=self.instance_id,api_key=self.api_key,tp_price=tp_price,sl_price=sl_price,operation_id=operation_id)
                general_logger.info(f'TP on {tp_price} and SL on {sl_price}')
            
            if operation_log:
                general_logger.error(operation_log)
            self.update_webhook_operation(data, operation_id)

    def update_webhook_operation(self, filtered_data, operation_id):
        if operation_id is None:
            operation_id = 0

        for market_object in filtered_data:
            new_data = {
                "symbol": market_object["symbol"],
                "side": market_object["side"],
                "indicator": market_object.get("indicator"),
                "operation": operation_id
            }
            try:
                self.webhook_data_manager.update_market_object_at_index(market_object["id"], new_data)
                general_logger.info(f"Updated operation ID {operation_id} for object {market_object['id']}")
            except Exception as e:
                general_logger.error(f"Error updating object {market_object['id']}: {e}")

    def check_conditions(self, data):
        return self.condition_handler.check_condition(data)

    def perform_operation(self, market_data, perc_tp=None, perc_sl=None):
        match = re.match(r"^([^-]+)-([^-]+)$", market_data.symbol)
        if not match:
            raise ValueError(f"O símbolo '{market_data.symbol}' não está no formato esperado 'parte1-parte2'.")

        base_currency, quote_currency = match.groups()
        ccy = quote_currency if market_data.side == 'buy' else base_currency
        try:
            actual_size = self.exchange_interface.get_balance(ccy)
        except Exception as e:
            raise ValueError(f'Erro ao obter o saldo: {e}')

        if not isinstance(actual_size, (int, float, Decimal)):
            raise ValueError(f"Erro no tipo de valor do saldo: {actual_size}")

        # Converte explicitamente `actual_size` para float se for Decimal
        percent_size = float(actual_size) * float(self.percent)

        general_logger.info(f'Balance: {percent_size} {ccy}')

        if percent_size != 0:
            order_response = self.exchange_interface.place_order(
                symbol=market_data.symbol,
                side=market_data.side,
                order_type=market_data.order_type,
                size=percent_size,
                currency=ccy,
                price=market_data.price
            )

            general_logger.info(f'Ordem enviada, aguardando execução....')

            if not order_response:
                general_logger.error("Erro: ordem não foi executada.")
                return None, percent_size, 'erro', None, None

            execution_price = self.exchange_interface.get_fill_price(order_response)
            tp, sl = None, None

            if execution_price is not None:
                if perc_tp is not None or perc_sl is not None:
                    tp, sl = self.calculate_tp_sl(execution_price, perc_tp, perc_sl)

                return execution_price, percent_size, 'realizada', tp, sl
            else:
                general_logger.error("Erro: Preço de execução não encontrado.")
                return None, percent_size, 'erro', None, None
        else:
            general_logger.warning("Operação não realizada, pois o percent_size é zero.")
            return None, percent_size, 'percent_size=0', None, None

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
