from celery import shared_task
from source.context import get_db_connection
from celeryManager.tasks.base import logger
from source.dbmanager import load_query  # ou onde estiver seu load_query

@shared_task(name="save_operation_task")
def save_operation_task(user_id, api_key, symbol, side, size, price, instance_id, status):
    try:
        query = load_query('insert_operation.sql')
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (
                user_id,
                api_key,
                symbol,
                side,
                size,
                price,
                instance_id,
                status
            ))
            db_client.conn.commit()
            logger.info(f"Operação salva com sucesso: {symbol} - {status}")
    except Exception as e:
        logger.error(f"Erro ao salvar operação no banco: {e}")
