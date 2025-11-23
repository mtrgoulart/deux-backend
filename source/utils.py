# Em um arquivo como source/utils.py ou source/operation.py

def normalize_exchange_response(response):
    """
    Recebe a resposta crua da corretora e a normaliza para um formato de dicionário padrão.
    Isso garante que sempre salvaremos um objeto JSON no banco de dados.
    """
    # Se a resposta já for um dicionário, apenas a retornamos.
    if isinstance(response, dict):
        return response
    
    # Se for qualquer outra coisa (string, número, etc.), nós a empacotamos.
    # A chave 'raw_response' guarda o valor original para não perdermos informação.
    return {
        "raw_response": response,
        "response_type": type(response).__name__  # Guarda o tipo original (ex: 'str', 'int')
    }