from celery import shared_task
from source.context import get_db_connection
from celeryManager.tasks.base import logger
from source.dbmanager import load_query  # ou onde estiver seu load_query
import json
from source.celery_client import get_client

@shared_task(name="trade.save_operation", bind=True)
def save_operation_task(self, operation_data):
    """
    Salva a operação e dispara a task de enriquecimento de preço.
    """
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

            try:
                get_client().send_task(
                    "price.fetch_execution_price",
                    kwargs={
                        "operation_id": operation_id,
                        "symbol": operation_data.get("symbol"),
                        "executed_at": operation_data.get("executed_at")
                    },
                    queue='pricing'
                )
                logger.info(f"Task price.fetch_execution_price disparada para operation_id: {operation_id}")
            except Exception as e:
                logger.error(f"Falha ao disparar task 'price.fetch_execution_price' para op_id {operation_id}: {e}")

            return operation_id

    except Exception as e:
        logger.error(f"Erro ao salvar operação: {e}", exc_info=True)
        raise