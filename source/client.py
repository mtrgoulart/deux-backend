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
        query_string = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
        signature = hmac.new(self.secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        params['signature'] = signature
        return params

    def send_signed_request(self, method, endpoint, params=None):
        params = params or {}
        params['timestamp'] = int(time.time() * 1000)
        signed_params = self.sign(params)
        headers = {'X-MBX-APIKEY': self.api_key}
        try:
            if method == 'GET':
                res = self.session.get(self.url + endpoint, headers=headers, params=signed_params)
            else:
                res = self.session.post(self.url + endpoint, headers=headers, params=signed_params)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[Binance] Error: {e}")
            return None

    def get_current_price(self, symbol):
        try:
            response = self.session.get(f"{self.url}/api/v3/ticker/price", params={"symbol": symbol})
            return float(response.json()["price"])
        except:
            return None

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": size
        }
        if price:
            params["price"] = price
            params["timeInForce"] = "GTC"
        response = self.send_signed_request("POST", "/api/v3/order", params)
        return response.get("orderId") if response else None

    def wait_for_fill_price(self, order_id, symbol, check_interval=1, timeout=90):
        start_time = time.time()
        while time.time() - start_time <= timeout:
            order = self.get_order_status(symbol, order_id)
            if order and order.get("status") == "FILLED":
                return float(order.get("price", 0.0))
            time.sleep(check_interval)
        return 0.0

    def cancel_order(self, symbol, order_id):
        return self.send_signed_request("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def get_open_orders(self, symbol):
        return self.send_signed_request("GET", "/api/v3/openOrders", {"symbol": symbol})

    def get_order_status(self, symbol, order_id):
        return self.send_signed_request("GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def get_balance(self, asset=None):
        data = self.send_signed_request("GET", "/api/v3/account")
        if asset:
            balances = [x for x in data.get("balances", []) if x["asset"] == asset]
            return balances[0] if balances else None
        return data.get("balances", [])

    def get_last_trade(self, symbol):
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
    def __init__(self, credentials, base_url='https://open-api.bingx.com'):
        self.api_key = credentials['api_key']
        self.secret_key = credentials['secret_key']
        self.base_url = base_url
        self.session = requests.Session()

    def sign(self, params):
        query_string = urlencode(params)
        return hmac.new(self.secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def send_request(self, method, path, params=None):
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self.sign(params)
        headers = {
            'X-BX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}{path}"
        if method.upper() == 'GET':
            response = self.session.get(url, headers=headers, params=params)
        else:
            response = self.session.post(url, headers=headers, json=params)
        try:
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[BingX] Error: {e}")
            return None

    def get_current_price(self, symbol):
        path = '/openApi/spot/v1/ticker/price'
        return self.send_request('GET', path, {'symbol': symbol})

    def place_order(self, symbol, side, order_type, size, currency, price=None):
        path = '/openApi/spot/v1/trade/order'
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': size
        }
        if price:
            params['price'] = price
            params['timeInForce'] = 'GTC'
        result = self.send_request('POST', path, params)
        return result.get('data', {}).get('orderId')

    def wait_for_fill_price(self, order_id, symbol, check_interval=1, timeout=90):
        path = '/openApi/spot/v1/trade/query'
        start_time = time.time()
        while time.time() - start_time <= timeout:
            response = self.send_request('GET', path, {'symbol': symbol, 'orderId': order_id})
            if response and response.get('data', {}).get('status') == 'FILLED':
                return float(response['data'].get('price', 0.0))
            time.sleep(check_interval)
        return 0.0

    def cancel_order(self, symbol, order_id):
        path = '/openApi/spot/v1/trade/cancel'
        return self.send_request('POST', path, {'symbol': symbol, 'orderId': order_id})

    def get_open_orders(self, symbol):
        path = '/openApi/spot/v1/trade/openOrders'
        return self.send_request('GET', path, {'symbol': symbol})

    def get_order_status(self, symbol, order_id):
        path = '/openApi/spot/v1/trade/query'
        return self.send_request('GET', path, {'symbol': symbol, 'orderId': order_id})

    def get_balance(self):
        path = '/openApi/spot/v1/account/balance'
        return self.send_request('GET', path)

    def get_last_trade(self, symbol):
        path = '/openApi/spot/v1/trade/myTrades'
        response = self.send_request('GET', path, {'symbol': symbol, 'limit': 1})
        if response and response.get('data'):
            trade = response['data'][-1]
            return SimpleNamespace(
                id=trade.get('id'),
                order_id=trade.get('orderId'),
                symbol=trade.get('symbol'),
                price=trade.get('price'),
                qty=trade.get('qty'),
                time=datetime.fromtimestamp(int(trade.get('time', 0)) / 1000),
                is_buyer=trade.get('isBuyer')
            )
        return None

    def get_recent_trades_last_7_days(self, symbol):
        path = '/openApi/spot/v1/trade/myTrades'
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        seven_days_ago = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
        all_trades = []

        params = {
            'symbol': symbol,
            'startTime': seven_days_ago,
            'endTime': now,
            'limit': 100
        }

        response = self.send_request('GET', path, params)
        trades = response.get('data', [])
        if trades:
            all_trades.extend(trades)
            with open('bingx_trades.csv', 'w', newline='') as csvfile:
                fieldnames = list(trades[0].keys()) + ['datetime']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for trade in trades:
                    trade['datetime'] = datetime.fromtimestamp(int(trade['time']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow(trade)
        return all_trades
