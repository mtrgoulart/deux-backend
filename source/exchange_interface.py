from log.log import general_logger
from .client import OKXClient, OKXDemoClient, BinanceClient, BinanceDemoClient, BingXClient, AsterClient
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
        #general_logger.info(f"[BingXInterface] Buscando saldo para a moeda: {ccy}...")
        
        # 1. Chama o método do cliente para obter todos os saldos da conta spot
        balance_data = self.bingx_client.get_balance()
        general_logger.info(f"[BingXInterface] Balance atual para moeda {ccy}: {balance_data}...")

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
        Abstrai a criação de uma ordem, chamando o método correspondente do cliente
        e utilizando o parâmetro de quantidade correto ('quantity' ou 'quoteOrderQty')
        com base no lado da operação ('side').

        Args:
            symbol (str): Símbolo do mercado (ex: "BTC-USDT").
            side (str): Lado da ordem ("BUY" ou "SELL").
            order_type (str): Tipo da ordem ("MARKET" ou "LIMIT").
            size (float): Tamanho da ordem. Para 'BUY', é o valor em moeda de cotação (USDT).
                          Para 'SELL', é o valor em moeda base (BTC).
            price (float): Preço da ordem (usado para ordens LIMIT).
            kwargs: Argumentos adicionais para compatibilidade.

        Returns:
            dict or None: A resposta da API da exchange.
        """

        try:
            # Prepara os parâmetros para o cliente, deixando a quantidade de fora por enquanto
            params = {
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "price": price
            }

            # Lógica principal: decide qual parâmetro de quantidade usar
            if side.upper() == 'BUY':
                # Para compra, 'size' representa a quantidade da moeda de cotação (ex: USDT)
                params['quoteOrderQty'] = size
            elif side.upper() == 'SELL':
                # Para venda, 'size' representa a quantidade da moeda base (ex: BTC)
                params['quantity'] = size
            else:
                # Segurança para evitar lados inválidos
                raise ValueError(f"Lado da operação inválido: '{side}'. Use 'BUY' ou 'SELL'.")

            # Chama o método do cliente usando desempacotamento de dicionário
            order_response = self.bingx_client.place_order(**params)
            return order_response
            
        except ValueError as e:
            print(f"[BingXInterface] Erro ao criar ordem: {e}")
            return None

class AsterInterface(ExchangeInterface):
    def __init__(self, exchange_id, user_id, api_key):
        super().__init__(exchange_id, user_id, api_key)
        self.aster_client = self.create_client()

    def create_client(self):
        """Instancia o cliente específico para a API da AsterDex."""
        return AsterClient(self.credentials)

    def get_balance(self, ccy: str) -> float:
        """
        Busca e retorna o saldo disponível ('free') de uma moeda específica.

        Este método chama o cliente da AsterDex, processa a resposta e extrai
        o valor do saldo para a moeda solicitada.

        Args:
            ccy (str): O símbolo da moeda (ex: 'USDT', 'BTC').

        Returns:
            float: O saldo disponível da moeda. Retorna 0.0 se a moeda não for
                   encontrada ou em caso de erro.
        """
        # 1. Chama o método do cliente para obter os dados da conta
        account_data = self.aster_client.get_balance()

        # 2. Verifica se a resposta é válida e contém a lista de 'balances'
        if not account_data or 'balances' not in account_data:
            general_logger.warning(f"[AsterInterface] Não foi possível obter os saldos ou a resposta está malformada: {account_data}")
            return 0.0

        # 3. Procura pela moeda específica (ccy) na lista de saldos
        for balance in account_data['balances']:
            if balance.get('asset', '').upper() == ccy.upper():
                # 4. Se encontrar, retorna o saldo 'free' convertido para float
                return float(balance.get('free', 0.0))

        # 5. Se não encontrar a moeda, retorna 0.0
        general_logger.info(f"[AsterInterface] Moeda '{ccy}' não encontrada na conta.")
        return 0.0
    
    def place_order(self, symbol: str, side: str, order_type: str, size: float, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Abstrai a criação de uma ordem a mercado, chamando o cliente e formatando a resposta.
        Como o cliente já está focado em ordens a mercado, o parâmetro 'order_type' é ignorado.

        Args:
            symbol (str): Símbolo do mercado (ex: "BTC-USDT").
            side (str): Lado da ordem ("BUY" ou "SELL").
            order_type (str): Tipo da ordem (ignorado, sempre será 'MARKET').
            size (float): Tamanho da ordem. Para 'BUY', é o valor em moeda de cotação (USDT).
                          Para 'SELL', é o valor em moeda base (BTC).
            kwargs: Argumentos adicionais para compatibilidade com a classe base.

        Returns:
            dict or None: Um dicionário formatado com os dados essenciais da ordem ou None em caso de falha.
        """
        try:
            # 1. Chama o método do cliente, que já lida com a lógica de ordens a mercado
            raw_order_response = self.aster_client.place_order(
                symbol=symbol,
                side=side,
                size=size
            )

            # 2. Verifica se a criação da ordem foi bem-sucedida
            if not raw_order_response or 'orderId' not in raw_order_response:
                general_logger.error(f"[AsterInterface] Falha ao criar a ordem na AsterDex. Resposta: {raw_order_response}")
                return None

            # 3. Formata a resposta para um padrão limpo e consistente
            formatted_order = {
                'order_id': raw_order_response.get('orderId'),
                'symbol': raw_order_response.get('symbol'),
                'side': raw_order_response.get('side'),
                'type': raw_order_response.get('type'),
                'status': raw_order_response.get('status'),
                'client_order_id': raw_order_response.get('clientOrderId'),
                'update_time': raw_order_response.get('updateTime'),
                'raw_response': raw_order_response  # Inclui a resposta original para fins de debug
            }
            
            general_logger.info(f"[AsterInterface] Ordem criada com sucesso: {formatted_order}")
            return formatted_order
            
        except Exception as e:
            general_logger.error(f"[AsterInterface] Exceção ao criar ordem: {e}")
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
