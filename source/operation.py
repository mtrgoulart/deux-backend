import re
import time
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from source.exchange_interface import get_exchange_interface
from log.log import general_logger
from source.celery_client import get_client
from source.position import get_open_position
from source.fill_extractor import extract_filled_base_qty
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone

def parse_symbol(symbol: str):
    quote_currencies = [
        "USDT", "USDC", "TUSD", "BUSD", "FDUSD",
        "BTC", "ETH", "BNB", "XRP", "EUR", "GBP", "JPY", "AUD", "BRL"
        ]

    base_currency = None
    quote_currency = None

    # 1. Tenta o padrão "moeda_base-moeda_cotacao"
    match = re.match(r"^([^-]+)-([^-]+)$", symbol)
    if match:
        return match.groups()
    else:
        for qc in quote_currencies:
            if symbol.endswith(qc):
                base_currency = symbol[:-len(qc)]
                quote_currency = qc
                break
        return (base_currency,quote_currency)


def calculate_order_size(balance, percentage):
    if not isinstance(balance, (int, float, Decimal)):
        raise TypeError(f"Tipo inválido de saldo: {type(balance)}")
    size = float(balance) * float(percentage)
    if size <= 0:
        raise ValueError("Tamanho da ordem é zero ou negativo.")
    return size

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def call_place_order(exchange_interface, symbol, side, size, currency):
    return exchange_interface.place_order(
        symbol=symbol,
        side=side,
        order_type='market',
        size=size,
        currency=currency
    )

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def call_get_balance(exchange_interface, currency):
    return exchange_interface.get_balance(currency)

