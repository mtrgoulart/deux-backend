from celery import shared_task
from source.operation import execute_operation
from source.utils import normalize_exchange_response, sanitize_trace_response
from source.tracing import record_stage


def _build_exchange_request(data, result):
    """Reconstruct the logical exchange request from task parameters."""
    request = {
        "symbol": data.get("symbol"),
        "side": data.get("side"),
        "order_type": "market",
        "size_mode": data.get("size_mode", "percentage"),
    }
    if data.get("size_mode") == "flat_value":
        request["flat_value"] = data.get("flat_value")
    else:
        request["percentage"] = data.get("perc_balance_operation")
    if result.get("size"):
        request["computed_size"] = result["size"]
    if result.get("currency"):
        request["currency"] = result["currency"]
    return request


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
        if op_status == "success" and result.get("size"):
            exchange_request = _build_exchange_request(data, result)
            exchange_response = sanitize_trace_response(result.get('order_response'))
            record_stage(trace_id, "trade_execute", status="completed",
                         metadata={
                             "size": result.get("size", data.get("perc_balance_operation")),
                             "currency": result.get("currency"),
                             "exchange_request": exchange_request,
                             "exchange_response": exchange_response,
                         })
        elif op_status == "success":
            # Zero-size result — trade_save won't be dispatched
            record_stage(trace_id, "trade_execute", status="skipped",
                         is_terminal=True,
                         metadata={"reason": "zero_size"})
        elif op_status == "no_position":
            record_stage(trace_id, "trade_execute", status="skipped",
                         metadata={"reason": op_status})
        elif op_status == "insufficient_balance":
            record_stage(trace_id, "trade_execute", status="skipped",
                         is_terminal=True,
                         metadata={"reason": op_status})
        else:
            record_stage(trace_id, "trade_execute", status="failed",
                         is_terminal=True,
                         error=result.get("error", result.get("message", "")))

        return result

    except Exception as e:
        record_stage(trace_id, "trade_execute", status="failed", error=str(e))
        raise