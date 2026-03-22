"""
Commission calculation task — triggered after sell price enrichment.

Fetches closed position entries for a sell operation, calculates PnL per entry,
and records commission in the ledger for profitable entries.
"""
from celery import shared_task
from decimal import Decimal
from celeryManager.tasks.base import logger
from source.context import get_db_connection
from source.dbmanager import load_query
from source.tracing import record_stage


def _get_platform_config_value(key):
    """Fetch a value from platform_config table."""
    with get_db_connection() as db_client:
        db_client.cursor.execute(
            "SELECT config_value FROM platform_config WHERE config_key = %s",
            (key,),
        )
        row = db_client.cursor.fetchone()
        return row[0] if row else None


def _get_closed_entries_for_sell(sell_operation_id):
    """Fetch closed position entries with enriched buy/sell prices."""
    query = load_query('select_position_entries_for_commission.sql')
    with get_db_connection() as db_client:
        db_client.cursor.execute(query, (sell_operation_id,))
        rows = db_client.cursor.fetchall()
    return rows


def _insert_commission_ledger(user_id, entry_id, sell_operation_id,
                              profit, commission_rate, commission_amount, commission_token):
    """Insert a pending commission ledger entry. Returns ledger_id."""
    query = """
        INSERT INTO commission_ledger
            (user_id, position_entry_id, sell_operation_id,
             profit, commission_rate, commission_amount, commission_token)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    with get_db_connection() as db_client:
        db_client.cursor.execute(query, (
            user_id, entry_id, sell_operation_id,
            float(profit), float(commission_rate),
            float(commission_amount), commission_token,
        ))
        ledger_id = db_client.cursor.fetchone()[0]
        db_client.conn.commit()
    return ledger_id


@shared_task(name="commission.process", bind=True)
def process_commission_task(self, sell_operation_id, trace_id=None):
    """
    Calculate and record commissions for a completed sell operation.

    Triggered by price_enricher after successfully enriching a sell operation's price.
    Commission = (sell_price - buy_price) * quantity * commission_rate
    Only charged on profitable entries.
    """
    task_id = self.request.id
    record_stage(trace_id, "commission_process", status="started",
                 celery_task_id=task_id,
                 metadata={"sell_operation_id": sell_operation_id})

    try:
        # Fetch commission rate from platform config
        rate_str = _get_platform_config_value("commission_rate")
        if not rate_str:
            logger.warning(
                f"COMMISSION: commission_rate not configured, skipping op {sell_operation_id}"
            )
            record_stage(trace_id, "commission_process", status="skipped",
                         metadata={"reason": "commission_rate_not_configured"})
            return {"status": "skipped", "reason": "commission_rate_not_configured"}

        commission_rate = Decimal(rate_str)
        commission_token = _get_platform_config_value("commission_token") or "USDT"

        # Fetch closed entries for this sell
        entries = _get_closed_entries_for_sell(sell_operation_id)

        if not entries:
            logger.info(f"COMMISSION: No position entries for sell op {sell_operation_id}")
            record_stage(trace_id, "commission_process", status="completed",
                         metadata={"commissions_created": 0, "reason": "no_entries"})
            return {"status": "success", "commissions_created": 0}

        commissions_created = 0
        total_commission = Decimal('0')
        skipped_null = 0

        for row in entries:
            entry_id, user_id, buy_price, sell_price, base_qty = row

            if buy_price is None or sell_price is None:
                skipped_null += 1
                logger.warning(
                    f"COMMISSION: Skipping entry {entry_id} — price not enriched "
                    f"(buy={buy_price}, sell={sell_price})"
                )
                continue

            buy_price = Decimal(str(buy_price))
            sell_price = Decimal(str(sell_price))
            base_qty = Decimal(str(base_qty))

            profit = (sell_price - buy_price) * base_qty

            if profit <= 0:
                logger.info(
                    f"COMMISSION: Entry {entry_id} not profitable "
                    f"(PnL={profit:.8f}), no commission"
                )
                continue

            commission_amount = profit * commission_rate

            ledger_id = _insert_commission_ledger(
                user_id=user_id,
                entry_id=entry_id,
                sell_operation_id=sell_operation_id,
                profit=profit,
                commission_rate=commission_rate,
                commission_amount=commission_amount,
                commission_token=commission_token,
            )

            commissions_created += 1
            total_commission += commission_amount

            logger.info(
                f"COMMISSION: Entry {entry_id} | user:{user_id} | "
                f"profit={profit:.8f} | commission={commission_amount:.8f} {commission_token} | "
                f"ledger_id={ledger_id}"
            )

        record_stage(trace_id, "commission_process", status="completed",
                     metadata={
                         "commissions_created": commissions_created,
                         "total_commission": float(total_commission),
                         "skipped_null_prices": skipped_null,
                     })

        logger.info(
            f"COMMISSION: Sell op {sell_operation_id} processed — "
            f"{commissions_created} commissions, total={total_commission:.8f} {commission_token}"
        )

        return {
            "status": "success",
            "commissions_created": commissions_created,
            "total_commission": float(total_commission),
        }

    except Exception as e:
        logger.error(
            f"COMMISSION: Error processing sell op {sell_operation_id}: {e}",
            exc_info=True
        )
        record_stage(trace_id, "commission_process", status="failed",
                     error=str(e))
        raise
