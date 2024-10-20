import requests

url_local = "http://127.0.0.1:5000/webhookcallback"
url_external = "https://74f2-2804-d57-6329-e600-31a9-8b1d-6f82-4642.ngrok-free.app"

# Exemplo de dados JSON em formato de string (texto)
json_data = '''{
    "symbol": "ETH-USDT",
    "type": "market",
    "size": 100,
    "side": "buy"
}'''

str_data='symbol=ETH-USDT, side=buy, indicator=1'



# Enviando o POST request com o corpo como texto
headers = {'Content-Type': 'application/json'}
headers_text = {'Content-Type': 'text/plain'}


# Teste com URL externa
r = requests.post(url_local, headers=headers_text, data=str_data)  # Usando 'data' ao invés de 'json'
print(r.status_code)
print(r.content)
