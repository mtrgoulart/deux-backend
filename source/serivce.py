from source.dbmanager import load_query
from source.context import get_db_connection
from log.log import general_logger

def get_neouser_apikey_from_sharing(user_id, sharing_id):
    query = load_query('select_neouser_apikey_from_sharing.sql')
    params = (sharing_id, user_id)

    with get_db_connection() as db_client: 
        results = db_client.fetch_data(query, params)

        if not results:
            general_logger.info(f'No api key for sharing_id:{sharing_id}')
            return []

        # Converte lista de tuplas para lista de dicts
        return [
            {
                "user_id": row[0],
                "api_key": row[1],
                "exchange_id":row[2],
                "instance_id":row[3]
            } for row in results
        ]   