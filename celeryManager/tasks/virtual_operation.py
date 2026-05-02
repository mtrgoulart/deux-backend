"""
Virtual Operations - strategy-level signal recording, independent of execution.

When a webhook signal passes the strategy's interval + condition checks, this
task fires in parallel to `trade.execute_operation`. It records what the
strategy would have done (a "virtual" buy or sell) at the market price at
signal time, and pairs buys/sells via simple FIFO into virtual_position_entries.

Why this exists: the real `operations` + `spot_position_entries` tables only
get populated when an order actually fills on an exchange. Strategy-level
metrics (% return, cycle count) need a record of every signal that *should*
have been executed, regardless of whether the owner had funds, ran the bot,
or whether the exchange was reachable. Virtuals provide that record.

Pricing is enriched asynchronously by `virtual.enrich_price` using
TimescaleDB market_trades. If the symbol isn't tracked yet, the enrich task
auto-adds it to exchange_symbols so future signals get priced; the current
op is left with execution_price=NULL and status='enrichment_failed'.
"""

from datetime import datetime, timedelta, timezone

from celery import shared_task
from celery.exceptions import Retry

from celeryManager.tasks.base import logger
from source.celery_client import get_client
from source.context import get_db_connection, get_timescale_db_connection


# ============================================================================
# Helpers
# ============================================================================

def _normalize_symbol(symbol: str) -> str:
    return symbol.replace("-", "").replace("/", "").upper()


def _derive_base_currency(symbol: str) -> str:
    """
    Best-effort base-currency extraction from an instance symbol.

    Examples: 'BTC-USDT' -> 'BTC', 'ETHUSDT' -> 'ETH', 'BTC/USDT' -> 'BTC'.
    Falls back to the full symbol if nothing matches a known quote suffix.
    """
    s = symbol.upper().replace("/", "-")
    if "-" in s:
        return s.split("-")[0]
    for quote in ("USDT", "USDC", "USD", "BUSD", "BTC", "ETH"):
        if s.endswith(quote) and len(s) > len(quote):
            return s[: -len(quote)]
    return s


# ============================================================================
# Task: virtual.record_operation
# ============================================================================

@shared_task(name="virtual.record_operation", bind=True, acks_late=True)
def record_virtual_operation(self, signal):
    """
    Record a virtual operation + maintain FIFO virtual_position_entries.

    Args:
        signal (dict): {
            "instance_id": int,
            "user_id": int,           # instance owner
            "symbol": str,
            "side": "buy" | "sell",
            "trace_id": str | None,
        }

    The task is fire-and-forget from the caller's perspective: failures
    here MUST NOT propagate back to the real-execution path. Catch-all at
    the bottom logs and returns rather than re-raising.
    """
    instance_id = signal.get("instance_id")
    user_id = signal.get("user_id")
    symbol = signal.get("symbol")
    side = (signal.get("side") or "").lower()
    trace_id = signal.get("trace_id")

    log_prefix = f"[VirtualOp][Instance: {instance_id}][{symbol}][{side}]"

    if side not in ("buy", "sell"):
        logger.warning(f"{log_prefix} Invalid side, skipping virtual record")
        return {"status": "skipped", "reason": "invalid_side"}

    if not (instance_id and user_id and symbol):
        logger.warning(f"{log_prefix} Missing required signal fields, skipping")
        return {"status": "skipped", "reason": "missing_fields"}

    now = datetime.now(timezone.utc)

    try:
        with get_db_connection() as db:
            # 1) Insert the virtual operation row (price NULL — enriched async)
            db.cursor.execute(
                """
                INSERT INTO virtual_operations
                    (date, symbol, side, status, instance_id, user_id, signal_trace_id, created_at, updated_at)
                VALUES
                    (%s, %s, %s, 'pending', %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (now, symbol, side, instance_id, user_id, trace_id, now, now),
            )
            virtual_op_id = db.cursor.fetchone()[0]

            # 2) FIFO position pairing — simplest possible
            if side == "buy":
                db.cursor.execute(
                    """
                    INSERT INTO virtual_position_entries
                        (operation_id, instance_id, user_id, symbol,
                         base_currency, base_qty, status, created_at)
                    VALUES
                        (%s, %s, %s, %s, %s, 1, 'open', %s);
                    """,
                    (
                        virtual_op_id,
                        instance_id,
                        user_id,
                        symbol,
                        _derive_base_currency(symbol),
                        now,
                    ),
                )
            else:  # sell — close the oldest open entry for this instance+symbol
                db.cursor.execute(
                    """
                    UPDATE virtual_position_entries
                    SET status = 'closed',
                        sell_operation_id = %s,
                        closed_at = %s
                    WHERE id = (
                        SELECT id FROM virtual_position_entries
                        WHERE instance_id = %s
                          AND symbol = %s
                          AND status = 'open'
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    );
                    """,
                    (virtual_op_id, now, instance_id, symbol),
                )
                if db.cursor.rowcount == 0:
                    logger.info(
                        f"{log_prefix} sell signal with no open virtual position to close"
                    )

            db.conn.commit()

        # 3) Queue async price enrichment (non-blocking; failures here don't matter)
        try:
            get_client().send_task(
                "virtual.enrich_price",
                kwargs={
                    "virtual_operation_id": virtual_op_id,
                    "symbol": symbol,
                    "executed_at": now.isoformat(),
                    "trace_id": trace_id,
                },
                queue="virtual",
            )
        except Exception as e:
            logger.warning(f"{log_prefix} Failed to dispatch enrich_price: {e}")

        logger.info(
            f"{log_prefix} Recorded virtual operation id={virtual_op_id}"
        )
        return {"status": "success", "virtual_operation_id": virtual_op_id}

    except Exception as e:
        # Swallow — virtual recording failures must NEVER affect real execution.
        logger.error(
            f"{log_prefix} Error recording virtual operation: {e}",
            exc_info=True,
        )
        return {"status": "error", "error": str(e)}


# ============================================================================
# Task: virtual.enrich_price
# ============================================================================

def _get_price_from_timescale(symbol: str, executed_at_str: str):
    """Look up the most-recent market_trades price for `symbol` at-or-before
    the given timestamp, within a 5-minute safety window."""
    normalized = _normalize_symbol(symbol)
    query = """
        SELECT price
        FROM market_trades
        WHERE symbol = %s
          AND timestamp <= %s::timestamptz
          AND timestamp >= (%s::timestamptz - '5 minutes'::interval)
        ORDER BY timestamp DESC
        LIMIT 1;
    """
    try:
        with get_timescale_db_connection() as ts_cursor:
            ts_cursor.execute(query, (normalized, executed_at_str, executed_at_str))
            row = ts_cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"VIRTUAL_ENRICHER: TimescaleDB lookup failed for {symbol}: {e}")
        return None


def _ensure_symbol_tracked(symbol: str):
    """Auto-add the symbol to exchange_symbols with is_tracked=TRUE if it
    doesn't already exist. The price oracle picks it up on its next refresh,
    so future signals for this symbol get priced via TimescaleDB."""
    normalized = _normalize_symbol(symbol)
    try:
        with get_db_connection() as db:
            db.cursor.execute(
                """
                INSERT INTO exchange_symbols (symbol, is_tracked)
                VALUES (%s, TRUE)
                ON CONFLICT (symbol) DO UPDATE SET is_tracked = TRUE
                WHERE exchange_symbols.is_tracked = FALSE;
                """,
                (normalized,),
            )
            db.conn.commit()
            logger.info(f"VIRTUAL_ENRICHER: Ensured tracking for symbol {normalized}")
    except Exception as e:
        logger.warning(
            f"VIRTUAL_ENRICHER: Could not auto-track {normalized}: {e}"
        )


def _mark_enrichment_failed(virtual_operation_id: int, error: str):
    try:
        with get_db_connection() as db:
            db.cursor.execute(
                """
                UPDATE virtual_operations
                SET status = 'enrichment_failed',
                    price_enrichment_error = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (error, virtual_operation_id),
            )
            db.conn.commit()
    except Exception as e:
        logger.error(
            f"VIRTUAL_ENRICHER: Failed to mark op {virtual_operation_id} as failed: {e}"
        )


