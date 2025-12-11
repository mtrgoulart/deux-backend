from celery import shared_task
from source.operation import execute_operation
from source.utils import normalize_exchange_response 


# RENOMEAMOS a tarefa para ser mais específica e REMOVEMOS a chamada para save_operation_task
@shared_task(name="trade.execute_operation")
def task_execute_operation(data):
    """
    Execute trading operation on the exchange.

    This task interacts with the exchange API and supports two sizing modes:
    - percentage: Calculate size as percentage of balance (legacy mode)
    - flat_value: Use exact flat value amount

    Args:
        data: Dict containing operation parameters including size_mode and flat_value

    Returns:
        dict: Operation result with normalized exchange response
    """
    result = execute_operation(
        user_id=data.get("user_id"),
        api_key=data.get("api_key"),
        exchange_id=data.get("exchange_id"),
        perc_balance_operation=data.get("perc_balance_operation"),
        symbol=data.get("symbol"),
        side=data.get("side"),
        instance_id=data.get("instance_id"),
        size_mode=data.get("size_mode", "percentage"),  # Default to percentage for backward compatibility
        flat_value=data.get("flat_value")
    )

    # 2. ANTES DE RETORNAR, NORMALIZA A RESPOSTA!
    # A chave 'order_response' agora conterá o resultado normalizado.
    result['order_response'] = normalize_exchange_response(result.get('order_response'))
    
    # 3. Retorna o resultado já com a resposta padronizada
    return result