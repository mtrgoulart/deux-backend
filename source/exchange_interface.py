from log.log import general_logger
from .client import OKXClient, OKXDemoClient, BinanceClient, BinanceDemoClient, BingXClient
from .context import get_db_connection
from .dbmanager import load_query
import json
import importlib
import os
from typing import Dict, Any, Optional

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

    def get_balance(self, ccy: str) -> float:
        """
        Busca e retorna o saldo de uma moeda específica na conta spot.

        Este método utiliza o bingx_client para obter a lista de todos os ativos
        e filtra para encontrar o saldo da moeda solicitada.

        Args:
            ccy (str): O símbolo da moeda (ex: 'USDT', 'BTC', 'ETH').

        Returns:
            float: O saldo livre (disponível) da moeda. Retorna 0.0 se a
                   moeda não for encontrada ou em caso de erro na comunicação
                   com a API.
        """
        print(f"[BingXInterface] Buscando saldo para a moeda: {ccy}...")
        
        # 1. Chama o método do cliente para obter todos os saldos da conta spot
        balance_data = self.bingx_client.get_balance()

        # 2. Verifica se a chamada à API foi bem-sucedida e retornou dados
        if not balance_data:
            print(f"[BingXInterface] Não foi possível obter os saldos da API.")
            return 0.0

        # 3. Navega de forma segura pela estrutura de dados da resposta
        balances = balance_data.get("data", {}).get("balances", [])

        # 4. Procura pela moeda específica (ccy) na lista de saldos
        for asset in balances:
            # Compara os símbolos em maiúsculas para evitar erros (ex: 'usdt' vs 'USDT')
            if asset.get('asset', '').upper() == ccy.upper():
                # 5. Se encontrar, retorna o saldo 'free' convertido para float
                return float(asset.get('free', 0.0))

        # 6. Se o loop terminar e não encontrar a moeda, informa e retorna 0.0
        print(f"[BingXInterface] Moeda '{ccy}' não encontrada na carteira spot ou saldo zerado.")
        return 0.0
    
    def place_order(self, symbol: str, side: str, order_type: str, size: float, price: float=None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Abstrai a criação de uma ordem, chamando o método correspondente do cliente.

        Args:
            symbol (str): Símbolo do mercado (ex: "BTC-USDT").
            side (str): Lado da ordem ("BUY" ou "SELL").
            order_type (str): Tipo da ordem ("MARKET" ou "LIMIT").
            size (float): Tamanho da ordem.
            price (float): Preço da ordem (usado para ordens LIMIT).
            kwargs: Argumentos adicionais (não usados aqui, mas bom para compatibilidade).

        Returns:
            dict or None: A resposta da API da exchange.
        """

        try:
            order_response = self.bingx_client.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=size,
                price=price
            )
            return order_response
        except ValueError as e:
            print(f"[BingXInterface] Erro ao criar ordem: {e}")
            return None


def get_exchange_interface(exchange_id: int, user_id: int, api_key: int):
    try:
        query = load_query('select_exchange_by_id.sql') #
        with get_db_connection() as db_client:
            result = db_client.fetch_data(query, (exchange_id,))
            if not result:
                raise ValueError(f"Exchange ID {exchange_id} não encontrada.")
            # Captura a flag is_demo
            db_exchange_id, name, base_url, is_demo = result[0] #

        with open(exchange_classes_path, 'r') as json_file:
            exchange_classes = json.load(json_file)

        # Acessa o mapeamento para a exchange específica
        exchange_mapping = exchange_classes.get(str(exchange_id))
        if not exchange_mapping:
            raise ValueError(f"Mapeamento para Exchange ID {exchange_id} não encontrado em exchange_classes.json.")

        # Escolhe o caminho da classe com base na flag is_demo
        if is_demo:
            class_path = exchange_mapping.get("demo")
        else:
            class_path = exchange_mapping.get("real")
        
        if not class_path:
            mode = "demo" if is_demo else "real"
            raise ValueError(f"Interface '{mode}' para Exchange ID {exchange_id} não mapeada.")

        # O resto da função continua igual
        module_name, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        exchange_class = getattr(module, class_name)

        return exchange_class(exchange_id, user_id, api_key)
    except Exception as e:
        raise ValueError(f"Erro ao inicializar a interface para Exchange ID {exchange_id}: {e}")
