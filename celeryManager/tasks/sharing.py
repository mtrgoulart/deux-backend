from celery import shared_task
from celeryManager.tasks.base import logger
from interface.instance import execute_shared_operations

@shared_task(name="process_sharing_operations")
def process_sharing_operations(data):
    try:
        share_id = data.get("share_id")
        user_id = data.get("user_id")
        symbol = data.get("symbol")
        side = data.get("side")
        perc_size = data.get("perc_size")

        if not share_id or not user_id:
            return {"status": "error", "message": "Missing share_id or user_id"}

        return execute_shared_operations(share_id, user_id, symbol, side, perc_size)
    except Exception as e:
        logger.error(f"Erro operação compartilhada: {e}")
        return {"status": "error", "message": str(e)}
