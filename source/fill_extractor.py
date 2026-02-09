from decimal import Decimal
from log.log import general_logger


def extract_filled_base_qty(order_response):
    """
    Extract filled base currency quantity from an exchange order response.

    Each exchange returns a different response format. This function tries
    each known format sequentially and returns the first valid value found.

    Returns:
        Decimal: The filled base quantity, or Decimal('0') if extraction fails.
    """
    if not order_response:
        return Decimal('0')

    try:
        # Binance: direct dict from /api/v3/order
        # {"executedQty": "0.001", "status": "FILLED", ...}
        if isinstance(order_response, dict) and "executedQty" in order_response:
            qty = order_response["executedQty"]
            if qty and Decimal(str(qty)) > 0:
                general_logger.info(f"[FillExtractor] Binance format: executedQty={qty}")
                return Decimal(str(qty))

        # BingX: full response {"code": 0, "data": {"executedQty": "..."}}
        if isinstance(order_response, dict) and "data" in order_response:
            data = order_response["data"]
            if isinstance(data, dict) and "executedQty" in data:
                qty = data["executedQty"]
                if qty and Decimal(str(qty)) > 0:
                    general_logger.info(f"[FillExtractor] BingX format: executedQty={qty}")
                    return Decimal(str(qty))

        # Aster: formatted dict with raw_response key
        # {"order_id": ..., "raw_response": {"executedQty": "..."}}
        if isinstance(order_response, dict) and "raw_response" in order_response:
            raw = order_response["raw_response"]
            if isinstance(raw, dict) and "executedQty" in raw:
                qty = raw["executedQty"]
                if qty and Decimal(str(qty)) > 0:
                    general_logger.info(f"[FillExtractor] Aster format: executedQty={qty}")
                    return Decimal(str(qty))

        # Phemex: data dict with cumBaseQtyEv (scaled by 10^8)
        if isinstance(order_response, dict) and "cumBaseQtyEv" in order_response:
            raw_qty = int(order_response["cumBaseQtyEv"])
            if raw_qty > 0:
                qty = Decimal(raw_qty) / Decimal('100000000')
                general_logger.info(f"[FillExtractor] Phemex format: cumBaseQtyEv={raw_qty} -> {qty}")
                return qty

        # OKX: returns list [{"ordId": "...", "sCode": "0"}] — no fill data
        # Falls through to return 0, caller will use balance fallback

    except Exception as e:
        general_logger.warning(f"[FillExtractor] Error extracting filled qty: {e}")

    general_logger.info(f"[FillExtractor] Could not extract filled qty from response, returning 0")
    return Decimal('0')
