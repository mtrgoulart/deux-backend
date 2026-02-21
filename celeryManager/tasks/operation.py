from celery import shared_task
from source.operation import execute_operation
from source.utils import normalize_exchange_response
from source.tracing import record_stage


@shared_task(name="trade.execute_operation", bind=True)
def task_execute_operation(self, data):
    """
    Execute trading operation on the exchange.

    This task interacts with the exchange API and supports two sizing modes:
    - percentage: Calculate size as percentage of balance (legacy mode)
    - flat_value: Use exact flat value amount

    Args:
        data: Dict containing operation parameters including size_mode and flat_value

    Returns:
        dict: Operation result with normalized exchange response
    """
    trace_id = data.get("trace_id")
    task_id = self.request.id
    record_stage(trace_id, "trade_execute", status="started", celery_task_id=task_id,
                 metadata={"exchange_id": data.get("exchange_id"),
                           "size_mode": data.get("size_mode", "percentage")})

    try:
        result = execute_operation(
            user_id=data.get("user_id"),
            api_key=data.get("api_key"),
            exchange_id=data.get("exchange_id"),
            perc_balance_operation=data.get("perc_balance_operation"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            instance_id=data.get("instance_id"),
            size_mode=data.get("size_mode", "percentage"),
            flat_value=data.get("flat_value"),
            trace_id=trace_id
        )

        result['order_response'] = normalize_exchange_response(result.get('order_response'))

        op_status = result.get("status", "")
        if op_status == "success":
            record_stage(trace_id, "trade_execute", status="completed",
                         metadata={"size": data.get("perc_balance_operation")})
        elif op_status in ("no_position", "insufficient_balance"):
            record_stage(trace_id, "trade_execute", status="skipped",
                         metadata={"reason": op_status})
        else:
            record_stage(trace_id, "trade_execute", status="failed",
                         error=result.get("error", result.get("message", "")))

        return result

    except Exception as e:
        record_stage(trace_id, "trade_execute", status="failed", error=str(e))
        raise