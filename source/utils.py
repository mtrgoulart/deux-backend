import json

# Em um arquivo como source/utils.py ou source/operation.py

_SENSITIVE_KEYS = frozenset({
    'api_key', 'secret_key', 'passphrase', 'signature', 'sign',
    'OK-ACCESS-KEY', 'OK-ACCESS-SIGN', 'OK-ACCESS-PASSPHRASE',
    'X-MBX-APIKEY', 'X-BX-APIKEY',
})


def sanitize_trace_response(response, max_size=10000):
    """Strip sensitive keys and cap size for safe JSONB storage in traces."""
    if response is None:
        return None
    if not isinstance(response, (dict, list)):
        return {"raw_value": str(response)[:500]}

    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items() if k not in _SENSITIVE_KEYS}
        elif isinstance(obj, list):
            return [_clean(item) for item in obj[:50]]
        elif isinstance(obj, str) and len(obj) > 500:
            return obj[:500] + "...[truncated]"
        return obj

    cleaned = _clean(response)
    serialized = json.dumps(cleaned, default=str)
    if len(serialized) > max_size:
        return {"_truncated": True, "_message": f"Response exceeded {max_size} byte limit"}
    return cleaned


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