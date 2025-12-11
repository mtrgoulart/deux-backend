import re
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from source.exchange_interface import get_exchange_interface
from log.log import general_logger
from source.celery_client import get_client
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

    Supports two sizing modes:
    1. percentage: Calculate size as percentage of balance (legacy mode)
    2. flat_value: Use exact flat value amount

    Args:
        user_id: User ID
        api_key: API key ID
        exchange_id: Exchange ID
        perc_balance_operation: Percentage of balance (used in percentage mode)
        symbol: Trading symbol
        side: 'buy' or 'sell'
        instance_id: Instance ID
        max_amount_size: Maximum size limit (optional, for copy trading)
        size_mode: "percentage" or "flat_value"
        flat_value: Exact amount to trade (used in flat_value mode)

    Returns:
        dict: Operation result with status and details
    """
    try:
        base_currency, quote_currency = parse_symbol(symbol)
        exchange_interface = get_exchange_interface(exchange_id, user_id, api_key)
        ccy = quote_currency if side == 'buy' else base_currency

        # Get current balance
        balance_raw = call_get_balance(exchange_interface, ccy)
        general_logger.info(f"Raw balance for {ccy}: {balance_raw} (type: {type(balance_raw)})")
        balance = Decimal(str(balance_raw))

        # Calculate order size based on mode
        if size_mode == "flat_value":
            # FLAT VALUE MODE: Use exact amount specified
            if flat_value is None or flat_value <= 0:
                return {
                    "status": "error",
                    "message": "flat_value must be a positive number when size_mode is 'flat_value'"
                }

            size = Decimal(str(flat_value))

            # Check if balance is sufficient for flat value
            if balance < size:
                general_logger.warning(
                    f"Insufficient balance for user_id {user_id}. "
                    f"Balance: {balance}, flat_value requested: {size}. Operation not executed."
                )
                return {
                    "status": "insufficient_balance",
                    "message": f"Insufficient balance. Required: {size}, Available: {balance}"
                }

            general_logger.info(f"Using FLAT VALUE mode: size = {size} {ccy}")

        else:
            # PERCENTAGE MODE: Calculate based on balance percentage (legacy mode)
            base_para_calculo = balance

            # Apply max_amount_size limit if specified (for copy trading)
            if max_amount_size is not None:
                if balance < max_amount_size:
                    general_logger.warning(
                        f"Insufficient balance for user_id {user_id}. "
                        f"Balance: {balance}, max_amount_size: {max_amount_size}. Operation not executed."
                    )
                    return {
                        "status": "insufficient_balance",
                        "message": "Insufficient balance to cover max_amount_size."
                    }

                base_para_calculo = max_amount_size

            # Calculate size as percentage of balance
            perc_decimal = Decimal(str(perc_balance_operation))
            size = base_para_calculo * perc_decimal

            general_logger.info(f"Using PERCENTAGE mode: {perc_balance_operation * 100}% of {base_para_calculo} = {size} {ccy}")

        # Validate calculated size
        if size <= 0:
            return {
                "status": "success",
                "message": "Calculated order size is zero. No operation performed."
            }

        general_logger.info(f'Sending order for user_id: {user_id}, instance_id: {instance_id}, side: {side}, size: {size}, ccy: {ccy}, mode: {size_mode}')

        # Convert Decimal to float for API calls and JSON serialization
        size_float = float(size)
        order_response = call_place_order(exchange_interface, symbol, side, size_float, ccy)
        executed_at_utc = datetime.now(timezone.utc)

        operation_data= {
            "status": "realizada",
            "user_id": user_id,
            "api_key":api_key,
            "symbol": symbol,
            "side": side,
            "size": size_float,
            "order_response": order_response,
            "instance_id": instance_id,
            "executed_at": executed_at_utc.isoformat()
        }
        get_client().send_task(
            "trade.save_operation",
            kwargs={"operation_data": operation_data},
            queue='db'
        )
        
        return {"status": "success", "message": "Operação executada e tarefa de salvamento enfileirada."}


    except Exception as e:
        general_logger.error(f"Erro na operação para {symbol} ({side}): {e}")
        return {"status": "error", "error": str(e)}
