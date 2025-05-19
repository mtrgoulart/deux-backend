from celery import shared_task
from tasks.base import logger
from tasks.utils import insert_data_to_db
from interface.webhook_auth import authenticate_signal
from interface.instance import get_instance_status, execute_instance_operation

@shared_task(name="process_webhook")
def process_webhook(data):
    signal = data.get("signal")
    side = data.get("side")

    if not signal or not side:
        logger.info(f"Parâmetro ausente: signal={signal}, side={side}")
        return {"status": None, "message": "Parâmetros ausentes"}

    user_id, instance_id = authenticate_signal(signal)
    if not user_id or not instance_id:
        logger.warning(f"Chave de sinal inválida: {signal}")
        return {"status": "error", "message": "Invalid signal"}

    status = get_instance_status(instance_id, user_id)
    if status == 1:
        return {"status": None, "message": "Instance not running"}
    if status == 2:
        if side not in ["buy", "sell"]:
            return {"status": "error", "message": "Invalid side"}
        data["user_id"] = user_id
        data["instance_id"] = instance_id
        insert_data_to_db(data)
        return execute_instance_operation(instance_id, user_id, side)

    return {"status": "error", "message": f"Unknown status {status}"}
