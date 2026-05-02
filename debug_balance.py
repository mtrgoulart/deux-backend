"""
Usage:
    python debug_balance.py <user_id> <exchange_id> <api_key_id> [ccy]

Loads the user's API credentials via the same path the workers use, then dumps
the raw exchange balance response so we can see real error codes (e.g. BingX
permission/IP/signature failures that the interface currently swallows).

Examples:
    python debug_balance.py 6 3 12 USDT       # user 6, exchange 3, api_key_id 12
    python debug_balance.py 6 3 12            # defaults ccy=USDT
"""
import json
import sys

from source.exchange_interface import get_exchange_interface


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 1

    user_id = int(sys.argv[1])
    exchange_id = int(sys.argv[2])
    api_key_id = int(sys.argv[3])
    ccy = sys.argv[4] if len(sys.argv) > 4 else "USDT"

    print(f"user_id={user_id} exchange_id={exchange_id} api_key_id={api_key_id} ccy={ccy}")
    print("-" * 80)

    iface = get_exchange_interface(
        exchange_id=exchange_id,
        user_id=user_id,
        api_key=api_key_id,
    )
    print(f"Interface: {type(iface).__name__}  exchange_name={iface.exchange_name}")
    print("-" * 80)

    raw = None
    if hasattr(iface, "bingx_client"):
        raw = iface.bingx_client.get_balance()
    elif hasattr(iface, "binance_client"):
        raw = iface.binance_client.get_balance(asset=ccy)
    elif hasattr(iface, "okx_client"):
        raw = iface.okx_client.get_balance(ccy)
    elif hasattr(iface, "aster_client"):
        raw = iface.aster_client.get_balance(ccy)
    elif hasattr(iface, "phemex_client"):
        raw = iface.phemex_client.get_balance(currency=ccy)

    print("RAW client response:")
    try:
        print(json.dumps(raw, indent=2, ensure_ascii=False, default=str))
    except Exception:
        print(repr(raw))
    print("-" * 80)

    try:
        parsed = iface.get_balance(ccy)
        print(f"Parsed balance for {ccy}: {parsed}")
    except Exception as e:
        print(f"Parsed balance for {ccy}: RAISED {type(e).__name__}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
