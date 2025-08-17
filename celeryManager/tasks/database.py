from celery import shared_task
from source.context import get_db_connection
from celeryManager.tasks.base import logger
from source.dbmanager import load_query  # ou onde estiver seu load_query

@shared_task(name="trade.save_operation", queue="db", bind=True)
def save_operation_task(operation_data):
    """
    Recebe os dados de uma operação e salva no banco de dados,
    armazenando o order_response completo.
    """
    try:
        # Converte o order_response (que é um dict/objeto) para uma string JSON
        # O driver do banco de dados (psycopg2) geralmente faz isso para colunas JSONB,
        # mas fazer explicitamente é mais seguro e compatível.

        query = load_query('insert_operation.sql')
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (
                operation_data.get("user_id"),
                operation_data.get("api_key"),
                operation_data.get("symbol"),
                operation_data.get("side"),
                operation_data.get("size"),
                operation_data.get("order_response"),
                operation_data.get("instance_id"),
                operation_data.get("status")
            ))
            operation_id = db_client.cursor.fetchone()[0]
            db_client.conn.commit()

            logger.info(f"Operação salva com sucesso (ID: {operation_id}): {operation_data.get('symbol')}")
            return operation_id

    except Exception as e:
        logger.error(f"Erro ao salvar operação para o symbol {operation_data.get('symbol')}: {e}", exc_info=True)
        raise