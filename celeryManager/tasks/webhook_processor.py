from celery import shared_task
from celeryManager.tasks.base import logger
from interface.instance import get_instance_status, execute_instance_operation
from interface.webhook_auth import insert_data_to_db


@shared_task(name="webhook.processor", bind=True)
def process_webhook(self, signal_data, side, original_key):
    """
    Process webhook signal and orchestrate trading operation.

    This task runs in the 'logic' queue and orchestrates the complete trading flow:
    1. Validates instance status (must be running)
    2. Persists webhook data to database
    3. Executes instance operation (which handles interval checking, condition validation,
       trade execution via 'ops' queue, and copy trading distribution via 'sharing' queue)

    The refactored architecture uses structured DTOs (OperationContext) internally
    to pass data cleanly through the execution pipeline, replacing scattered variables.

    Args:
        signal_data: Dict containing instance_id, user_id, symbol, indicator_id
        side: 'buy' or 'sell'
        original_key: Original webhook key for audit trail

    Returns:
        dict: Operation result with status and details
    """
    task_id = self.request.id
    instance_id = signal_data['instance_id']
    user_id = signal_data['user_id']
    symbol = signal_data.get('symbol')

    log_prefix = f"[TaskID: {task_id}] [Instance: {instance_id}] [User: {user_id}]"
    logger.info(f"{log_prefix} Starting webhook processing for {side} signal on {symbol}")

    try:
        # Validate instance exists and is running
        status = get_instance_status(instance_id, user_id)

        if status is None:
            logger.error(f"{log_prefix} Instance not found")
            return {"status": "error", "message": "Instance not found"}

        if status != 2:
            logger.info(f"{log_prefix} Instance not running (status={status}). Ignoring signal.")
            return {"status": "ignored", "message": f"Instance not running (status={status})"}

        # Persist webhook data to database
        logger.info(f"{log_prefix} Instance active. Persisting webhook data to DB.")
        db_data = {
            "key": original_key,
            "symbol": symbol,
            "side": side,
            "indicator_id": signal_data.get('indicator_id'),
            "instance_id": instance_id
        }
        insert_data_to_db(db_data)

        # Execute instance operation
        # This function now:
        # - Fetches instance and strategy data from DB
        # - Builds OperationContext DTO with all necessary data
        # - Validates interval constraints
        # - Checks trading conditions
        # - Sends trade task to 'ops' queue
        # - Sends copy trading task to 'sharing' queue (if applicable)
        logger.info(f"{log_prefix} Webhook data persisted. Executing operation.")
        result = execute_instance_operation(instance_id, user_id, side)
        logger.info(f"{log_prefix} Operation completed. Result: {result}")

        return result

    except Exception as e:
        logger.error(f"{log_prefix} Exception during webhook processing: {e}", exc_info=True)
        raise