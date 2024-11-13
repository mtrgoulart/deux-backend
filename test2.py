import requests

def get_all_inst_ids():
    url = "https://www.okx.com/api/v5/public/instruments"
    params = {
        "instType": "SPOT"  # Tipo de instrumento: 'SPOT' para mercado à vista (pode ajustar conforme necessário)
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json().get("data", [])
        inst_ids = [item["instId"] for item in data]
        return inst_ids
    else:
        print(f"Erro ao buscar dados: {response.status_code}")
        return []

# Exemplo de uso
inst_ids = get_all_inst_ids()
print(inst_ids)
