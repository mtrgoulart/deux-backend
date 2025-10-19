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
        
        try:
            if method.upper() == 'GET':
                res = self.session.get(f"{self.url}{endpoint}?{query_string_with_signature}", headers=headers)
            elif method.upper() == 'POST':
                res = self.session.post(f"{self.url}{endpoint}?{query_string_with_signature}", headers=headers)
            elif method.upper() == 'DELETE':
                res = self.session.delete(f"{self.url}{endpoint}?{query_string_with_signature}", headers=headers)
            else:
                 print(f"[Binance] Error: Método HTTP '{method}' não suportado.")
                 return None

            res.raise_for_status()  # Lança uma exceção para códigos de erro HTTP (4xx ou 5xx)
            return res.json()
        
        except requests.exceptions.RequestException as e:
            # Captura de erro aprimorada para fornecer mais detalhes.
            print(f"[Binance] Erro na requisição para {e.request.url}: {e}")
            if e.response:
                print(f"[Binance] Resposta do Servidor ({e.response.status_code}): {e.response.text}")
            return None

    def get_current_price(self, symbol):
        # Endpoint público, não requer assinatura.
        try:
            response = self.session.get(f"{self.url}/api/v3/ticker/price", params={"symbol": symbol})
            response.raise_for_status()
            return float(response.json()["price"])
        except requests.exceptions.RequestException as e:
            print(f"[Binance] Erro ao obter preço para {symbol}: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"[Binance] Erro ao processar resposta de preço para {symbol}: {e}")
            return None

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        # Validação: O endpoint está correto (POST /api/v3/order).
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": size
        }
        # O parâmetro 'currency' não é usado pela API da Binance neste endpoint,
        # mas mantê-lo na assinatura do método garante a compatibilidade com a ExchangeInterface.
        
        if order_type.upper() == "LIMIT":
            if not price:
                raise ValueError("O parâmetro 'price' é obrigatório para ordens do tipo LIMIT.")
            params["price"] = price
            params["timeInForce"] = "GTC" # Good-Til-Canceled, correto para ordens LIMIT padrão.

        response = self.send_signed_request("POST", "/api/v3/order", params)
        return response # Retornar a resposta completa pode ser mais útil.

    def wait_for_fill_price(self, order_id, symbol, check_interval=1, timeout=90):
        start_time = time.time()
        while time.time() - start_time <= timeout:
            order = self.get_order_status(symbol, order_id)
            if order and order.get("status") == "FILLED":
                # Para ordens a mercado, o 'price' é 0. O preço real está em 'cummulativeQuoteQty' / 'executedQty'.
                # Para simplificar e manter consistência, usar o preço da ordem LIMIT ou o preço médio da MARKET é uma boa abordagem.
                if float(order.get("price", 0.0)) > 0:
                    return float(order.get("price"))
                elif float(order.get("executedQty", 0.0)) > 0:
                    return float(order.get("cummulativeQuoteQty")) / float(order.get("executedQty"))

            time.sleep(check_interval)
        print(f"[Binance] Timeout ao aguardar execução da ordem {order_id}.")
        return 0.0

    def cancel_order(self, symbol, order_id):
        # Validação: O endpoint está correto (DELETE /api/v3/order).
        params = {"symbol": symbol, "orderId": order_id}
        return self.send_signed_request("DELETE", "/api/v3/order", params)

    def get_open_orders(self, symbol):
        # Validação: O endpoint está correto (GET /api/v3/openOrders).
        params = {"symbol": symbol}
        return self.send_signed_request("GET", "/api/v3/openOrders", params)

    def get_order_status(self, symbol, order_id):
        # Validação: O endpoint está correto (GET /api/v3/order).
        params = {"symbol": symbol, "orderId": order_id}
        return self.send_signed_request("GET", "/api/v3/order", params)

    def get_balance(self, asset=None):
        # Validação: O endpoint está correto (GET /api/v3/account).
        data = self.send_signed_request("GET", "/api/v3/account")
        if not data:
            return [] if not asset else None
            
        balances_data = data.get("balances", [])
        if asset:
            for balance in balances_data:
                if balance["asset"] == asset.upper():
                    return balance # Retorna o dicionário completo do ativo.
            return None # Retorna None se o ativo específico não for encontrado.
        return balances_data

    def get_last_trade(self, symbol):
        # Validação: O endpoint está correto (GET /api/v3/myTrades).
        trades = self.send_signed_request("GET", "/api/v3/myTrades", {"symbol": symbol, "limit": 1})
        if trades:
            trade = trades[-1]
            time_obj = datetime.fromtimestamp(trade["time"] / 1000)
            return SimpleNamespace(
                id=trade["id"],
                order_id=trade["orderId"],
                price=trade["price"],
                qty=trade["qty"],
                time=time_obj,
                is_buyer=trade["isBuyer"]
            )
        return None

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