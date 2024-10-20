import time
import hmac
import base64
import requests
import json
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .pp import LastOperation

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

    def place_order(self, symbol, side, order_type, size, price=None):
        print(f'\nSending Order: {symbol},{side},{order_type},{size}')
        body = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side,
            "ordType": order_type,
            "sz": size,
            "px": price,
            "tgtCcy": "quote_ccy",
        }
        return self.send_request('POST', '/api/v5/trade/order', body)

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
        body = {
            "instId": symbol,
            "limit": "100"
        }
        response = self.send_request('GET', '/api/v5/trade/fills', body)
        if response and response.get("code") == "0" and response.get("data"):
            sorted_trades = sorted(response['data'], key=lambda x: x['fillTime'], reverse=True)
            last_trade_data = sorted_trades[0]
            fill_time_ms = int(last_trade_data.get('fillTime'))
            fill_time = datetime.fromtimestamp(fill_time_ms / 1000)
            return LastOperation(
                fill_id=last_trade_data.get('tradeId'),
                order_id=last_trade_data.get('ordId'),
                symbol=last_trade_data.get('instId'),
                side=last_trade_data.get('side'),
                fill_size=last_trade_data.get('fillSz'),
                fill_price=last_trade_data.get('fillPx'),
                fee=last_trade_data.get('fee'),
                time=fill_time
            )
        else:
            return None

if __name__=="__main__":
    from pp import ConfigLoader
    config = ConfigLoader(r'C:\Project\okx\venv\config.ini')
    client = OKXClient(config)
    op = client.get_last_trade('BTC-USDT')
    if op:
        print(op.time)
    else:
        print("No trade data available.")
