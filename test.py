import requests
import json

# URL do webhook
url = "http://localhost:5004/webhook"

# Dados a serem enviados no formato JSON
data = {
    "data": "key=1,symbol=BTC-USDT,side=buy,indicator=1,instance_id=22"
}

# Headers indicando que o conteúdo é JSON
headers = {
    "Content-Type": "application/json"
}

# Enviando o POST request
response = requests.post(url, data=json.dumps(data), headers=headers)

# Exibir resposta do servidor
print(f"Status Code: {response.status_code}")
print(f"Response Body: {response.text}")
