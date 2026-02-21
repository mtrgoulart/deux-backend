"""
Panic processor task for user-level operations.

Handles panic stop and resume operations triggered via user-level webhook keys.
"""
from celery import shared_task
from celeryManager.tasks.base import logger
from interface.panic_actions import execute_panic_stop, execute_resume
from source.tracing import record_stage


@shared_task(name="panic.processor", bind=True)
def process_panic_signal(self, user_id, action, original_key, trace_id=None):
    """
    Process user-level panic/resume signals.

    Routes to appropriate handler based on process action.

    Args:
        user_id: The authenticated user ID
        action: The process action (panic_stop, resume_restart, resume_no_restart)
        original_key: The original webhook key (for logging)
        trace_id: Optional trace ID for pipeline observability
    """
    task_id = self.request.id
    log_prefix = f"[PanicTaskID: {task_id}]"
    if trace_id:
        log_prefix = f"[PanicTaskID: {task_id}] [TraceID: {trace_id}]"

    logger.info(f"{log_prefix} Processing user-level signal: action={action}, user_id={user_id}")
    record_stage(trace_id, "panic_processor", status="started", celery_task_id=task_id)

    try:
        handlers = {
            "panic_stop": lambda: execute_panic_stop(user_id),
            "resume_restart": lambda: execute_resume(user_id, restart_instances=True),
            "resume_no_restart": lambda: execute_resume(user_id, restart_instances=False),
        }

        handler = handlers.get(action)
        if not handler:
            logger.error(f"{log_prefix} Unknown action: {action}")
            record_stage(trace_id, "panic_processor", status="failed",
                         error=f"Unknown action: {action}", is_terminal=True)
            return {"status": "error", "message": f"Unknown action: {action}"}

        result = handler()

        logger.info(f"{log_prefix} Action {action} completed: {result}")
        record_stage(trace_id, "panic_processor", status="completed",
                     metadata={"action": action}, is_terminal=True)
        return result

    except Exception as e:
        logger.error(f"{log_prefix} Error processing panic signal: {e}", exc_info=True)
        record_stage(trace_id, "panic_processor", status="failed",
                     error=str(e), is_terminal=True)
        return {"status": "error", "message": str(e)}
