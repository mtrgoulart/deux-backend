from celery import shared_task
from source.context import get_db_connection
from celeryManager.tasks.base import logger
from source.dbmanager import load_query
import json
from decimal import Decimal
from source.celery_client import get_client
from source.position import add_position_entry, close_position_entries
from source.tracing import record_stage


def _update_spot_position(operation_data, operation_id):
    """
    Create or close spot position entries after an operation is saved.

    - BUY: creates a new 'open' entry linking to the buy operation_id
    - SELL: closes all open entries referenced by entry_ids, linking to the sell operation_id

    This must NOT fail the save task — position entries can be reconstructed
    from operation history if needed.
    """
    try:
        side = operation_data.get("side", "").lower()

        if side == "buy":
            filled_base_qty_str = operation_data.get("filled_base_qty")
            if not filled_base_qty_str:
                logger.warning(f"No filled_base_qty for buy operation {operation_id}, skipping position entry")
                return

            filled_base_qty = Decimal(str(filled_base_qty_str))
            if filled_base_qty <= 0:
                logger.warning(f"filled_base_qty <= 0 for buy operation {operation_id}, skipping position entry")
                return

            entry_id = add_position_entry(
                operation_id=operation_id,
                instance_id=operation_data.get("instance_id"),
                user_id=operation_data.get("user_id"),
                symbol=operation_data.get("symbol"),
                base_currency=operation_data.get("base_currency", ""),
                base_qty=filled_base_qty
            )
            logger.info(f"Position entry {entry_id} created for buy operation {operation_id}")

        elif side == "sell":
            entry_ids = operation_data.get("entry_ids")
            if not entry_ids:
                logger.info(f"No entry_ids for sell operation {operation_id}, skipping position close")
                return

            close_position_entries(entry_ids, operation_id)
            logger.info(f"Closed {len(entry_ids)} position entries for sell operation {operation_id}")

    except Exception as e:
        logger.error(f"Failed to update spot position for operation {operation_id}: {e}", exc_info=True)


@shared_task(name="trade.save_operation", bind=True)
def save_operation_task(self, operation_data):
    """
    Salva a operação e dispara a task de enriquecimento de preço.
    """
    trace_id = operation_data.get("trace_id")
    task_id = self.request.id
    record_stage(trace_id, "trade_save", status="started", celery_task_id=task_id)

    try:
        query = load_query('insert_operation.sql')
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (
                operation_data.get("user_id"),
                operation_data.get("api_key"),
                operation_data.get("symbol"),
                operation_data.get("side"),
                operation_data.get("size"),
                json.dumps(operation_data.get("order_response")),
                operation_data.get("instance_id"),
                operation_data.get("status"),
                operation_data.get("executed_at")
            ))
            operation_id = db_client.cursor.fetchone()[0]
            db_client.conn.commit()

            logger.info(f"Operação salva com sucesso (ID: {operation_id} User_id: {operation_data.get('user_id')}): {operation_data.get('symbol')}")

            _update_spot_position(operation_data, operation_id)

            record_stage(trace_id, "trade_save", status="completed",
                         metadata={"operation_id": operation_id})

            op_status = operation_data.get("status", "")
            if op_status.startswith("virtual"):
                logger.info(f"Skipping price enrichment for virtual operation {operation_id} (status: {op_status})")
                record_stage(trace_id, "price_enrichment", status="skipped",
                             metadata={"reason": f"virtual operation ({op_status})"},
                             is_terminal=True)
            else:
                try:
                    get_client().send_task(
                        "price.fetch_execution_price",
                        kwargs={
                            "operation_id": operation_id,
                            "symbol": operation_data.get("symbol"),
                            "executed_at": operation_data.get("executed_at"),
                            "trace_id": trace_id
                        },
                        queue='pricing'
                    )
                    logger.info(f"Task price.fetch_execution_price disparada para operation_id: {operation_id}")
                except Exception as e:
                    logger.error(f"Falha ao disparar task 'price.fetch_execution_price' para op_id {operation_id}: {e}")

            return operation_id

    except Exception as e:
        logger.error(f"Erro ao salvar operação: {e}", exc_info=True)
        record_stage(trace_id, "trade_save", status="failed", error=str(e), is_terminal=True)
        raise