def execute_operation(user_id, api_key, exchange_id, perc_balance_operation, symbol, side, instance_id, max_amount_size=None, size_mode="percentage", flat_value=None):
    """
    Execute a trading operation on the exchange.

    BUY: Uses percentage/flat_value sizing modes against quote currency balance.
    SELL: Sells 100% of the accumulated position tracked in spot_position_entries,
          capped by exchange balance for safety.

    Args:
        user_id: User ID
        api_key: API key ID
        exchange_id: Exchange ID
        perc_balance_operation: Percentage of balance (used in percentage mode for buys)
        symbol: Trading symbol
        side: 'buy' or 'sell'
        instance_id: Instance ID
        max_amount_size: Maximum size limit (optional, for copy trading)
        size_mode: "percentage" or "flat_value"
        flat_value: Exact amount to trade (used in flat_value mode for buys)

    Returns:
        dict: Operation result with status and details
    """
    start_time = time.time()
    status = "FAILED"
    exchange_name = f"Exchange:{exchange_id}"
    size = None
    ccy = None
    balance_raw = None

    try:
        base_currency, quote_currency = parse_symbol(symbol)
        exchange_interface = get_exchange_interface(exchange_id, user_id, api_key)
        exchange_name = getattr(exchange_interface, 'exchange_name', exchange_name)

        # Log header
        general_logger.info("=" * 80)
        general_logger.info(f"OPERATION START | {exchange_name} | user:{user_id} | inst:{instance_id} | {symbol} | {side.upper()}")
        general_logger.info("-" * 80)

        if side == 'sell':
            # === SELL PATH: Position-based selling ===
            ccy = base_currency

            # Query accumulated position from spot_position_entries
            position_qty, entry_ids = get_open_position(instance_id, user_id, symbol)

            if position_qty <= 0:
                general_logger.info(f"  Mode: POSITION_SELL | Position: 0 | No open entries found")
                general_logger.info("-" * 80)
                general_logger.info("  Order skipped: No position to sell")
                status = "SKIPPED"
                return {"status": "no_position", "message": "No open position entries found for this instance."}

            # Get exchange balance as safety cap
            balance_raw = call_get_balance(exchange_interface, ccy)
            exchange_balance = Decimal(str(balance_raw))

            # Use min of position and exchange balance
            size = min(position_qty, exchange_balance)

            general_logger.info(f"  Mode: POSITION_SELL | Position: {position_qty.normalize()} | Exchange Balance: {exchange_balance.normalize()} | Sell Size: {size.normalize()}")
            general_logger.info("-" * 80)

            if size <= 0:
                general_logger.info("  Order skipped: Effective sell size is zero")
                status = "SKIPPED"
                return {
                    "status": "success",
                    "message": "Effective sell size is zero (exchange balance is 0). No operation performed."
                }

            # Place sell order
            size_float = float(size)
            order_response = call_place_order(exchange_interface, symbol, side, size_float, ccy)
            executed_at_utc = datetime.now(timezone.utc)

            general_logger.info("  Order sent successfully")
            status = "SUCCESS"

            operation_data = {
                "status": "realizada",
                "user_id": user_id,
                "api_key": api_key,
                "symbol": symbol,
                "side": side,
                "size": size_float,
                "order_response": order_response,
                "instance_id": instance_id,
                "executed_at": executed_at_utc.isoformat(),
                "entry_ids": entry_ids,
            }
            get_client().send_task(
                "trade.save_operation",
                kwargs={"operation_data": operation_data},
                queue='db'
            )

            return {"status": "success", "message": "Operação executada e tarefa de salvamento enfileirada."}

        else:
            # === BUY PATH: Percentage/flat_value sizing with fill extraction ===
            ccy = quote_currency

            # Get pre-buy base currency balance for fill fallback
            pre_buy_base_balance = None
            try:
                pre_buy_base_raw = call_get_balance(exchange_interface, base_currency)
                pre_buy_base_balance = Decimal(str(pre_buy_base_raw))
            except Exception as e:
                general_logger.warning(f"  Could not get pre-buy base balance for fallback: {e}")

            # Get quote currency balance
            balance_raw = call_get_balance(exchange_interface, ccy)
            balance = Decimal(str(balance_raw))

            # Calculate order size based on mode
            if size_mode == "flat_value":
                # FLAT VALUE MODE: Use exact amount specified
                if flat_value is None or flat_value <= 0:
                    general_logger.info(f"  Mode: {size_mode} | flat_value invalid: {flat_value}")
                    general_logger.info(f"  Balance: {balance_raw} {ccy}")
                    general_logger.info("-" * 80)
                    general_logger.error("  Order FAILED: flat_value must be a positive number")
                    return {
                        "status": "error",
                        "message": "flat_value must be a positive number when size_mode is 'flat_value'"
                    }

                size = Decimal(str(flat_value))

                # Log mode details
                general_logger.info(f"  Mode: {size_mode} | Size: {size:.2f} {ccy} | Percentage: {perc_balance_operation * 100}%")
                general_logger.info(f"  Balance: {balance_raw} {ccy}")
                general_logger.info("-" * 80)

                # Check if balance is sufficient for flat value
                if balance < size:
                    general_logger.error(f"  Order FAILED: Insufficient balance. Required: {size}, Available: {balance}")
                    return {
                        "status": "insufficient_balance",
                        "message": f"Insufficient balance. Required: {size}, Available: {balance}"
                    }

            else:
                # PERCENTAGE MODE: Calculate based on balance percentage (legacy mode)
                base_para_calculo = balance

                # Apply max_amount_size limit if specified (for copy trading)
                if max_amount_size is not None:
                    if balance < max_amount_size:
                        general_logger.info(f"  Mode: {size_mode} | Percentage: {perc_balance_operation * 100}% | max_amount_size: {max_amount_size}")
                        general_logger.info(f"  Balance: {balance_raw} {ccy}")
                        general_logger.info("-" * 80)
                        general_logger.error(f"  Order FAILED: Insufficient balance for max_amount_size. Balance: {balance}, Required: {max_amount_size}")
                        return {
                            "status": "insufficient_balance",
                            "message": "Insufficient balance to cover max_amount_size."
                        }

                    base_para_calculo = max_amount_size

                # Calculate size as percentage of balance
                perc_decimal = Decimal(str(perc_balance_operation))
                size = base_para_calculo * perc_decimal

                # Log mode details
                general_logger.info(f"  Mode: {size_mode} | Size: {size:.2f} {ccy} | Percentage: {perc_balance_operation * 100}%")
                general_logger.info(f"  Balance: {balance_raw} {ccy}")
                general_logger.info("-" * 80)

            # Validate calculated size
            if size <= 0:
                general_logger.info("  Order skipped: Calculated size is zero")
                status = "SKIPPED"
                return {
                    "status": "success",
                    "message": "Calculated order size is zero. No operation performed."
                }

            # Convert Decimal to float for API calls and JSON serialization
            size_float = float(size)
            order_response = call_place_order(exchange_interface, symbol, side, size_float, ccy)
            executed_at_utc = datetime.now(timezone.utc)

            general_logger.info("  Order sent successfully")
            status = "SUCCESS"

            # Extract filled base quantity from exchange response
            filled_base_qty = extract_filled_base_qty(order_response)

            # Fallback: compute from balance difference if extraction failed
            if filled_base_qty <= 0 and pre_buy_base_balance is not None:
                try:
                    post_buy_base_raw = call_get_balance(exchange_interface, base_currency)
                    post_buy_base_balance = Decimal(str(post_buy_base_raw))
                    filled_base_qty = post_buy_base_balance - pre_buy_base_balance
                    if filled_base_qty > 0:
                        general_logger.info(f"  Fill fallback: pre={pre_buy_base_balance} post={post_buy_base_balance} filled={filled_base_qty}")
                    else:
                        filled_base_qty = Decimal('0')
                        general_logger.warning(f"  Fill fallback failed: balance diff <= 0 (pre={pre_buy_base_balance} post={post_buy_base_balance})")
                except Exception as e:
                    general_logger.warning(f"  Fill fallback balance query failed: {e}")
                    filled_base_qty = Decimal('0')

            operation_data = {
                "status": "realizada",
                "user_id": user_id,
                "api_key": api_key,
                "symbol": symbol,
                "side": side,
                "size": size_float,
                "order_response": order_response,
                "instance_id": instance_id,
                "executed_at": executed_at_utc.isoformat(),
                "filled_base_qty": str(filled_base_qty),
                "base_currency": base_currency,
            }
            get_client().send_task(
                "trade.save_operation",
                kwargs={"operation_data": operation_data},
                queue='db'
            )

            return {"status": "success", "message": "Operação executada e tarefa de salvamento enfileirada."}

    except Exception as e:
        general_logger.error(f"  Order FAILED: {e}")
        return {"status": "error", "error": str(e)}

    finally:
        elapsed = time.time() - start_time
        general_logger.info("=" * 80)
        general_logger.info(f"OPERATION END | {exchange_name} | inst:{instance_id} | {symbol} | {side.upper()} | {status} | {elapsed:.2f}s")
        general_logger.info("=" * 80)
