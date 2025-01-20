import requests
import json

# URL do endpoint
url = "http://127.0.0.1:8095/start_operation"

# Função para enviar um POST
def send_post(data):
    try:
        response = requests.post(url, json=data)
        
        # Exibindo a resposta
        if response.status_code == 200:
            print("Operação iniciada com sucesso:", response.json())
        else:
            print("Erro ao iniciar operação:", response.status_code, response.json())
    except Exception as e:
        print(f"Erro ao conectar ao servidor: {e}")

# Dados do payloads e envio das requisições
payloads = [
    {
        "percent": 0.2,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "ETH-USDC",
        "side": "buy"
    },
    {
        "percent": 1,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "ETH-USDC",
        "side": "sell"
    },
    {
        "percent": 0.2,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "SOL-USDC",
        "side": "buy"
    },
    {
        "percent": 1,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "SOL-USDC",
        "side": "sell"
    },
    {
        "percent": 0.2,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "AVAX-USDC",
        "side": "buy"
    },
    {
        "percent": 1,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "AVAX-USDC",
        "side": "sell"
    },
    {
        "percent": 0.2,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "DOGE-USDC",
        "side": "buy"
    },
    {
        "percent": 1,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "DOGE-USDC",
        "side": "sell"
    },
    {
        "percent": 0.2,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "XRP-USDC",
        "side": "buy"
    },
    {
        "percent": 1,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "XRP-USDC",
        "side": "sell"
    },
    {
        "percent": 0.2,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "BTC-USDC",
        "side": "buy"
    },
    {
        "percent": 1,
        "avaiable_size": 50000,
        "condition_limit": 1,
        "interval": 60,
        "symbol": "BTC-USDC",
        "side": "sell"
    }
]



# Enviando cada payload
for data in payloads:
    send_post(data)