@shared_task(name="virtual.enrich_price", bind=True, max_retries=1)
def enrich_virtual_price(self, virtual_operation_id, symbol, executed_at, trace_id=None):
    """
    Populate virtual_operations.execution_price from TimescaleDB market_trades.

    Retry policy mirrors price.fetch_execution_price: try once, retry once
    after 10s if the oracle hasn't ingested the trade yet, then give up.
    On total miss, auto-add the symbol to exchange_symbols so future signals
    get priced going forward.
    """
    log_prefix = f"[VirtualEnrich][op_id={virtual_operation_id}][{symbol}]"

    try:
        price = _get_price_from_timescale(symbol, executed_at)

        if price is None:
            current_retry = self.request.retries
            if current_retry < self.max_retries:
                eta = datetime.utcnow() + timedelta(seconds=10)
                logger.warning(
                    f"{log_prefix} Price not in TimescaleDB yet, retrying in 10s "
                    f"(attempt {current_retry + 1}/{self.max_retries + 1})"
                )
                raise self.retry(eta=eta, exc=Exception("price_not_yet_ingested"))

            # Final miss — auto-track for future, mark this one failed
            _ensure_symbol_tracked(symbol)
            error_msg = (
                f"Price not found in TimescaleDB after {self.max_retries + 1} "
                f"attempts. Symbol auto-added to exchange_symbols; future "
                f"signals on {symbol} should be priced once the oracle picks it up."
            )
            _mark_enrichment_failed(virtual_operation_id, error_msg)
            logger.warning(f"{log_prefix} {error_msg}")
            return {"status": "error", "error": "price_not_found"}

        # Price found — write it
        with get_db_connection() as db:
            db.cursor.execute(
                """
                UPDATE virtual_operations
                SET execution_price = %s,
                    status = 'priced',
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (price, virtual_operation_id),
            )
            db.conn.commit()

        logger.info(f"{log_prefix} ✅ Priced at {price}")
        return {"status": "success", "price": float(price)}

    except Retry:
        # Let Celery handle scheduled retries
        raise
    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error: {e}", exc_info=True)
        _mark_enrichment_failed(virtual_operation_id, f"unexpected: {e}")
        return {"status": "error", "error": str(e)}
