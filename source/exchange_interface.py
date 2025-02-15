from log.log import general_logger  # Importa o logger configurado
from .client import OKXClient, BinanceClient
from .context import get_db_connection
from .dbmanager import load_query
import json
import importlib

class ExchangeInterface:
    def __init__(self, exchange_id: int, user_id: int, api_key: int):
        """
        Classe base para interfaces de comunicação com exchanges.
        :param exchange_id: ID da exchange.
        :param user_id: ID do usuário.
        :param api_key: ID da API Key.
        """
        self.exchange_id = exchange_id
        self.user_id = user_id
        self.api_key = api_key
        self.credentials = self.load_credentials()

    def load_credentials(self):
        """
        Carrega as credenciais da API do banco de dados com base no user_id e api_key.
        """
        try:
            query = load_query('select_api_credentials.sql')  # Criação desta query é necessária
            with get_db_connection() as db_client:
                result = db_client.fetch_data(query, (self.api_key, self.user_id))
            if not result:
                raise ValueError(f"Credenciais não encontradas para api_key {self.api_key} e user_id {self.user_id}.")
            
            credentials_json = result[0][0]
            return credentials_json
        except Exception as e:
            general_logger.error(f"Erro ao carregar credenciais: {e}")
            raise ValueError(f"Falha ao carregar credenciais: {e}")

    def create_client(self):
        """
        Retorna uma instância do client apropriado (OKXClient, BinanceClient, etc.)
        """
        raise NotImplementedError("Este método deve ser implementado pelas subclasses.")

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def get_fill_price(self, order_id):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def cancel_order(self, symbol, order):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def get_open_order(self, symbol):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def get_order_status(self, symbol, order_id):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def get_last_trade(self, symbol):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")
    
    def get_current_price(self, symbol):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def get_balance(self, ccy=None):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

    def get_order_execution_price(self, symbol, order_id):
        raise NotImplementedError("Este método deve ser implementado pela subclasse específica da exchange.")

class OKXInterface(ExchangeInterface):
    def __init__(self, exchange_id: int, user_id: int, api_key: int):
        super().__init__(exchange_id, user_id, api_key)
        self.okx_client = self.create_client()

    def create_client(self):
        """
        Cria uma instância do OKXClient com as credenciais carregadas.
        """
        return OKXClient({
            "api_key": self.credentials.get("api_key"),
            "secret_key": self.credentials.get("secret_key"),
            "passphrase": self.credentials.get("passphrase"),
        })

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        general_logger.info(f"Placing order: {symbol}, {side}, {order_type}, {size}, {currency}, {price}")
        response = self.okx_client.place_order(symbol, side, order_type, size, currency, price)
        return response
    
    def get_current_price(self, symbol):
        return self.okx_client.get_current_price(symbol)

    def get_fill_price(self, order_id):
        general_logger.info(f"Getting fill price for order ID: {order_id}")
        return self.okx_client.wait_for_fill_price(order_id)

    def cancel_order(self, symbol, order):
        general_logger.info(f"Cancelling order: {order} for symbol: {symbol}")
        response = self.okx_client.cancel_order(symbol, order)
        return response

    def get_open_order(self, symbol):
        general_logger.info(f"Getting open orders for symbol: {symbol}")
        response = self.okx_client.get_open_orders(symbol)
        return response

    def get_order_status(self, symbol, order_id):
        general_logger.info(f"Getting status for order ID: {order_id} on symbol: {symbol}")
        response = self.okx_client.get_order_status(symbol, order_id)
        return response

    def get_last_trade(self, symbol):
        general_logger.info(f"Getting last trade for symbol: {symbol}")
        response = self.okx_client.get_last_trade(symbol)
        return response

    def get_balance(self, ccy=None):
        general_logger.info(f"Getting balance for currency: {ccy}")
        response = self.okx_client.get_balance(ccy)

        if 'data' in response and isinstance(response['data'], list) and response['data']:
            details = response['data'][0].get('details', [])
            for detail in details:
                if detail.get('ccy') == ccy:
                    avail_balance = detail.get('availBal', None)
                    if avail_balance is not None and avail_balance != '':
                        return float(avail_balance)
        return 0.0

    def get_order_execution_price(self, symbol, order_id):
        general_logger.info(f"Getting execution price for order ID: {order_id} on symbol: {symbol}")
        order_status = self.okx_client.get_order_status(symbol, order_id)
        execution_price = float(order_status['data'][0].get('fillPx', 0))
        return execution_price

class BinanceInterface(ExchangeInterface):
    def __init__(self, config: object):
        """
        Interface específica para a Binance.
        :param config: Configurações específicas para a Binance.
        """
        super().__init__(config)
        self.binance_client = BinanceClient(self.config)

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        general_logger.info(f"Placing order: {symbol}, {side}, {order_type}, {size}, {currency}, {price}")
        response = self.binance_client.place_order(symbol, side, order_type, size, currency, price)
        return response
    
    def get_current_price(self, symbol):
        try:
            response = self.okx_client.get_ticker(symbol)
            if 'data' in response and isinstance(response['data'], list) and response['data']:
                return float(response['data'][0].get('last', 0))
            else:
                general_logger.error(f"Erro ao obter preço atual na OKX para {symbol}")
                return None
        except Exception as e:
            general_logger.error(f"Erro ao obter preço atual na OKX: {e}")
            return None

    def get_fill_price(self, order_id):
        general_logger.info(f"Getting fill price for order ID: {order_id}")
        return self.binance_client.get_fill_price(order_id)

    def cancel_order(self, symbol, order):
        general_logger.info(f"Cancelling order: {order} for symbol: {symbol}")
        response = self.binance_client.cancel_order(symbol, order)
        return response

    def get_open_order(self, symbol):
        general_logger.info(f"Getting open orders for symbol: {symbol}")
        response = self.binance_client.get_open_orders(symbol)
        return response

    def get_order_status(self, symbol, order_id):
        general_logger.info(f"Getting status for order ID: {order_id} on symbol: {symbol}")
        response = self.binance_client.get_order_status(symbol, order_id)
        return response

    def get_last_trade(self, symbol):
        general_logger.info(f"Getting last trade for symbol: {symbol}")
        response = self.binance_client.get_last_trade(symbol)
        return response

    def get_balance(self, ccy=None):
        general_logger.info(f"Getting balance for currency: {ccy}")
        response = self.binance_client.get_balance(ccy)
        return response

    def get_order_execution_price(self, symbol, order_id):
        general_logger.info(f"Getting execution price for order ID: {order_id} on symbol: {symbol}")
        order_status = self.binance_client.get_order_status(symbol, order_id)
        execution_price = float(order_status.get('execution_price', 0))
        return execution_price

def get_exchange_interface(exchange_id: int, user_id: int, api_key: int):
    """
    Retorna a interface apropriada com base no ID da exchange.
    """
    try:
        query = load_query('select_exchange_by_id.sql')
        with get_db_connection() as db_client:
            result = db_client.fetch_data(query, (exchange_id,))
            if not result:
                raise ValueError(f"Exchange ID {exchange_id} não encontrada.")
            exchange_id, name,_,_ = result[0]

        with open('source/exchange_classes.json', 'r') as json_file:
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