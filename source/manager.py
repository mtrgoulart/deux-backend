from .client import OKXClient
from log.log import general_logger  # Importa o logger configurado
import threading
import time
from .pp import ConfigLoader, Market, WebhookData, Operations
from datetime import datetime
import re
from .context import get_db_connection
from threading import Event
from .exchange_interface import get_exchange_interface
from decimal import Decimal

class IntervalHandler:
    def __init__(self, interval, symbol, side, simultaneus_operation=1):
        self.interval = float(interval)
        self.symbol = symbol
        self.side = side
        self.operations = None
        self.simultaneus_operation=simultaneus_operation

        # Instancia o Operations com conexão
        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

    def get_last_operations(self,limit):
        #general_logger.info(f"Fetching last {self.simultaneus_operation} operations from DB for symbol: {self.symbol}")
        return self.operations.get_last_operations_from_db(self.symbol, limit)


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
                if last_operation:
                    if last_operation["side"] != self.side: 
                        return True
                    else:
                        valid_interval = self._interval_logic(last_operation["date"])
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
    def __init__(self, market_manager, condition_handler, interval, symbol, side, percent,exchange_id,user_id,api_key,instance_id):
        self.market_manager = market_manager
        self.condition_handler = condition_handler
        self.interval = interval
        self.symbol = symbol
        self.side = side
        self.percent = percent
        self.webhook_data_manager = None
        self.instance_id=instance_id

        self.stop_event = Event()
        self._is_running = False

        self.exchange_interface = get_exchange_interface(exchange_id, user_id, api_key)

        # Instancia o WebhookData com conexão
        with get_db_connection() as db_client:
            self.webhook_data_manager = WebhookData(db_client)

        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

        general_logger.info(f"OperationHandler initialized for symbol: {self.symbol}, side: {self.side}")

    def start(self, start_date):
        general_logger.info(f"Starting operation at {start_date} for symbol: {self.symbol}, {self.side}")
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, args=(start_date,))
        self.thread.start()
        self._is_running = True

    def stop(self):
        general_logger.info(f"Stopping operation for: {self.side} - {self.symbol}")
        self.stop_event.set()  # Sinaliza a parada
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()  # Aguarda a thread terminar
        self._is_running = False

    def run(self, start_date):
        while not self.stop_event.is_set():
            data = self.webhook_data_manager.get_market_objects_as_models(self.symbol, self.side, start_date)
            operation_performed = False
            if self.check_conditions(data) and len(data) >= 1:
                general_logger.info(f'**Filled Condition** Performing Operation...')
                last_market_data = data[-1]
                market_to_operation = Market(
                    symbol=last_market_data["symbol"],
                    order_type='market',
                    side=last_market_data["side"]
                )
                execution_price, execution_size, execution_status = self.perform_operation(market_to_operation)
                market_to_operation.size = execution_size
                general_logger.info(f'Operation Executed on: symbol:{last_market_data["symbol"]} price:{execution_price}')
                operation_id,operation_log = self.operations.save_operation_to_db(
                    market_to_operation.to_dict(), price=execution_price, status=execution_status, instance_id=self.instance_id
                )
                if operation_log:
                    general_logger.error(operation_log)
                self.update_webhook_operation(data, operation_id)
                operation_performed = True
                time.sleep(2)
                self._is_running = False

            if operation_performed:
                break

            time.sleep(3)

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

    def perform_operation(self, market_data):
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
                print("Erro: ordem não foi executada.")
                return None, percent_size, 'erro'

            execution_price = self.exchange_interface.get_fill_price(order_response)

            if execution_price is not None:
                return execution_price, percent_size, 'realizada'
            else:
                print("Erro: Preço de execução não encontrado.")
                return None, percent_size, 'erro'
        else:
            print("Operação não realizada, pois o percent_size é zero.")
            return None, percent_size, 'percent_size=0'

    def get_execution_price(self, client,symbol, order_id):
        # Consulta o status da ordem usando o 'ordId'
        order_status = client.get_order_status(symbol, order_id)

        # Supondo que a resposta da API contenha 'fillPx', que é o preço de execução
        execution_price = float(order_status['data'][0].get('fillPx', 0))

        if execution_price == 0:
            raise ValueError("Preço de execução não encontrado ou inválido.")

        return execution_price

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
