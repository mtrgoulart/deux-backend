from celery import shared_task
from celeryManager.tasks.base import logger
from interface.instance import execute_shared_operations
from source.tracing import record_stage


@shared_task(name="process_sharing_operations", bind=True)
def process_sharing_operations(self, data):
    trace_id = data.get("trace_id")
    task_id = self.request.id
    record_stage(trace_id, "sharing", status="started", celery_task_id=task_id)

    try:
        share_id = data.get("share_id")
        user_id = data.get("user_id")
        symbol = data.get("symbol")
        side = data.get("side")
        perc_size = data.get("perc_size")
        size_mode = data.get("size_mode", "percentage")
        flat_value = data.get("flat_value")

        if not share_id or not user_id:
            record_stage(trace_id, "sharing", status="failed",
                         error="Missing share_id or user_id")
            return {"status": "error", "message": "Missing share_id or user_id"}

        result = execute_shared_operations(
            share_id, user_id, symbol, side, perc_size,
            size_mode=size_mode, flat_value=flat_value
        )

        if result.get("status") == "success":
            record_stage(trace_id, "sharing", status="completed",
                         metadata={"message": result.get("message", "")})
        elif "nenhum compartilhamento" in result.get("message", "").lower():
            record_stage(trace_id, "sharing", status="skipped",
                         metadata={"reason": result.get("message", "")})
        else:
            record_stage(trace_id, "sharing", status="failed",
                         error=result.get("message", ""))

        return result
    except Exception as e:
        logger.error(f"Erro operação compartilhada: {e}")
        record_stage(trace_id, "sharing", status="failed", error=str(e))
        return {"status": "error", "message": str(e)}
