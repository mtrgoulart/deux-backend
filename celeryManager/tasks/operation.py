from celery import shared_task
from interface.instance import execute_operation
from celeryManager.tasks.save import save_operation_task

@shared_task(name="process_operation", queue="ops")
def process_operation(data):
    result = execute_operation(
        user_id=data.get("user_id"),
        api_key=data.get("api_key"),
        exchange_id=data.get("exchange_id"),
        perc_balance_operation=data.get("perc_balance_operation"),
        symbol=data.get("symbol"),
        side=data.get("side")
    )

    save_operation_task.delay(
        user_id=result.get("user_id"),
        api_key=result.get("api_key"),
        symbol=result.get("symbol"),
        side=result.get("side"),
        size=result.get("size", 0),
        price=result.get("price"),
        instance_id=result.get("instance_id"),
        status=result.get("status")
    )

