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


class OKXClient:
    def __init__(self, config_loader, url='https://www.okx.com'):
        self.api_key = config_loader.get('okx', 'api_key')
        self.secret_key = config_loader.get('okx', 'secret_key')
        self.passphrase = config_loader.get('okx', 'passphrase')
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

if __name__=="__main__":
    from pp import ConfigLoader
    config = ConfigLoader(r'C:\Project\DeuxTradingBot\config.ini')
    client = OKXClient(config)
    #op = client.get_last_trade('BTC-USDT')
    #print(op)
    price=client.get_balance('USDT')
    print(price)
    

