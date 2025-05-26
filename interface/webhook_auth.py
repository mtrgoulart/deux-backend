from source.dbmanager import load_query
from source.context import get_db_connection
from log.log import general_logger

def authenticate_signal(key):
    """
    Autentica a chave do webhook e retorna user_id e instance_id.
    """
    query = load_query("select_user_instance_by_key.sql")

    try:
        with get_db_connection() as db_client:
            result = db_client.fetch_data(query, (key,))
            if not result:
                general_logger.warning(f"Chave de sinal inválida: {key}")
                return None
            
            row = result[0]  # linha completa: (user_id, instance_id, symbol, indicator_id)

            return {
                'user_id': row[0],
                'instance_id': row[1],
                'symbol': row[2],
                'indicator_id': row[3]
            }
        
    except Exception as e:
        general_logger.error(f"Erro ao autenticar sinal {key}: {str(e)}")
        return None


def insert_data_to_db(data):
    """
    Insere os dados do webhook usando o padrão de queries carregadas.
    
    Args:
        data (dict): Dicionário com:
            - key (str)
            - symbol (str)
            - side (str)
            - indicator_id (int)
            - instance_id (int)
    """
    query = load_query("insert_webhook_data.sql")  # Você precisará criar este arquivo
    
    try:
        with get_db_connection() as db_client:
            # Convertendo o dict para tupla na ordem esperada pela query
            params = (
                data['key'],
                data['symbol'],
                data['side'],
                data['indicator_id'],
                data['instance_id']
            )
            db_client.insert_data(query, params)
            general_logger.info(f"Dados inseridos com sucesso. Key: {data['key']}")
    except KeyError as e:
        error_msg = f"Campo faltando no dicionário de dados: {str(e)}"
        general_logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        general_logger.error(f"Erro ao inserir dados: {str(e)}")
        raise