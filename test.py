import time
import requests
import hmac
from hashlib import sha256

APIURL = "https://open-api.bingx.com"
# Lembre-se de nunca expor suas chaves publicamente.
# Considere usar variáveis de ambiente.
API_KEY = "e6y2hfmpzmGRscXsIXI23dnrcRMMrOzLHNvTCfg8m9417bQ0cvUJOx1zhnpAGkNQMTsOZd9p3r2pBgcdaww"
SECRET_KEY = "I9rXxCSl2DiDWar693c32Ygg8eHUuMowHo3Mfx9Bu0UHKjaUEgZM5CCCRFIUD2x80OTsGkOI24i8gsxezNk6Q"

def demo():
    path = '/openApi/spot/v1/trade/order'
    method = "POST"
    
    # Parâmetros da requisição SEM o timestamp
    paramsMap = {
        "type": "MARKET",
        "symbol": "BTC-USDT",
        "side": "BUY",
        "quoteOrderQty": 10,
        # "newClientOrderId": "", # Opcional, pode ser removido se não usado
        # "recvWindow": 1000,     # Opcional
        # "timeInForce": "GTC",   # Opcional para ordens a mercado
    }
    
    # ADICIONADO: Gerar timestamp atual e adicioná-lo ao dicionário
    paramsMap['timestamp'] = int(time.time() * 1000)
    
    paramsStr = parseParam(paramsMap)
    return send_request(method, path, paramsStr)

def get_sign(api_secret, payload_str):
    signature = hmac.new(api_secret.encode("utf-8"), payload_str.encode("utf-8"), digestmod=sha256).hexdigest()
    print("String para assinar: " + payload_str)
    print("Assinatura gerada: " + signature)
    return signature

def send_request(method, path, params_str):
    signature = get_sign(SECRET_KEY, params_str)
    url = f"{APIURL}{path}?{params_str}&signature={signature}"
    
    print("URL final: " + url)
    
    headers = {
        'X-BX-APIKEY': API_KEY,
    }
    # Para POST, o payload (corpo da requisição) deve estar vazio, 
    # pois todos os parâmetros já estão na URL.
    response = requests.request(method, url, headers=headers, data={})
    return response.text

# FUNÇÃO SIMPLIFICADA
def parseParam(paramsMap):
    """
    Ordena os parâmetros e os formata em uma query string.
    Ex: key1=value1&key2=value2
    """
    sortedKeys = sorted(paramsMap)
    return "&".join([f"{x}={paramsMap[x]}" for x in sortedKeys])


if __name__ == '__main__':
    print("Resultado:", demo())