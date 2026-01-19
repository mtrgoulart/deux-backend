from celery import shared_task
from celeryManager.tasks.base import logger
from interface.webhook_auth import authenticate_signal, authenticate_user_key
from celeryManager.tasks.webhook_processor import process_webhook as process_webhook_task
from celeryManager.tasks.panic_processor import process_panic_signal as process_panic_task


@shared_task(name="webhook.receipt", bind=True)
def process_webhook_receipt(self, data):
    """
    Route webhook signals based on pattern (instance-level or user-level).

    Supports dual-pattern messages:
    - Instance-level (side): Routes to webhook.processor for buy/sell
    - User-level (process): Routes to panic.processor for panic/resume
    """
    task_id = self.request.id
    log_prefix = f"[WebhookTaskID: {task_id}]"
    logger.info(f"{log_prefix} Starting webhook processing.")

    try:
        key = data.get("key")
        pattern = data.get("pattern")
        action = data.get("action")

        if not key or not pattern or not action:
            logger.warning(f"{log_prefix} Missing parameters. Key: '{key}', Pattern: '{pattern}', Action: '{action}'.")
            return {"status": "error", "message": "Missing parameters"}

        if pattern == "instance":
            # Instance-level flow: authenticate instance key -> webhook.processor
            return _handle_instance_pattern(log_prefix, key, action)

        elif pattern == "user":
            # User-level flow: authenticate user key -> panic.processor
            return _handle_user_pattern(log_prefix, key, action)

        else:
            logger.warning(f"{log_prefix} Unknown pattern: {pattern}")
            return {"status": "error", "message": f"Unknown pattern: {pattern}"}

    except Exception as e:
        logger.error(f"{log_prefix} Error in webhook receipt: {e}", exc_info=True)
        raise


def _handle_instance_pattern(log_prefix, key, side):
    """Handle instance-level pattern (buy/sell operations)."""
    if side not in ["buy", "sell"]:
        logger.warning(f"{log_prefix} Invalid side: '{side}'.")
        return {"status": "error", "message": f"Invalid side: {side}"}

    signal_data = authenticate_signal(key)

    if not signal_data:
        logger.warning(f"{log_prefix} Instance key authentication failed: ...{key[-4:]}")
        return {"status": "error", "message": "Invalid signal key"}

    logger.info(f"{log_prefix} Instance signal authenticated. Delegating to logic queue.")

    process_webhook_task.delay(
        signal_data=signal_data,
        side=side,
        original_key=key
    )

    return {"status": "queued", "message": "Signal accepted and queued for processing."}


def _handle_user_pattern(log_prefix, key, action):
    """Handle user-level pattern (panic/resume operations)."""
    valid_actions = ["panic_stop", "resume_restart", "resume_no_restart"]
    if action not in valid_actions:
        logger.warning(f"{log_prefix} Invalid process action: '{action}'.")
        return {"status": "error", "message": f"Invalid process action: {action}"}

    user_data = authenticate_user_key(key)

    if not user_data:
        logger.warning(f"{log_prefix} User key authentication failed: ...{key[-4:]}")
        return {"status": "error", "message": "Invalid user key"}

    logger.info(f"{log_prefix} User signal authenticated. Delegating to logic queue for user_id={user_data['user_id']}.")

    process_panic_task.delay(
        user_id=user_data["user_id"],
        action=action,
        original_key=key
    )

    return {"status": "queued", "message": "Signal accepted and queued for processing."}