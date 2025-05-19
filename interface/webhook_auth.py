from source.dbmanager import load_query
from source.context import get_db_connection
from log.log import general_logger

def authenticate_signal(signal_key):
    """
    Autentica a chave do webhook e retorna user_id e instance_id.
    """
    query = load_query("select_user_instance_by_signal.sql")

    try:
        with get_db_connection() as db_client:
            result = db_client.fetch_data(query, (signal_key,))
            if not result:
                general_logger.warning(f"Chave de sinal inválida: {signal_key}")
                return None, None

            user_id, instance_id = result[0][0]
            return user_id, instance_id
    except Exception as e:
        general_logger.error(f"Erro ao autenticar sinal {signal_key}: {str(e)}")
        return None, None
