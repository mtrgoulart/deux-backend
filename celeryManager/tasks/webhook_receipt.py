from celery import shared_task
from celeryManager.tasks.base import logger
from interface.webhook_auth import authenticate_signal, authenticate_user_key
from celeryManager.tasks.webhook_processor import process_webhook as process_webhook_task
from celeryManager.tasks.panic_processor import process_panic_signal as process_panic_task
from source.tracing import record_stage


@shared_task(name="webhook.receipt", bind=True)
def process_webhook_receipt(self, data):
    """
    Route webhook signals based on pattern (instance-level or user-level).

    Supports dual-pattern messages:
    - Instance-level (side): Routes to webhook.processor for buy/sell
    - User-level (process): Routes to panic.processor for panic/resume
    """
    task_id = self.request.id
    trace_id = data.get("trace_id")
    log_prefix = f"[WebhookTaskID: {task_id}]"
    if trace_id:
        log_prefix = f"[WebhookTaskID: {task_id}] [TraceID: {trace_id}]"

    logger.info(f"{log_prefix} Starting webhook processing.")
    record_stage(trace_id, "webhook_receipt", status="started", celery_task_id=task_id)

    try:
        key = data.get("key")
        pattern = data.get("pattern")
        action = data.get("action")

        if not key or not pattern or not action:
            logger.warning(f"{log_prefix} Missing parameters. Key: '{key}', Pattern: '{pattern}', Action: '{action}'.")
            record_stage(trace_id, "webhook_receipt", status="failed",
                         error="Missing parameters", is_terminal=True)
            return {"status": "error", "message": "Missing parameters"}

        if pattern == "instance":
            return _handle_instance_pattern(log_prefix, key, action, trace_id)

        elif pattern == "user":
            return _handle_user_pattern(log_prefix, key, action, trace_id)

        else:
            logger.warning(f"{log_prefix} Unknown pattern: {pattern}")
            record_stage(trace_id, "webhook_receipt", status="failed",
                         error=f"Unknown pattern: {pattern}", is_terminal=True)
            return {"status": "error", "message": f"Unknown pattern: {pattern}"}

    except Exception as e:
        logger.error(f"{log_prefix} Error in webhook receipt: {e}", exc_info=True)
        record_stage(trace_id, "webhook_receipt", status="failed",
                     error=str(e), is_terminal=True)
        raise


def _handle_instance_pattern(log_prefix, key, side, trace_id=None):
    """Handle instance-level pattern (buy/sell operations)."""
    if side not in ["buy", "sell"]:
        logger.warning(f"{log_prefix} Invalid side: '{side}'.")
        record_stage(trace_id, "webhook_receipt", status="failed",
                     error=f"Invalid side: {side}", is_terminal=True)
        return {"status": "error", "message": f"Invalid side: {side}"}

    signal_data = authenticate_signal(key)

    if not signal_data:
        logger.warning(f"{log_prefix} [Side: {side}] Instance key authentication failed: ...{key[-4:]}")
        record_stage(trace_id, "webhook_receipt", status="failed",
                     error="Invalid signal key", is_terminal=True)
        return {"status": "error", "message": "Invalid signal key"}

    signal_log = (
        f"[User: {signal_data['user_id']}] "
        f"[Instance: {signal_data['instance_id']}] "
        f"[Indicator: {signal_data['indicator_id']}] "
        f"[Symbol: {signal_data['symbol']}] "
        f"[Side: {side}]"
    )

    record_stage(trace_id, "webhook_receipt", status="completed",
                 metadata={"user_id": signal_data['user_id'],
                           "instance_id": signal_data['instance_id'],
                           "symbol": signal_data['symbol']},
                 user_id=signal_data['user_id'],
                 instance_id=signal_data['instance_id'],
                 symbol=signal_data['symbol'])

    signal_data['trace_id'] = trace_id

    delay_seconds = signal_data.get('delay_seconds')

    if delay_seconds and delay_seconds > 0:
        logger.info(f"{log_prefix} {signal_log} Signal authenticated. Scheduling deferred processing ({delay_seconds}s delay).")
        process_webhook_task.apply_async(
            kwargs={"signal_data": signal_data, "side": side, "original_key": key},
            countdown=delay_seconds
        )
    else:
        logger.info(f"{log_prefix} {signal_log} Signal authenticated. Delegating to logic queue.")
        process_webhook_task.delay(
            signal_data=signal_data,
            side=side,
            original_key=key
        )

    return {"status": "queued", "message": "Signal accepted and queued for processing."}


def _handle_user_pattern(log_prefix, key, action, trace_id=None):
    """Handle user-level pattern (panic/resume operations)."""
    valid_actions = ["panic_stop", "resume_restart", "resume_no_restart"]
    if action not in valid_actions:
        logger.warning(f"{log_prefix} Invalid process action: '{action}'.")
        record_stage(trace_id, "webhook_receipt", status="failed",
                     error=f"Invalid process action: {action}", is_terminal=True)
        return {"status": "error", "message": f"Invalid process action: {action}"}

    user_data = authenticate_user_key(key)

    if not user_data:
        logger.warning(f"{log_prefix} User key authentication failed: ...{key[-4:]}")
        record_stage(trace_id, "webhook_receipt", status="failed",
                     error="Invalid user key", is_terminal=True)
        return {"status": "error", "message": "Invalid user key"}

    logger.info(f"{log_prefix} User signal authenticated. Delegating to logic queue for user_id={user_data['user_id']}.")

    record_stage(trace_id, "webhook_receipt", status="completed",
                 metadata={"user_id": user_data['user_id']},
                 user_id=user_data['user_id'])

    process_panic_task.delay(
        user_id=user_data["user_id"],
        action=action,
        original_key=key,
        trace_id=trace_id
    )

    return {"status": "queued", "message": "Signal accepted and queued for processing."}