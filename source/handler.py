import time
import hmac
import base64
import requests
import json
from datetime import datetime, timezone

class OKXClient:
    def __init__(self, config_loader, url='https://www.okx.com'):
        self.api_key = config_loader.get('okx', 'api_key')
        self.secret_key = config_loader.get('okx', 'secret_key')
        self.passphrase = config_loader.get('okx', 'passphrase')
        self.url = url

    def generate_signature(self, timestamp, method, request_path, body):
        message = timestamp + method + request_path + body
        mac = hmac.new(bytes(self.secret_key, 'utf-8'), bytes(message, 'utf-8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d).decode()

    def send_request(self, method, request_path, body):
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
        response = requests.request(method, self.url + request_path, headers=headers, data=body_str)

        #print(response.json())
        '''response_json = response.json()
        with open('response_output.txt', 'w') as file:
            file.write(json.dumps(response_json, indent=4))  # Salvando de forma legível'''
    
        return response.json()

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
        # Prepara o corpo da requisição
        body = {
            "ordId": order_id,
            "instId": symbol
            
        }
        # Consulta o status da ordem com os parâmetros 'symbol' e 'ordId'
        return self.send_request('GET', '/api/v5/trade/order', body)
    
    def get_balance(self, ccy=None):
    # Define os parâmetros da requisição
        params = {}
        if ccy:
            params['ccy'] = ccy

        # Envia a requisição GET com os parâmetros
        return self.send_request('GET', '/api/v5/account/balance', body=params)

if __name__=="__main__":
    from pp import ConfigLoader
    config=ConfigLoader(r'C:\Project\okx\venv\config.ini')
    client=OKXClient(config)
    response=client.get_order_status('BTC-USDT','1785573139386859520')
    print(response)