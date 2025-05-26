from celery import shared_task
from celeryManager.tasks.base import logger
from interface.webhook_auth import authenticate_signal,insert_data_to_db
from interface.instance import get_instance_status, execute_instance_operation

@shared_task(name="process_webhook", queue="webhook")
def process_webhook(data):
    key = data.get("key")
    side = data.get("side")

    if not key or not side:
        logger.info(f"Parâmetro ausente: key={key}, side={side}")
        return {"status": None, "message": "Parâmetros ausentes"}

    signal_data = authenticate_signal(key)
    if not signal_data:
        logger.warning(f"Chave de sinal inválida: {key}")
        return {"status": "error", "message": "Invalid signal"}

    user_id = signal_data['user_id']
    instance_id = signal_data['instance_id']
    symbol = signal_data.get('symbol')
    indicator_id = signal_data.get('indicator_id')

    status = get_instance_status(instance_id, user_id)
    if status is None:
        return {"status": "error", "message": "Instance not found"}

    if status == 1:
        return {"status": None, "message": "Instance not running"}

    if status == 2:
        if side not in ["buy", "sell"]:
            return {"status": "error", "message": "Invalid side"}
        
        # Prepara os dados específicos para inserção no banco
        db_data = {
            "key": key,
            "symbol": symbol,
            "side": side,
            "indicator_id": indicator_id,
            "instance_id": instance_id
        }
        
        insert_data_to_db(db_data)
        return execute_instance_operation(instance_id, user_id, side)

    return {"status": "error", "message": f"Unknown status {status}"}
