from log.log import general_logger
from .client import OKXClient, OKXDemoClient, BinanceClient, BinanceDemoClient, BingXClient
from .context import get_db_connection
from .dbmanager import load_query
import json
import importlib
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exchange_classes_path = os.path.join(BASE_DIR, 'exchange_classes.json')

class ExchangeInterface:
    def __init__(self, exchange_id: int, user_id: int, api_key: int):
        self.exchange_id = exchange_id
        self.user_id = user_id
        self.api_key = api_key
        self.credentials = self.load_credentials()

    def load_credentials(self):
        try:
            query = load_query('select_api_credentials.sql')
            with get_db_connection() as db_client:
                result = db_client.fetch_data(query, (self.api_key, self.user_id))
            if not result:
                raise ValueError(f"Credenciais não encontradas para api_key {self.api_key} e user_id {self.user_id}.")
            return result[0][0]
        except Exception as e:
            general_logger.error(f"Erro ao carregar credenciais: {e}")
            raise ValueError(f"Falha ao carregar credenciais: {e}")

    def create_client(self):
        raise NotImplementedError

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        raise NotImplementedError

    def get_fill_price(self, order_id):
        raise NotImplementedError

    def cancel_order(self, symbol, order):
        raise NotImplementedError

    def get_open_order(self, symbol):
        raise NotImplementedError

    def get_order_status(self, symbol, order_id):
        raise NotImplementedError

    def get_last_trade(self, symbol):
        raise NotImplementedError

    def get_current_price(self, symbol):
        raise NotImplementedError

    def get_balance(self, ccy=None):
        raise NotImplementedError

    def get_order_execution_price(self, symbol, order_id):
        raise NotImplementedError

class OKXRealInterface(ExchangeInterface):
    def __init__(self, exchange_id, user_id, api_key):
        super().__init__(exchange_id, user_id, api_key)
        self.okx_client = self.create_client()

    def create_client(self):
        return OKXClient(self.credentials)

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        return self.okx_client.place_order(symbol, side, order_type, size, currency, price)

    def get_fill_price(self, order_id):
        return self.okx_client.wait_for_fill_price(order_id)

    def cancel_order(self, symbol, order):
        return self.okx_client.cancel_order(symbol, order)

    def get_open_order(self, symbol):
        return self.okx_client.get_open_orders(symbol)

    def get_order_status(self, symbol, order_id):
        return self.okx_client.get_order_status(symbol, order_id)

    def get_last_trade(self, symbol):
        return self.okx_client.get_last_trade(symbol)

    def get_current_price(self, symbol):
        return self.okx_client.get_current_price(symbol)

    def get_balance(self, ccy=None):
        return self.okx_client.get_balance(ccy)

    def get_order_execution_price(self, symbol, order_id):
        return self.okx_client.get_order_execution_price(symbol, order_id)

class OKXDemoInterface(OKXRealInterface):
    def create_client(self):
        return OKXDemoClient(self.credentials)

class BinanceRealInterface(ExchangeInterface):
    def __init__(self, exchange_id, user_id, api_key):
        super().__init__(exchange_id, user_id, api_key)
        self.binance_client = self.create_client()

    def create_client(self):
        return BinanceClient(self.credentials)

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        return self.binance_client.place_order(symbol, side, order_type, size, currency, price)

    def get_fill_price(self, order_id, symbol):
        return self.binance_client.wait_for_fill_price(order_id, symbol)

    def cancel_order(self, symbol, order):
        return self.binance_client.cancel_order(symbol, order)

    def get_open_order(self, symbol):
        return self.binance_client.get_open_orders(symbol)

    def get_order_status(self, symbol, order_id):
        return self.binance_client.get_order_status(symbol, order_id)

    def get_last_trade(self, symbol):
        return self.binance_client.get_last_trade(symbol)

    def get_current_price(self, symbol):
        return self.binance_client.get_current_price(symbol)

    def get_balance(self, ccy=None):
        return self.binance_client.get_balance(ccy)

    def get_order_execution_price(self, symbol, order_id):
        return self.binance_client.wait_for_fill_price(order_id, symbol)

class BinanceDemoInterface(BinanceRealInterface):
    def create_client(self):
        return BinanceDemoClient(self.credentials)

class BingXInterface(ExchangeInterface):
    def __init__(self, exchange_id, user_id, api_key):
        super().__init__(exchange_id, user_id, api_key)
        self.bingx_client = self.create_client()

    def create_client(self):
        return BingXClient(self.credentials)

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        return self.bingx_client.place_order(symbol, side, order_type, size, currency, price)

    def get_fill_price(self, order_id):
        raise NotImplementedError("Método requer símbolo também.")

    def cancel_order(self, symbol, order):
        return self.bingx_client.cancel_order(symbol, order)

    def get_open_order(self, symbol):
        return self.bingx_client.get_open_orders(symbol)

    def get_order_status(self, symbol, order_id):
        return self.bingx_client.get_order_status(symbol, order_id)

    def get_last_trade(self, symbol):
        return self.bingx_client.get_last_trade(symbol)

    def get_current_price(self, symbol):
        response = self.bingx_client.get_current_price(symbol)
        if response and 'data' in response and isinstance(response['data'], dict):
            return float(response['data'].get('price', 0.0))
        return None

    def get_balance(self, ccy=None):
        response = self.bingx_client.get_balance()
        if response and 'data' in response and isinstance(response['data'], list):
            if ccy:
                for item in response['data']:
                    if item.get('asset') == ccy:
                        return float(item.get('free', 0))
            else:
                return response['data']
        return 0.0

    def get_order_execution_price(self, symbol, order_id):
        status = self.get_order_status(symbol, order_id)
        if status and 'data' in status and isinstance(status['data'], dict):
            return float(status['data'].get('price', 0.0))
        return 0.0

def get_exchange_interface(exchange_id: int, user_id: int, api_key: int):
    try:
        query = load_query('select_exchange_by_id.sql')
        with get_db_connection() as db_client:
            result = db_client.fetch_data(query, (exchange_id,))
            if not result:
                raise ValueError(f"Exchange ID {exchange_id} não encontrada.")
            exchange_id, name, _, _ = result[0]

        with open(exchange_classes_path, 'r') as json_file:
            exchange_classes = json.load(json_file)

        class_path = exchange_classes.get(str(exchange_id))
        if not class_path:
            raise ValueError(f"Interface para Exchange ID {exchange_id} não mapeada.")

        module_name, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        exchange_class = getattr(module, class_name)

        return exchange_class(exchange_id, user_id, api_key)
    except Exception as e:
        raise ValueError(f"Erro ao inicializar a interface para Exchange ID {exchange_id}: {e}")
