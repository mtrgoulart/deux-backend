from source.operation import execute_operation as execute_operation_source

def execute_operation(user_id, api_key, exchange_id, perc_balance_operation, symbol, side, instance_id):
    """
    Interface entre as tasks Celery e a lógica de operação no módulo source.
    """
    return execute_operation_source(
        user_id=user_id,
        api_key=api_key,
        exchange_id=exchange_id,
        perc_balance_operation=perc_balance_operation,
        symbol=symbol,
        side=side,
        instance_id=instance_id
    )
