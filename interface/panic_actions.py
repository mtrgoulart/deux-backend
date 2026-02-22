"""
Panic actions interface for user-level operations.

Handles panic stop (sell all positions, stop instances) and resume operations
triggered via user-level webhook keys.
"""
import json
from source.dbmanager import load_query
from source.context import get_db_connection
from celeryManager.celery_app import celery as celery_app
from log.log import general_logger

# Instance status constants
STATUS_STOPPED = 1
STATUS_RUNNING = 2


def execute_panic_stop(user_id):
    """
    Execute panic stop: sell all positions, stop all instances, activate panic mode.

    Args:
        user_id: The user ID

    Returns:
        dict: Result with status and details
    """
    try:
        # 0. Skip if panic mode is already active
        panic_state = _get_panic_state(user_id)
        if panic_state and panic_state.get("is_panic_active"):
            general_logger.info(f"[PanicStop] User {user_id} already in panic mode — skipping.")
            return {"status": "skipped", "message": "Panic mode already active"}

        # 1. Get all active (running) instances for the user
        active_instance_ids = _get_active_instance_ids(user_id)

        if not active_instance_ids:
            general_logger.info(f"[PanicStop] User {user_id} has no active instances to stop.")
            return {"status": "success", "message": "No active instances to stop", "instances_stopped": 0}

        # 2. For each instance, send a sell order and stop the instance
        sell_orders_sent = 0
        instances_stopped = []

        for instance_id in active_instance_ids:
            # Get instance details for the sell operation
            instance_details = _get_instance_details_for_operation(instance_id, user_id)

            if instance_details:
                # Send sell order via trade.execute_operation task
                operation_data = {
                    "user_id": user_id,
                    "api_key": instance_details["api_key"],
                    "exchange_id": instance_details["exchange_id"],
                    "perc_balance_operation": 1,
                    "symbol": instance_details["symbol"],
                    "side": "sell",
                    "instance_id": instance_id,
                    "size_mode": "percentage",
                    "flat_value": None
                }

                celery_app.send_task("trade.execute_operation", kwargs={"data": operation_data})
                sell_orders_sent += 1
                general_logger.info(f"[PanicStop] Sell order sent for user {user_id}, instance {instance_id}, symbol {instance_details['symbol']}")

            # Stop the instance
            _update_instance_status(instance_id, user_id, STATUS_STOPPED, starting=False)
            instances_stopped.append(instance_id)
            general_logger.info(f"[PanicStop] Instance {instance_id} stopped.")

        # 3. Activate panic mode
        _activate_panic_mode(user_id, instances_stopped)

        general_logger.info(f"[PanicStop] User {user_id} panic stop completed. {sell_orders_sent} sell orders sent, {len(instances_stopped)} instances stopped.")

        return {
            "status": "success",
            "message": "Panic stop executed",
            "sell_orders_sent": sell_orders_sent,
            "instances_stopped": len(instances_stopped)
        }

    except Exception as e:
        general_logger.error(f"[PanicStop] Error executing panic stop for user {user_id}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def execute_resume(user_id, restart_instances):
    """
    Execute resume: exit panic mode, optionally restart instances.

    Args:
        user_id: The user ID
        restart_instances: Whether to restart the instances that were stopped

    Returns:
        dict: Result with status and details
    """
    try:
        # 1. Check if user is in panic mode
        panic_state = _get_panic_state(user_id)

        if not panic_state or not panic_state.get("is_panic_active"):
            general_logger.info(f"[Resume] User {user_id} is not in panic mode.")
            return {"status": "success", "message": "User is not in panic mode", "instances_restarted": 0}

        instances_restarted = 0

        # 2. If restart_instances is True, restart the instances that were stopped
        if restart_instances:
            stopped_instances = panic_state.get("instances_stopped_json")
            if stopped_instances:
                # Parse JSON if it's a string
                if isinstance(stopped_instances, str):
                    stopped_instances = json.loads(stopped_instances)

                for instance_id in stopped_instances:
                    _update_instance_status(instance_id, user_id, STATUS_RUNNING, starting=True)
                    instances_restarted += 1
                    general_logger.info(f"[Resume] Instance {instance_id} restarted.")

        # 3. Deactivate panic mode
        _deactivate_panic_mode(user_id)

        action = "resume_restart" if restart_instances else "resume_no_restart"
        general_logger.info(f"[Resume] User {user_id} {action} completed. {instances_restarted} instances restarted.")

        return {
            "status": "success",
            "message": f"Resume executed ({action})",
            "instances_restarted": instances_restarted
        }

    except Exception as e:
        general_logger.error(f"[Resume] Error executing resume for user {user_id}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# === Helper Functions ===

def _get_active_instance_ids(user_id):
    """Get list of active (running) instance IDs for a user."""
    query = load_query("select_active_instances_by_user.sql")

    with get_db_connection() as db_client:
        result = db_client.fetch_data(query, (user_id,))
        if result:
            return [row[0] for row in result]
        return []


def _get_instance_details_for_operation(instance_id, user_id):
    """Get instance details needed for executing a sell operation."""
    query = load_query("select_instance_details_for_operation.sql")

    with get_db_connection() as db_client:
        result = db_client.fetch_data(query, (user_id, instance_id))
        if result:
            row = result[0]
            return {
                "api_key": row[0],
                "exchange_id": row[1],
                "symbol": row[2]
            }
        return None


def _update_instance_status(instance_id, user_id, status, starting=False):
    """Update instance status (stop or start)."""
    if starting:
        query = load_query("update_starting_instance.sql")
    else:
        query = load_query("update_stopping_instance.sql")

    with get_db_connection() as db_client:
        db_client.update_data(query, (status, instance_id, user_id))


def _get_panic_state(user_id):
    """Get current panic state for a user."""
    query = load_query("get_panic_state.sql")

    with get_db_connection() as db_client:
        result = db_client.fetch_data(query, (user_id,))
        if result:
            row = result[0]
            return {
                "user_id": row[0],
                "is_panic_active": row[1],
                "panic_activated_at": row[2],
                "instances_stopped_json": row[3]
            }
        return None


def _activate_panic_mode(user_id, instance_ids):
    """Activate panic mode and record stopped instances."""
    query = load_query("activate_panic_mode.sql")
    instances_json = json.dumps(instance_ids)

    with get_db_connection() as db_client:
        db_client.insert_data(query, (user_id, instances_json))


def _deactivate_panic_mode(user_id):
    """Deactivate panic mode."""
    query = load_query("deactivate_panic_mode.sql")

    with get_db_connection() as db_client:
        db_client.update_data(query, (user_id,))
