import sys
import time
import hmac
import base64
import requests
import json
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from types import SimpleNamespace
import hmac
import hashlib
from datetime import datetime,timedelta
from urllib.parse import urlencode
from typing import Dict, Any, Optional

from log.log import general_logger

from eth_account import Account
from eth_account.messages import encode_typed_data,encode_defunct
import uuid
from web3 import Web3
from eth_abi import encode
import math


class BaseClient:
    def __init__(self):
        self.session = self.create_session_with_retries()

    def create_session_with_retries(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session

class OKXClient(BaseClient):
    def __init__(self, credentials, url='https://www.okx.com'):
        super().__init__()
        self.api_key = credentials["api_key"]
        self.secret_key = credentials["secret_key"]
        self.passphrase = credentials["passphrase"]
        self.url = url
        self.simulated = False 


    def generate_signature(self, timestamp, method, request_path, body):
        message = timestamp + method + request_path + body
        mac = hmac.new(bytes(self.secret_key, 'utf-8'), bytes(message, 'utf-8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d).decode()

    def send_request(self, method, request_path, body=None):
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        body_str = json.dumps(body) if body else ''
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self.generate_signature(timestamp, method, request_path, body_str),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
        }
        if self.simulated:
            headers['x-simulated-trading'] = '1'

        try:
            response = self.session.request(method, self.url + request_path, headers=headers, data=body_str)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[OKX] Error: {e}")
            return None
        

    def get_current_price(self, symbol):
        """
        Obtém o preço atual do ativo na OKX.

        :param symbol: Símbolo do ativo (exemplo: "BTC-USDT").
        :return: Preço atual do ativo como float ou None em caso de erro.
        """
        try:
            request_path = f'/api/v5/market/ticker?instId={symbol}'
            response = self.send_request('GET', request_path, None)

            # Verificar se a resposta é válida e contém os dados esperados
            if isinstance(response, dict) and "data" in response and isinstance(response["data"], list) and response["data"]:
                price_str = response["data"][0].get("last")
                if price_str is not None:
                    try:
                        return float(price_str)  # Converter corretamente a string para float
                    except ValueError:
                        print(f"Erro ao converter preço para float: {price_str}")
                        return None

            print(f"Erro ao obter preço atual na OKX para {symbol}: resposta inesperada {response}")
            return None

        except Exception as e:
            print(f"Erro ao obter preço atual na OKX: {e}")
            return None



    def place_order(self, symbol, side, order_type, size, currency, price=None):
        tgtCcy = "quote_ccy" if side == "buy" else "base_ccy"
        
        print(f'\nSending Order: {symbol},{side},{order_type},{size} in {tgtCcy}')
        
        body = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side,
            "ordType": order_type,
            "sz": size,
            "px": price,
            "tgtCcy": tgtCcy,
        }
        response = self.send_request('POST', '/api/v5/trade/order', body)
        if response and "data" in response:
            return response["data"]
        return None
   
    def wait_for_fill_price(self, order_id, check_interval=1, timeout=90):
        """
        Verifica repetidamente até que a ordem especificada pelo `order_id` seja executada, retornando o `fillPx`.
        Interrompe a verificação após um tempo limite de 30 segundos.

        Args:
            order_id (str): ID da ordem a ser monitorada.
            check_interval (int): Intervalo de tempo em segundos entre verificações (padrão é 1 segundo).
            timeout (int): Tempo máximo em segundos para aguardar o preenchimento (padrão é 30 segundos).

        Returns:
            float: Preço de execução `fillPx` da ordem quando ela for preenchida.
            None: Caso o tempo limite seja atingido ou a ordem não seja encontrada.
        """
        start_time = time.time()  # Marca o início do tempo de espera

        while True:
            # Verifica se o tempo limite foi atingido
            if time.time() - start_time > timeout:
                print("Tempo limite atingido. Ordem não executada dentro de 30 segundos.")
                return float(0.0)

            # Verifica o preenchimento da ordem
            response = self.send_request('GET', '/api/v5/trade/fills', {"ordId": order_id})
            
            if response and "data" in response:
                # Itera sobre cada trade na resposta para verificar o `order_id`
                for trade in response["data"]:
                    if trade["ordId"] == order_id:
                        return float(trade["fillPx"])  # Retorna o preço de execução específico da ordem
            
            time.sleep(check_interval)  # Espera antes de verificar novamente

    def cancel_order(self, symbol, order_id):
        body = {
            "instId": symbol,
            "ordId": order_id,
        }
        return self.send_request('POST', '/api/v5/trade/cancel-order', body)

    def get_open_orders(self, symbol):
        body = {
            "instId": symbol,
        }
        return self.send_request('GET', '/api/v5/trade/orders-pending', body)
    
    def get_order_status(self, symbol, order_id):
        body = {
            "ordId": order_id,
            "instId": symbol
        }
        return self.send_request('GET', '/api/v5/trade/order', body)
    
    def get_balance(self, ccy=None):
        """
        Obtém o saldo disponível de uma moeda específica (ccy).
        Se ccy não for fornecido, retorna 0.0 para evitar erros.
        """
        if not ccy:
            print("[OKX] Alerta: a função get_balance foi chamada sem uma moeda específica (ccy).")
            return 0.0

        # --- CORREÇÃO APLICADA AQUI ---
        # O parâmetro 'ccy' agora é parte da URL (query string), que é a forma correta para requisições GET.
        request_path = f'/api/v5/account/balance?ccy={ccy}'
        
        # A chamada agora não envia mais um 'body' para uma requisição GET.
        response = self.send_request('GET', request_path)

        # 1. Verifica se a chamada à API foi bem-sucedida e se os dados existem.
        if response and response.get('code') == '0' and response.get('data'):
            data_list = response['data']
            # 2. Navega pela estrutura do JSON para encontrar a lista de 'details'.
            if data_list and 'details' in data_list[0] and data_list[0]['details']:
                # Como agora filtramos corretamente na URL, a lista de detalhes deve ter apenas um item.
                asset_details = data_list[0]['details'][0]
                
                # 3. Extrai o saldo disponível ('availBal').
                avail_balance_str = asset_details.get('availBal')
                
                if avail_balance_str:
                    try:
                        # 4. Converte a string para um número float e retorna.
                        return float(avail_balance_str)
                    except (ValueError, TypeError):
                        print(f"[OKX] Erro ao converter o saldo '{avail_balance_str}' para float.")
                        return 0.0

        # 5. Se algo der errado (API fora do ar, moeda não encontrada, etc.), retorna 0.0.
        print(f"[OKX] Não foi possível obter o saldo para a moeda: {ccy}. Resposta da API: {response}")
        return 0.0

    def get_last_trade(self, symbol):
        body = {"instId": symbol, "limit": "100"}
        response = self.send_request('GET', '/api/v5/trade/fills', body)
        
        if response and response.get("code") == "0" and response.get("data"):
            last_trade_data = max(response["data"], key=lambda x: x['fillTime'])
            fill_time = datetime.fromtimestamp(int(last_trade_data.get('fillTime', 0)) / 1000)
            return SimpleNamespace(
                fill_id=last_trade_data.get("tradeId"),
                order_id=last_trade_data.get("ordId"),
                symbol=last_trade_data.get("instId"),
                side=last_trade_data.get("side"),
                fill_size=last_trade_data.get("fillSz"),
                fill_price=last_trade_data.get("fillPx"),
                fee=last_trade_data.get("fee"),
                time=fill_time
            )
        
        return None

    def get_recent_trades_last_7_days(self):

        def save_trades_to_csv(trades, filename='trades23.csv'):
            import csv
            """
            Salva a lista de trades em um arquivo CSV.

            :param trades: Lista de dicionários com os dados dos trades
            :param filename: Nome do arquivo CSV a ser gerado
            """
            if not trades:
                print("Nenhum trade para salvar.")
                return

            # Garante que todos os campos estejam presentes
            fieldnames = list(trades[0].keys()) + ["datetime"]

            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                for trade in trades:
                    # Converte o timestamp para datetime legível
                    ts = int(trade["ts"])
                    trade["datetime"] = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow(trade)
        """
        Retorna todas as operações realizadas nos últimos 7 dias.

        :return: Lista de dicionários com as operações filtradas.
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = int((now - timedelta(days=7)).timestamp() * 1000)

        all_trades = []
        body = {
            "limit": "100",
            "end": int(now.timestamp() * 1000)
        }

        response = self.send_request('GET', '/api/v5/trade/fills', body)
        trades_batch = response["data"]
        all_trades.extend(trades_batch)

        if not trades_batch:
            return []

        timestamps = [int(trade["ts"]) for trade in trades_batch]
        min_ts = min(timestamps)
        oldest_trade = min(trades_batch, key=lambda t: int(t["ts"]))
        oldest_bill_id = oldest_trade.get("billId")

        while min_ts > seven_days_ago:
            body = {
                "limit": "100",
                "before": 2379324521940650000
            }
            response = self.send_request('GET', '/api/v5/trade/fills', body)
            trades_batch = response["data"]
            if not trades_batch:
                break
            all_trades.extend(trades_batch)
            timestamps = [int(trade["ts"]) for trade in trades_batch]
            save_trades_to_csv(all_trades)
            min_ts = min(timestamps)
            oldest_trade = min(trades_batch, key=lambda t: int(t["ts"]))
            oldest_bill_id = oldest_trade.get("billId")
            print(f"Oldest billId: {oldest_bill_id}, timestamp: {min_ts}")
            break

        return all_trades

class OKXDemoClient(OKXClient):
    def __init__(self, credentials, url='https://www.okx.com'):
        super().__init__(credentials, url)
        self.simulated = True

class BinanceClient(BaseClient):
    def __init__(self, credentials, url='https://api.binance.com'):
        super().__init__()
        self.api_key = credentials["api_key"]
        self.secret_key = credentials["secret_key"]
        self.url = url

    def sign(self, params):
        # A geração da assinatura está correta, usando HMAC-SHA256.
        query_string = urlencode(params) # Usar urlencode é mais seguro que a junção manual.
        signature = hmac.new(self.secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        params['signature'] = signature
        return params

    def send_signed_request(self, method, endpoint, params=None):
        params = params or {}
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 10000

        headers = {'X-MBX-APIKEY': self.api_key}

        # A assinatura deve ser o último parâmetro adicionado.
        query_string_with_signature = urlencode(self.sign(params))

        # LOG REQUEST
        general_logger.info(f"[Binance] Request: {method} {endpoint}")

        try:
            if method.upper() == 'GET':
                res = self.session.get(f"{self.url}{endpoint}?{query_string_with_signature}", headers=headers)
            elif method.upper() == 'POST':
                res = self.session.post(f"{self.url}{endpoint}?{query_string_with_signature}", headers=headers)
            elif method.upper() == 'DELETE':
                res = self.session.delete(f"{self.url}{endpoint}?{query_string_with_signature}", headers=headers)
            else:
                general_logger.error(f"[Binance] Unsupported HTTP method: {method}")
                return None

            # LOG FULL RAW RESPONSE
            general_logger.info(f"[Binance] Response Status: {res.status_code}")
            general_logger.info(f"[Binance] Response Raw: {res.text}")

            res.raise_for_status()  # Lança uma exceção para códigos de erro HTTP (4xx ou 5xx)
            return res.json()

        except requests.exceptions.RequestException as e:
            general_logger.error(f"[Binance] Request error for {endpoint}: {e}")
            if e.response:
                general_logger.error(f"[Binance] Server response ({e.response.status_code}): {e.response.text}")
            return None

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        """
        Place an order on Binance.

        For MARKET orders:
        - BUY: uses quoteOrderQty (size = amount of quote currency to spend)
        - SELL: uses quantity (size = amount of base currency to sell)
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
        }

        if order_type.upper() == "MARKET":
            if side.upper() == "BUY":
                # BUY: size is quote currency amount to spend (e.g., 100 USDT)
                params["quoteOrderQty"] = size
            elif side.upper() == "SELL":
                # SELL: size is base currency amount to sell (e.g., 0.001 BTC)
                params["quantity"] = size
        else:
            # LIMIT orders always use quantity
            params["quantity"] = size

        if order_type.upper() == "LIMIT":
            if not price:
                raise ValueError("The 'price' parameter is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = "GTC"

        response = self.send_signed_request("POST", "/api/v3/order", params)
        return response

    def get_balance(self, asset=None):
        general_logger.info(f"[Binance] Fetching balance for asset: {asset}")

        data = self.send_signed_request("GET", "/api/v3/account")
        if not data:
            general_logger.error("[Binance] Failed to fetch account data")
            return [] if not asset else None

        balances_data = data.get("balances", [])

        if asset:
            # Log available assets with non-zero balances for debugging
            non_zero = [b for b in balances_data if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0]
            general_logger.info(f"[Binance] Assets with balance: {[b['asset'] for b in non_zero]}")

            for balance in balances_data:
                if balance.get("asset", "").upper() == asset.upper():
                    free_balance = float(balance.get('free', 0.0))
                    general_logger.info(f"[Binance] Found {asset}: free={free_balance}, locked={balance.get('locked', 0)}")
                    return free_balance

            general_logger.warning(f"[Binance] Asset '{asset}' not found in account balances")
            return None
        return balances_data

class BinanceDemoClient(BinanceClient):
    def __init__(self, credentials):
        super().__init__(credentials, url='https://testnet.binance.vision')

class BingXClient:
    """
    Um cliente para interagir com a API da BingX, com a lógica de assinatura
    e envio de requisições unificada e corrigida.
    """
    def __init__(self, credentials: Dict[str, str], base_url: str = 'https://open-api.bingx.com'):
        if not all(k in credentials for k in ['api_key', 'secret_key']):
            raise ValueError("As credenciais devem incluir 'api_key' e 'secret_key'.")
            
        self.api_key = credentials['api_key']
        self.secret_key = credentials['secret_key']
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'X-BX-APIKEY': self.api_key})

    def _sign_string(self, query_string: str) -> str:
        """Gera a assinatura HMAC-SHA256."""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _send_request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, params_in_body: bool = False) -> Optional[Dict[str, Any]]:
        """
        Envia uma requisição assinada para a API da BingX.
        O parâmetro 'params_in_body' foi ajustado para ter 'False' como padrão,
        que é o caso mais comum para endpoints de trade.
        """
        if params is None:
            params = {}
        
        # 1. Adiciona o timestamp aos parâmetros ANTES de qualquer outra coisa.
        params['timestamp'] = int(time.time() * 1000)
        
        # 2. Cria a query string ORDENADA. Esta será a base para tudo.
        sorted_keys = sorted(params.keys())
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted_keys])
        
        # 3. Gera a assinatura a partir da string exata.
        signature = self._sign_string(query_string)
        
        url = f"{self.base_url}{path}"
        
        try:
            response = None
            if method.upper() == 'GET':
                final_url = f"{url}?{query_string}&signature={signature}"
                response = self.session.get(final_url)
                
            elif method.upper() == 'POST':
                if params_in_body:
                    # Caso do get_balance: parâmetros no corpo
                    request_body = {**params, 'signature': signature}
                    response = self.session.post(url, data=request_body)
                else:
                    final_url = f"{url}?{query_string}&signature={signature}"
                    #print(f"Enviando POST para: {final_url} com corpo vazio")
                    response = self.session.post(final_url, data={}) # Corpo vazio!
            else:
                raise ValueError(f"Método HTTP '{method}' não suportado.")
            
            response.raise_for_status()
            response_data = response.json()
            
            # O código '0' na BingX significa sucesso.
            if response_data.get('code') != 0:
                return response_data # Retorna os dados do erro para debug
                
            return response_data

        except requests.exceptions.RequestException as e:
            print(f"[BingX] Erro na requisição: {e}")
            if e.response:
                print(f"[BingX] Resposta do Servidor: {e.response.text}")
            return None

    def get_balance(self) -> Optional[Dict[str, Any]]:
        """Consulta o saldo da conta spot."""
        path = "/openApi/spot/v1/account/balance"
        # Este endpoint específico requer os parâmetros no corpo.
        return self._send_request('POST', path, params_in_body=True)
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: Optional[float] = None, quoteOrderQty: Optional[float] = None, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Envia uma nova ordem para a exchange.
        Aceita 'quantity' (para moeda base) ou 'quoteOrderQty' (para moeda de cotação).
        """
        path = '/openApi/spot/v1/trade/order'
        
        # Validação: Um dos dois (quantity ou quoteOrderQty) deve ser fornecido.
        if quantity is None and quoteOrderQty is None:
            raise ValueError("É necessário fornecer 'quantity' (para a moeda base) ou 'quoteOrderQty' (para a moeda de cotação).")
        if quantity is not None and quoteOrderQty is not None:
            raise ValueError("Forneça apenas 'quantity' ou 'quoteOrderQty', não ambos.")

        order_params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
        }

        # Adiciona o parâmetro de quantidade correto com base no que foi fornecido
        if quantity is not None:
            order_params["quantity"] = quantity
        
        if quoteOrderQty is not None:
            order_params["quoteOrderQty"] = quoteOrderQty

        if order_type.upper() == 'LIMIT':
            if price is None or price <= 0:
                raise ValueError("O preço é obrigatório para ordens do tipo LIMIT.")
            order_params['price'] = price

        # Este endpoint requer os parâmetros na URL, então params_in_body=False.
        return self._send_request('POST', path, params=order_params, params_in_body=False)

class HyperliquidClient(BaseClient):
    """
    Cliente para interagir com a API da Hyperliquid, que usa assinatura EIP-712.
    """
    def __init__(self, credentials: Dict[str, str], url: str = 'https://api.hyperliquid.xyz'):
        super().__init__()
        if not all(k in credentials for k in ['wallet_address', 'private_key']):
            raise ValueError("As credenciais da Hyperliquid devem incluir 'wallet_address' e 'private_key'.")
        
        self.wallet_address = credentials['wallet_address']
        self.private_key = credentials['private_key']
        self.account = Account.from_key(self.private_key)
        self.base_url = url

    def _prepare_payload(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara e assina o payload da requisição de acordo com o padrão EIP-712 da Hyperliquid.
        """
        nonce = int(time.time() * 1000)
        
        # O vaultAddress é opcional e geralmente é zero para a maioria das ações
        signature_payload = {
            "action": action,
            "nonce": nonce,
            "vaultAddress": "0x0000000000000000000000000000000000000000"
        }

        # Definição da estrutura de dados para assinatura EIP-712
        typed_data = {
            "domain": {
                "name": "HyperliquidSignTransaction",
                "version": "1",
                "chainId": 1337, # Chain ID padrão para a L1 da Hyperliquid
                "verifyingContract": "0x0000000000000000000000000000000000000000",
            },
            "types": {
                "Agent": [
                    {"name": "source", "type": "string"},
                    {"name": "connectionId", "type": "bytes32"},
                ],
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
            },
            "primaryType": "Agent",
            "message": {
                "source": "a", # Fonte genérica 'a' para backend
                "connectionId": b'\0' * 32,
            },
        }

        # Converte a tupla de assinatura para o formato esperado
        raw_signature = self.account.sign_typed_data(full_message=typed_data)
        
        # A API espera que a assinatura seja uma tupla [r, s, v]
        signature = {
            "r": "0x" + raw_signature.r.to_bytes(32, 'big').hex(),
            "s": "0x" + raw_signature.s.to_bytes(32, 'big').hex(),
            "v": raw_signature.v
        }

        return {
            "action": action,
            "nonce": nonce,
            "signature": signature
        }

    def _send_request(self, request_type: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Envia uma requisição POST assinada para o endpoint da Hyperliquid.
        """
        full_payload = self._prepare_payload(payload)
        
        # O `type` da requisição é adicionado ao corpo final
        request_body = {
            "type": request_type,
            **full_payload
        }
        
        try:
            response = self.session.post(f"{self.base_url}/exchange", json=request_body)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[Hyperliquid] Erro na requisição: {e}")
            if e.response:
                print(f"[Hyperliquid] Resposta do Servidor: {e.response.text}")
            return None

    def get_balance(self, ccy: str = 'USDC') -> Optional[Dict[str, Any]]:
        """
        Consulta o saldo da conta e retorna o valor para uma moeda específica.
        O padrão é 'USDC', que é a principal moeda de margem na Hyperliquid.
        """
        action = {
            "type": "clearinghouseState",
            "user": self.wallet_address
        }
        response = self._send_request(action['type'], action)
        
        if response and isinstance(response, list) and len(response) > 0:
            data = response[0]
            if "assetPositions" in data:
                for position in data["assetPositions"]:
                    if position["position"]["coin"].upper() == ccy.upper():
                        # 'szi' representa o saldo da moeda
                        return float(position["position"]["szi"])
        return 0.0

    def place_order(self, symbol_index: int, is_buy: bool, size: float, limit_price: float, order_type: str) -> Optional[Dict[str, Any]]:
        """
        Envia uma nova ordem para a exchange.

        Args:
            symbol_index (int): O índice numérico do ativo (ex: 0 para BTC, 1 para ETH).
            is_buy (bool): True para compra, False para venda.
            size (float): Tamanho da ordem na moeda base.
            limit_price (float): Preço limite da ordem.
            order_type (str): Tipo da ordem, ex: "Gtc" (Good-til-Canceled) ou "Ioc" (Immediate-or-Cancel).
        """
        order_data = {
            "asset": symbol_index,
            "isBuy": is_buy,
            "limitPx": str(limit_price),
            "sz": str(size),
            "reduceOnly": False,
            "orderType": {"tif": order_type}, # Ex: {"tif": "Gtc"} ou {"tif": "Ioc"}
            "cloid": str(uuid.uuid4()) # Client Order ID opcional
        }
        
        action = {
            "type": "order",
            "orders": [order_data],
            "grouping": "na"
        }
        
        return self._send_request(action['type'], action)
    
class AsterClient(BaseClient):
    """
    Cliente corrigido para interagir com a API Spot da AsterDex,
    seguindo o método de autenticação HMAC SHA256 similar à Binance.
    """
    def __init__(self, credentials: Dict[str, str], url: str = 'https://sapi.asterdex.com'):
        super().__init__()
        if not all(k in credentials for k in ['api_key', 'secret_key']):
            raise ValueError("As credenciais da AsterDex devem incluir 'api_key' e 'secret_key'.")
            
        self.api_key = credentials['api_key']
        self.secret_key = credentials['secret_key']
        self.base_url = url

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Gera a assinatura HMAC-SHA256 a partir da query string dos parâmetros.
        """
        # A urllib.parse.urlencode garante a formatação correta (ex: key1=value1&key2=value2)
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _send_request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Prepara e envia uma requisição assinada para a API da AsterDex.
        """
        params = params or {}
        
        # Adiciona o timestamp obrigatório aos parâmetros ANTES de assinar
        params['timestamp'] = int(time.time() * 1000)
        
        # Gera a assinatura a partir de TODOS os parâmetros atuais
        params['signature'] = self._generate_signature(params)
        
        # Constrói a URL final com todos os parâmetros e a assinatura
        full_url = f"{self.base_url}{path}"
        query_string_with_signature = urlencode(params)
        
        # O header correto é 'X-MBX-APIKEY', conforme a documentação
        headers = {
            'X-MBX-APIKEY': self.api_key,
        }
        
        try:
            if method.upper() == 'GET':
                # Para GET, todos os parâmetros vão na URL
                response = self.session.get(f"{full_url}?{query_string_with_signature}", headers=headers)
            elif method.upper() == 'POST':
                # Para POST, a documentação permite parâmetros na query string também
                response = self.session.post(f"{full_url}?{query_string_with_signature}", headers=headers)
            else:
                raise ValueError(f"Método HTTP '{method}' não suportado.")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[AsterDex] Erro na requisição: {e}")
            if e.response:
                print(f"[AsterDex] Resposta do Servidor ({e.response.status_code}): {e.response.text}")
            return None

    def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        Consulta as informações da conta, incluindo todos os saldos,
        usando o endpoint /api/v1/account.
        """
        # Não são necessários parâmetros além de timestamp e signature, que são adicionados por _send_request
        return self._send_request('GET', '/api/v1/account')

    def place_order(self, symbol: str, side: str, size: float) -> Optional[Dict[str, Any]]:
        """
        Envia uma nova ordem a mercado (MARKET).

        Args:
            symbol (str): O par de negociação (ex: 'BTCUSDT').
            side (str): O lado da ordem ('BUY' ou 'SELL').
            size (float): A quantidade. Para 'BUY', é o valor a ser gasto (ex: 10 USDT).
                          Para 'SELL', é a quantidade a ser vendida (ex: 0.1 BTC).
        """        
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": 'MARKET',
        }

        if side.upper() == 'BUY':
            # Para compra, 'size' representa quanto gastar do ativo de cotação.
            params['quoteOrderQty'] = str(size)
        elif side.upper() == 'SELL':
            # Para venda, 'size' representa quanto vender do ativo base.
            params['quantity'] = str(size)
        else:
            raise ValueError("O parâmetro 'side' deve ser 'BUY' ou 'SELL'.")

        return self._send_request('POST', '/api/v1/order', params=params)

