"""
Internal paper-trading engine (the platform's "fake exchange").

Demo api keys point at the platform-owned "Paper" exchange, so the factory
(`get_exchange_interface`) hands back a `PaperTradingInterface` exactly like any
real exchange. Orders fill instantly at the live market price from the price
oracle (TimescaleDB `market_trades`); balances live in `paper_balances` and are
mutated atomically. No real exchange API and no real funds are ever touched.

The order-response shape mirrors BingX so `extract_filled_base_qty` and the rest
of the operation -> save -> position -> price-enrichment pipeline work unchanged.
"""

import time
import uuid
from decimal import Decimal

from log.log import general_logger
from source.context import get_db_connection, get_timescale_db_connection
from source.dbmanager import load_query
from source.exchange_interface import ExchangeInterface

# Window matching the price enricher: never fill at a price older than this.
PRICE_FRESHNESS = "5 minutes"


class PaperPriceUnavailable(Exception):
    """No fresh oracle price for the symbol — cannot simulate a fill."""


def _normalize(symbol: str) -> str:
    """Match the price-oracle symbol format ('BTC-USDT' -> 'BTCUSDT')."""
    return symbol.replace("-", "").replace("/", "").upper()


def _other_ccy(normalized_symbol: str, known_ccy: str) -> str:
    """Given a normalized symbol and one leg's currency, return the other leg."""
    known = known_ccy.upper()
    if normalized_symbol.endswith(known):
        return normalized_symbol[: -len(known)]
    if normalized_symbol.startswith(known):
        return normalized_symbol[len(known):]
    return normalized_symbol.replace(known, "", 1)


class PaperTradingInterface(ExchangeInterface):
    """Simulated exchange satisfying the full ExchangeInterface contract."""

    # Demo keys carry no real credentials — skip the DB credential lookup.
    def load_credentials(self):
        return {}

    def create_client(self):
        return None

    # --- price ---------------------------------------------------------------
    def _latest_price(self, normalized_symbol: str) -> Decimal:
        query = load_query("select_latest_market_price.sql")
        with get_timescale_db_connection() as cur:
            cur.execute(query, (normalized_symbol, PRICE_FRESHNESS))
            row = cur.fetchone()
        if not row or row[0] is None:
            raise PaperPriceUnavailable(
                f"No oracle price for '{normalized_symbol}' within {PRICE_FRESHNESS}. "
                f"Symbol must be tracked by the price oracle for paper trading."
            )
        return Decimal(str(row[0]))

    def get_current_price(self, symbol):
        return float(self._latest_price(_normalize(symbol)))

    def get_fill_price(self, order_id):
        # Fills are instant at market; the operation pipeline reads the fill
        # quantity from the order response, not via this method.
        return None

    def get_order_execution_price(self, symbol, order_id):
        return float(self._latest_price(_normalize(symbol)))

    # --- balances ------------------------------------------------------------
    def get_balance(self, ccy=None):
        if ccy:
            query = load_query("select_paper_balance.sql")
            with get_db_connection() as db:
                db.cursor.execute(query, (self.api_key, ccy.upper()))
                row = db.cursor.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0

        # No ccy: Binance-style list, used by the account.get_balance task.
        query = load_query("select_paper_balances_all.sql")
        with get_db_connection() as db:
            db.cursor.execute(query, (self.api_key,))
            rows = db.cursor.fetchall() or []
        return [{"asset": r[0], "free": float(r[1])} for r in rows]

    def _apply_fill(self, base_ccy, base_delta, quote_ccy, quote_delta):
        """Atomically apply both legs of a fill in a single transaction."""
        ensure = load_query("ensure_paper_balance.sql")
        lock = load_query("lock_paper_balances.sql")
        update = load_query("update_paper_balance_delta.sql")

        with get_db_connection() as db:
            cur = db.cursor
            cur.execute(ensure, (self.api_key, base_ccy))
            cur.execute(ensure, (self.api_key, quote_ccy))
            cur.execute(lock, (self.api_key, base_ccy, quote_ccy))
            balances = {r[0]: Decimal(str(r[1])) for r in cur.fetchall()}

            # Guard the debited leg (the credited leg can never go negative).
            for ccy, delta in ((base_ccy, base_delta), (quote_ccy, quote_delta)):
                if delta < 0 and balances.get(ccy, Decimal("0")) < -delta:
                    db.conn.rollback()
                    raise ValueError(
                        f"Insufficient paper balance: {ccy} "
                        f"have {balances.get(ccy, 0)}, need {-delta}"
                    )

            cur.execute(update, (str(base_delta), self.api_key, base_ccy))
            cur.execute(update, (str(quote_delta), self.api_key, quote_ccy))
            db.conn.commit()

    # --- orders --------------------------------------------------------------
    def place_order(self, symbol, side, order_type, size, currency, price=None):
        """
        Instant market fill at the latest oracle price.

        BUY:  `size`/`currency` is the quote amount to spend -> debit quote, credit base.
        SELL: `size`/`currency` is the base quantity to sell -> debit base, credit quote.
        Returns a BingX-shaped response (or None on failure, mirroring real interfaces).
        """
        try:
            normalized = _normalize(symbol)
            fill_price = self._latest_price(normalized)
            size_dec = Decimal(str(size))
            side_l = (side or "").lower()

            if side_l == "buy":
                quote_ccy = currency.upper()
                base_ccy = _other_ccy(normalized, quote_ccy)
                base_qty = size_dec / fill_price
                quote_amt = size_dec
                self._apply_fill(base_ccy, base_qty, quote_ccy, -quote_amt)
                executed_base = base_qty
            elif side_l == "sell":
                base_ccy = currency.upper()
                quote_ccy = _other_ccy(normalized, base_ccy)
                base_qty = size_dec
                quote_amt = size_dec * fill_price
                self._apply_fill(base_ccy, -base_qty, quote_ccy, quote_amt)
                executed_base = base_qty
            else:
                general_logger.error(f"[Paper] Invalid side '{side}'")
                return None

            general_logger.info(
                f"[Paper] FILLED {side_l.upper()} {normalized} | price={fill_price} "
                f"| base_qty={executed_base} | quote={quote_amt} | api_key={self.api_key}"
            )

            return {
                "code": 0,
                "paper": True,
                "data": {
                    "orderId": str(uuid.uuid4()),
                    "symbol": normalized,
                    "side": side_l.upper(),
                    "type": "MARKET",
                    "status": "FILLED",
                    "price": str(fill_price),
                    "executedQty": str(executed_base),
                    "cummulativeQuoteQty": str(quote_amt),
                    "transactTime": int(time.time() * 1000),
                },
            }

        except PaperPriceUnavailable as e:
            general_logger.error(f"[Paper] Order rejected: {e}")
            return None
        except Exception as e:
            general_logger.error(f"[Paper] Order failed: {e}")
            return None

    # --- read/no-op methods --------------------------------------------------
    def get_order_status(self, symbol, order_id):
        return {"status": "FILLED", "orderId": order_id}

    def get_last_trade(self, symbol):
        return None

    def get_open_order(self, symbol):
        return []

    def cancel_order(self, symbol, order):
        return {"status": "success", "paper": True}
