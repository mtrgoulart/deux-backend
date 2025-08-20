# Em operation.py

from celery import shared_task
from source.operation import execute_operation
# Importe a nova função que você criou
from source.utils import normalize_exchange_response 

@shared_task(name="trade.execute_operation", queue="ops")
def task_execute_operation(data):
    """
    Executa a operação de trade na exchange e normaliza o resultado.
    """
    # 1. Executa a operação como antes
    result = execute_operation(
        user_id=data.get("user_id"),
        api_key=data.get("api_key"),
        exchange_id=data.get("exchange_id"),
        perc_balance_operation=data.get("perc_balance_operation"),
        symbol=data.get("symbol"),
        side=data.get("side"),
        instance_id=data.get("instance_id")
    )

    # 2. ANTES DE RETORNAR, NORMALIZA A RESPOSTA!
    # A chave 'order_response' agora conterá o resultado normalizado.
    result['order_response'] = normalize_exchange_response(result.get('order_response'))
    
    # 3. Retorna o resultado já com a resposta padronizada
    return result