class PhemexClient(BaseClient):
    """
    Cliente para interagir com a API Spot da Phemex.
    Utiliza autenticação HMAC SHA256 com headers específicos.

    Phemex usa valores escalados:
    - Ep (prices): dividir por 10^priceScale (geralmente 8)
    - Ev (values): dividir por 10^valueScale (geralmente 8)
    """
    def __init__(self, credentials: Dict[str, str], url: str = 'https://api.phemex.com'):
        super().__init__()
        if not all(k in credentials for k in ['api_key', 'secret_key']):
            raise ValueError("As credenciais da Phemex devem incluir 'api_key' e 'secret_key'.")

        self.api_key = credentials['api_key']
        self.secret_key = credentials['secret_key']
        self.base_url = url
        # Phemex usa priceScale e valueScale - geralmente 8 para crypto
        self.price_scale = 8
        self.value_scale = 8

    def _to_scaled_value(self, value: float) -> int:
        """Converte um valor float para valor escalado (Ev)."""
        return int(value * (10 ** self.value_scale))

    def _from_scaled_value(self, scaled_value: int) -> float:
        """Converte um valor escalado (Ev) para float."""
        return float(scaled_value) / (10 ** self.value_scale)

    def _to_scaled_price(self, price: float) -> int:
        """Converte um preço float para preço escalado (Ep)."""
        return int(price * (10 ** self.price_scale))

    def _from_scaled_price(self, scaled_price: int) -> float:
        """Converte um preço escalado (Ep) para float."""
        return float(scaled_price) / (10 ** self.price_scale)

    def _generate_signature(self, path: str, query_string: str, expiry: int, body: str = '') -> str:
        """
        Gera a assinatura HMAC SHA256 para requisições Phemex.
        Formula: HMacSha256(URL Path + QueryString + Expiry + body)
        """
        message = path + query_string + str(expiry) + body
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _send_request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None,
                     body: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Prepara e envia uma requisição assinada para a API da Phemex.
        """
        # Expiry: timestamp Unix em SEGUNDOS (não milissegundos) + 60 segundos
        expiry = int(time.time()) + 60

        # Prepara query string se houver parâmetros
        query_string = ''
        if params:
            query_string = '?' + urlencode(params)

        # Prepara body string
        body_str = ''
        if body:
            body_str = json.dumps(body, separators=(',', ':'))

        # Gera assinatura
        signature = self._generate_signature(path, query_string, expiry, body_str)

        # Headers obrigatórios
        headers = {
            'x-phemex-access-token': self.api_key,
            'x-phemex-request-expiry': str(expiry),
            'x-phemex-request-signature': signature,
            'Content-Type': 'application/json'
        }

        # URL completa
        full_url = f"{self.base_url}{path}{query_string}"

        try:
            if method.upper() == 'GET':
                response = self.session.get(full_url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(full_url, headers=headers, data=body_str)
            elif method.upper() == 'PUT':
                response = self.session.put(full_url, headers=headers, data=body_str)
            elif method.upper() == 'DELETE':
                response = self.session.delete(full_url, headers=headers)
            else:
                raise ValueError(f"Método HTTP '{method}' não suportado.")

            response.raise_for_status()
            response_data = response.json()

            # Endpoints /md têm formato diferente: {"error": null, "result": {...}}
            # Outros endpoints: {"code": 0, "data": {...}}
            if path.startswith('/md'):
                if response_data.get('error') is not None:
                    print(f"[Phemex] Erro na API MD: {response_data.get('error')}")
                    return None
                return response_data.get('result')
            else:
                # Phemex retorna código 0 para sucesso
                if response_data.get('code') != 0:
                    print(f"[Phemex] Erro na API: {response_data.get('msg', 'Erro desconhecido')}")
                    return None
                return response_data.get('data')

        except requests.exceptions.RequestException as e:
            print(f"[Phemex] Erro na requisição: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[Phemex] Resposta do Servidor ({e.response.status_code}): {e.response.text}")
            return None

    def get_balance(self, currency: Optional[str] = None) -> float:
        """
        Consulta o saldo da carteira spot.

        Args:
            currency (str): O símbolo da moeda (ex: 'BTC', 'USDT').

        Returns:
            float: O saldo disponível da moeda.
        """
        path = '/spot/wallets'
        response = self._send_request('GET', path)

        # A API retorna uma lista direta de wallets, não um dict com 'balances'
        if not response or not isinstance(response, list):
            if not response:
                print(f"[Phemex] Não foi possível obter os saldos. Sem respostas.")
            else:
                print(f"[Phemex] Formato inesperado de resposta: {response}")
            return 0.0

        # Se currency não foi especificada, retorna 0
        if not currency:
            print(f"[Phemex] Moeda não especificada.")
            return 0.0

        # Procura pela moeda específica na lista de wallets
        for wallet in response:
            if wallet.get('currency', '').upper() == currency.upper():
                # Calcula o saldo disponível: balanceEv - lockedTradingBalanceEv - lockedWithdrawEv
                balance_ev = wallet.get('balanceEv', 0)
                locked_trading_ev = wallet.get('lockedTradingBalanceEv', 0)
                locked_withdraw_ev = wallet.get('lockedWithdrawEv', 0)
                available_balance_ev = balance_ev - locked_trading_ev - locked_withdraw_ev
                return self._from_scaled_value(available_balance_ev)

        print(f"[Phemex] Moeda '{currency}' não encontrada na carteira spot.")
        return 0.0

    def place_order(self, symbol: str, side: str, order_type: str, size: float,
                   currency: str, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Envia uma nova ordem para a exchange.

        Args:
            symbol (str): Símbolo do mercado (ex: "sBTCUSDT" - spot symbols começam com 's').
            side (str): Lado da ordem ("Buy" ou "Sell").
            order_type (str): Tipo da ordem ("Market" ou "Limit").
            size (float): Tamanho da ordem.
            currency (str): Moeda usada (base ou quote).
            price (float): Preço da ordem (obrigatório para LIMIT).

        Returns:
            dict or None: A resposta da API da exchange.
        """
        path = '/spot/orders'

        # Normaliza o side (Phemex usa Buy/Sell com maiúscula inicial)
        side_normalized = side.capitalize()

        # Determina qtyType baseado na moeda
        # Se currency é a moeda base, usa ByBase; se é quote, usa ByQuote
        base_currency = symbol.replace('s', '', 1).replace('USDT', '').replace('USDC', '')
        qty_type = 'ByBase' if currency.upper() == base_currency.upper() else 'ByQuote'

        # Converte size para valor escalado
        size_ev = self._to_scaled_value(size)

        # Monta o body da requisição
        order_body = {
            'symbol': symbol,
            'side': side_normalized,
            'ordType': order_type.capitalize(),
            'qtyType': qty_type,
        }

        # Define quantidade baseada no qtyType
        if qty_type == 'ByBase':
            order_body['baseQtyEv'] = str(size_ev)
            order_body['quoteQtyEv'] = '0'
        else:
            order_body['baseQtyEv'] = '0'
            order_body['quoteQtyEv'] = str(size_ev)

        # Se for ordem LIMIT, adiciona o preço
        if order_type.upper() == 'LIMIT':
            if not price:
                raise ValueError("O parâmetro 'price' é obrigatório para ordens do tipo LIMIT.")
            price_ep = self._to_scaled_price(price)
            order_body['priceEp'] = str(price_ep)
        else:
            order_body['priceEp'] = '0'

        # Campos opcionais
        order_body['stopPxEp'] = '0'
        order_body['clOrdID'] = str(uuid.uuid4())  # Client Order ID único

        response = self._send_request('POST', path, body=order_body)
        return response

    def get_order_status(self, symbol: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta o status de uma ordem específica.

        Args:
            symbol (str): Símbolo da ordem.
            order_id (str): ID da ordem.

        Returns:
            dict or None: Informações da ordem.
        """
        path = '/spot/orders/active'
        params = {'symbol': symbol}

        response = self._send_request('GET', path, params=params)

        # response já é diretamente o 'data' (uma lista de ordens)
        if not response:
            return None

        # Se response não for uma lista, pode ser um dict com 'rows'
        orders = response if isinstance(response, list) else response.get('rows', [])

        # Procura pela ordem específica
        for order in orders:
            if order.get('orderID') == order_id:
                return order

        return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Obtém o preço atual de mercado para um símbolo.

        Args:
            symbol (str): Símbolo do mercado (ex: "sBTCUSDT").

        Returns:
            float: Preço atual ou None em caso de erro.
        """
        path = '/md/spot/ticker/24hr'
        params = {'symbol': symbol}

        response = self._send_request('GET', path, params=params)

        if not response:
            return None

        # Para /md endpoints, response já é o 'result' diretamente
        # O formato é: {"openEp": ..., "highEp": ..., "lastEp": ..., ...}
        last_price_ep = response.get('lastEp', 0)
        return self._from_scaled_price(last_price_ep)

    def wait_for_fill_price(self, order_id: str, symbol: str,
                           check_interval: int = 1, timeout: int = 90) -> float:
        """
        Aguarda até que a ordem seja executada e retorna o preço de execução.

        Args:
            order_id (str): ID da ordem.
            symbol (str): Símbolo da ordem.
            check_interval (int): Intervalo entre verificações (segundos).
            timeout (int): Tempo máximo de espera (segundos).

        Returns:
            float: Preço de execução ou 0.0 em caso de timeout.
        """
        start_time = time.time()

        while time.time() - start_time <= timeout:
            order = self.get_order_status(symbol, order_id)

            if order:
                status = order.get('ordStatus')
                # Verifica se a ordem foi totalmente executada
                if status == 'Filled':
                    # Pega o preço médio de execução
                    avg_price_ep = order.get('avgPriceEp', 0)
                    if avg_price_ep:
                        return self._from_scaled_price(avg_price_ep)

            time.sleep(check_interval)

        print(f"[Phemex] Timeout ao aguardar execução da ordem {order_id}.")
        return 0.0

    def cancel_order(self, symbol: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Cancela uma ordem ativa.

        Args:
            symbol (str): Símbolo da ordem.
            order_id (str): ID da ordem.

        Returns:
            dict or None: Resposta da API.
        """
        path = '/spot/orders'
        params = {
            'symbol': symbol,
            'orderID': order_id
        }

        return self._send_request('DELETE', path, params=params)

    def get_open_orders(self, symbol: str) -> Optional[list]:
        """
        Retorna todas as ordens abertas para um símbolo.

        Args:
            symbol (str): Símbolo do mercado.

        Returns:
            list: Lista de ordens abertas.
        """
        path = '/spot/orders/active'
        params = {'symbol': symbol}

        response = self._send_request('GET', path, params=params)

        # response já é diretamente o 'data'
        if response:
            # Se for uma lista, retorna diretamente
            if isinstance(response, list):
                return response
            # Se for um dict com 'rows', retorna rows
            return response.get('rows', [])

        return []

class PhemexTestnetClient(PhemexClient):
    """Cliente Phemex para o ambiente de testes (testnet)."""
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials, url='https://testnet-api.phemex.com')

if __name__ == '__main__':
    # --- CONFIGURAÇÃO ---
    # IMPORTANTE: Mantenha suas chaves de API seguras.
    # Considere carregá-las de variáveis de ambiente ou de um arquivo de configuração seguro.
    API_KEY = "a78424aa56d3a69953ac47800ad9b21fa6ccfa962def066fd9683f69ef24bf0d"
    SECRET_KEY = "780257d71cfd02bccb00cfb52712764ad2a2809be5b2ef962a46ea199692812a"

    credentials = {
        "api_key": API_KEY,
        "secret_key": SECRET_KEY
    }

    # 1. Inicializar o cliente
    client = AsterClient(credentials)

    # 2. Chamar a função para obter o saldo
    balance=client.get_balance()
    print(balance)
    order = client.place_order(symbol='BTCUSDT',side='SELL',size=0.00003)
    print(order)