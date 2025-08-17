from celery import shared_task
from source.operation import execute_operation


# RENOMEAMOS a tarefa para ser mais específica e REMOVEMOS a chamada para save_operation_task
@shared_task(name="trade.execute_operation", queue="ops")
def task_execute_operation(data):
    """
    Executa a operação de trade na exchange.
    Esta tarefa é a primeira na cadeia e sua única responsabilidade
    é interagir com a API da exchange.
    Ela retorna um dicionário com o resultado da operação.
    """
    result = execute_operation(
        user_id=data.get("user_id"),
        api_key=data.get("api_key"),
        exchange_id=data.get("exchange_id"),
        perc_balance_operation=data.get("perc_balance_operation"),
        symbol=data.get("symbol"),
        side=data.get("side"),
        instance_id=data.get("instance_id")
    )
    return result