import re
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from source.exchange_interface import get_exchange_interface
from log.log import general_logger
from source.celery_client import get_client

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

def execute_operation(user_id, api_key, exchange_id, perc_balance_operation, symbol, side,instance_id):
    """
    Executa uma operação na exchange.
    """
    try:
        base_currency, quote_currency = parse_symbol(symbol)
        exchange_interface = get_exchange_interface(exchange_id, user_id, api_key)
        ccy = quote_currency if side == 'buy' else base_currency

        balance = call_get_balance(exchange_interface, ccy)
        size = calculate_order_size(balance, perc_balance_operation)

        order_response = call_place_order(exchange_interface, symbol, side, size, ccy)

        operation_data= {
            "status": "realizada",
            "user_id": user_id,
            "api_key":api_key,
            "symbol": symbol,
            "side": side,
            "size": size,
            "order_response": order_response,
            "instance_id": instance_id
        }
        get_client().send_task(
            "trade.save_operation",
            kwargs={"operation_data": operation_data}, # Envia o dicionário inteiro
            queue='db'
        )
        return {"status": "success", "message": "Operação executada e tarefa de salvamento enfileirada."}


    except Exception as e:
        general_logger.error(f"Erro na operação para {symbol} ({side}): {e}")
        return {"status": "error", "error": str(e)}
