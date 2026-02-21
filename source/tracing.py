"""
Signal pipeline tracing module.

Provides lightweight functions for tracking webhook signals through the
processing pipeline. All functions are fire-and-forget — tracing failures
never interrupt the main pipeline.
"""

import uuid
import json
from datetime import datetime, timezone
from log.log import general_logger


def generate_trace_id():
    """Generate a 32-char hex trace ID."""
    return uuid.uuid4().hex


def create_trace(trace_id, pattern, action, key_suffix):
    """
    Insert the initial signal_traces row with the first stage.

    Args:
        trace_id: 32-char hex identifier
        pattern: 'instance' or 'user'
        action: the side or process value (buy, sell, panic_stop, etc.)
        key_suffix: last 4 chars of the signal key (for display)
    """
    try:
        from source.context import get_db_connection

        initial_stage = json.dumps([{
            "stage": "webhook_received",
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"pattern": pattern, "action": action}
        }])

        query = """
            INSERT INTO signal_traces (trace_id, pattern, signal_key_suffix, side, stages)
            VALUES (%s, %s, %s, %s, %s::jsonb)
        """

        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (
                trace_id, pattern, key_suffix, action, initial_stage
            ))
            db_client.conn.commit()

    except Exception as e:
        general_logger.warning(f"[Tracing] Failed to create trace {trace_id}: {e}")


def record_stage(trace_id, stage_name, status="completed", celery_task_id=None,
                 metadata=None, error=None, is_terminal=False,
                 user_id=None, instance_id=None, symbol=None):
    """
    Append a stage entry to the signal_traces row and update metadata.

    Exits immediately if trace_id is None (backward compatibility).

    Args:
        trace_id: The trace identifier (or None to skip)
        stage_name: Pipeline stage name (e.g. 'webhook_receipt')
        status: 'started', 'completed', 'failed', 'skipped'
        celery_task_id: Optional Celery task ID
        metadata: Optional dict of stage-specific metadata
        error: Optional error message string
        is_terminal: If True, sets final_status and completed_at
        user_id: Optional user_id to set on the trace row
        instance_id: Optional instance_id to set on the trace row
        symbol: Optional symbol to set on the trace row
    """
    if trace_id is None:
        return

    try:
        from source.context import get_db_connection

        stage_entry = {
            "stage": stage_name,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if celery_task_id:
            stage_entry["celery_task_id"] = celery_task_id
        if metadata:
            stage_entry["metadata"] = metadata
        if error:
            stage_entry["error"] = error

        # Build dynamic UPDATE
        set_clauses = [
            "stages = stages || %s::jsonb",
            "current_stage = %s",
            "updated_at = NOW()"
        ]
        params = [json.dumps([stage_entry]), stage_name]

        if is_terminal:
            final_status = "failed" if status == "failed" else "completed"
            if status == "skipped":
                final_status = "skipped"
            set_clauses.append("final_status = %s")
            params.append(final_status)
            set_clauses.append("completed_at = NOW()")

        if error:
            set_clauses.append("error_message = %s")
            params.append(error)

        if user_id is not None:
            set_clauses.append("user_id = %s")
            params.append(user_id)

        if instance_id is not None:
            set_clauses.append("instance_id = %s")
            params.append(instance_id)

        if symbol is not None:
            set_clauses.append("symbol = %s")
            params.append(symbol)

        params.append(trace_id)

        query = f"UPDATE signal_traces SET {', '.join(set_clauses)} WHERE trace_id = %s"

        with get_db_connection() as db_client:
            db_client.cursor.execute(query, tuple(params))
            db_client.conn.commit()

    except Exception as e:
        general_logger.warning(f"[Tracing] Failed to record stage '{stage_name}' for {trace_id}: {e}")
