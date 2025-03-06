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
from mexc_api.spot import Spot
#from mexc_sdk.constant import OrderSide, OrderType
from datetime import datetime



class OKXClient:
    def __init__(self, credentials, url='https://www.okx.com'):
        self.api_key = credentials["api_key"]
        self.secret_key = credentials["secret_key"]
        self.passphrase = credentials["passphrase"]
        self.url = url
        self.session = self.create_session_with_retries()

    def create_session_with_retries(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session

    def generate_signature(self, timestamp, method, request_path, body):
        message = timestamp + method + request_path + body
        mac = hmac.new(bytes(self.secret_key, 'utf-8'), bytes(message, 'utf-8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d).decode()

    def send_request(self, method, request_path, body, timeout=30):
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        body_str = json.dumps(body) if body else ''
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self.generate_signature(timestamp, method, request_path, body_str),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'x-simulated-trading': '1'  # Simulated trading environment
        }

        try:
            response = self.session.request(method, self.url + request_path, headers=headers, data=body_str, timeout=timeout)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during request: {e}")
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
            return response["data"][0]["ordId"]  # Retorna o ID da ordem
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
        params = {}
        if ccy:
            params['ccy'] = ccy
        return self.send_request('GET', '/api/v5/account/balance', body=params)
    
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

class BinanceClient:
    def __init__(self, credentials, url='https://api.binance.com'):
        """
        Cliente para a API da Binance.
        :param credentials: Dicionário contendo as credenciais de API (api_key, secret_key).
        :param url: URL base da API da Binance.
        """
        self.api_key = credentials["api_key"]
        self.secret_key = credentials["secret_key"]
        self.url = url
        self.session = self.create_session_with_retries()

    def create_session_with_retries(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        return session

    def _generate_signature(self, params):
        query_string = '&'.join([f"{key}={value}" for key, value in params.items() if value is not None])
        return hmac.new(self.secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def _send_request(self, method, endpoint, params=None):
        if params is None:
            params = {}
        
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self._generate_signature(params)
        headers = {
            'X-MBX-APIKEY': self.api_key
        }

        url = f"{self.url}{endpoint}"

        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, params=params)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers, params=params)
            else:
                raise ValueError("HTTP method not supported.")

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error during request: {e}")
            return None

    def get_current_price(self, symbol):
        """
        Obtém o preço atual do ativo na Binance.
        """
        try:
            response = self._send_request('GET', f'/api/v3/ticker/price?symbol={symbol}')
            if response and 'price' in response:
                return float(response['price'])
            else:
                print(f"Erro ao obter preço atual na Binance para {symbol}")
                return None
        except Exception as e:
            print(f"Erro ao obter preço atual na Binance: {e}")
            return None

    def place_order(self, symbol, side, order_type, quantity, price=None):
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'price': price,
            'timeInForce': 'GTC' if price else None
        }
        return self._send_request('POST', '/api/v3/order', params)

    def cancel_order(self, symbol, order_id):
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._send_request('DELETE', '/api/v3/order', params)

    def get_open_orders(self, symbol=None):
        params = {
            'symbol': symbol
        }
        return self._send_request('GET', '/api/v3/openOrders', params)

    def get_order_status(self, symbol, order_id):
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._send_request('GET', '/api/v3/order', params)

    def get_balance(self, asset=None):
        endpoint = '/api/v3/account'
        response = self._send_request('GET', endpoint)
        if response and 'balances' in response:
            balances = {item['asset']: float(item['free']) for item in response['balances']}
            if asset:
                return balances.get(asset, 0.0)
            return balances
        return {}

    def get_last_trade(self, symbol):
        params = {
            'symbol': symbol,
            'limit': 1
        }
        response = self._send_request('GET', '/api/v3/myTrades', params)
        if response:
            return response[-1]  # Retorna o último trade
        return None

class MEXCClient:
    def __init__(self, credentials, url='https://api.mexc.com'):
        self.api_key = credentials["api_key"]
        self.secret_key = credentials["secret_key"]
        self.url = url
        self.client = Spot(api_key=self.api_key, api_secret=self.secret_key)

    def get_current_price(self, symbol):
        try:
            response = self.client.market.ticker_price(symbol)
            price_data=response[0]
            return float(price_data['price'])
        except Exception as e:
            print(f"Erro ao obter preço atual na MEXC: {e}")
            return None

    def place_order(self, symbol, side, order_type, quantity, price=None):
        try:
            order_params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": order_type.upper(),
                "quantity": quantity,
            }
            if price:
                order_params["price"] = price
                order_params["timeInForce"] = "GTC"
            response = self.client.trade.order_new(**order_params)
            return response.get('orderId')
        except Exception as e:
            print(f"Erro ao colocar ordem na MEXC: {e}")
            return None

    def cancel_order(self, symbol, order_id):
        try:
            response = self.client.trade.order_cancel(symbol=symbol, orderId=order_id)
            return response.get('status') == 'CANCELED'
        except Exception as e:
            print(f"Erro ao cancelar ordem na MEXC: {e}")
            return False

    def get_order_status(self, symbol, order_id):
        try:
            response = self.client.trade.order_query(symbol=symbol, orderId=order_id)
            return response
        except Exception as e:
            print(f"Erro ao obter status da ordem na MEXC: {e}")
            return None

    def get_open_orders(self, symbol=None):
        try:
            response = self.client.trade.open_orders(symbol=symbol)
            return response
        except Exception as e:
            print(f"Erro ao obter ordens abertas na MEXC: {e}")
            return None

    def get_balance(self, asset=None):
        try:
            response = self.client.account.get_account_info()
            balances = {item['asset']: float(item['free']) for item in response['balances']}
            return {asset: balances.get(asset, 0.0)} if asset else balances
        except Exception as e:
            print(f"Erro ao obter saldo na MEXC: {e}")
            return None

    def get_last_trade(self, symbol):
        try:
            response = self.client.market.trades(symbol=symbol, limit=1)
            return response[0] if response else None
        except Exception as e:
            print(f"Erro ao obter última negociação na MEXC: {e}")
            return None



if __name__ == "__main__":
    credentials = {"api_key": "mx0vglaDR6ZEF14nhe", "secret_key": "6c21d3327433484d9d53ddda99eac350"}
    mexc_client = MEXCClient(credentials)
    
    symbol = "BTCUSDT"
    print(f"Preço atual de {symbol}: {mexc_client.get_current_price(symbol)}")
    print(f"Saldo disponível: {mexc_client.get_balance()}")