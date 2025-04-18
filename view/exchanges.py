from flask import jsonify, Response
from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection
import json

def save_exchange(data):
    """
    Salva informações de uma exchange no banco de dados.
    """
    query = load_query('insert_exchange.sql')
    try:
        with get_db_connection() as db_client:
            params = (
                data['name'],
                data['is_demo'],
                data.get('base_url', None),
                data.get('description', None),
            )
            db_client.insert_data(query, params)
        return jsonify({"message": "Exchange saved successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error saving exchange: {str(e)}")
        return jsonify({"error": str(e)}), 500

def remove_exchange(exchange_id):
    """
    Remove uma exchange do banco de dados.
    """
    query = load_query('delete_exchange.sql')
    try:
        with get_db_connection() as db_client:
            params = (exchange_id,)
            db_client.insert_data(query, params)
        return jsonify({"message": "Exchange removed successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error removing exchange: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_exchanges():
    """
    Busca todas as exchanges do banco de dados.
    """
    query = load_query('select_exchanges.sql')
    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query)
            exchanges = [
                {
                    "id": row[0],  # ID da exchange
                    "name": row[1],  # Nome da exchange
                    "is_demo": row[2],  # Flag demo
                    "base_url": row[3],  # URL base da API (opcional)
                    "description": row[4],  # Descrição (opcional)
                    "created_at": row[5],  # Data de criação
                }
                for row in results
            ]
            return jsonify({"exchanges": exchanges}), 200
    except Exception as e:
        general_logger.error(f"Error fetching exchanges: {str(e)}")
        return jsonify({"error": str(e)}), 500

def save_user_apikey(data, user_id):
    """
    Salva credenciais de API de um usuário para uma exchange.
    """
    query = load_query('insert_user_apikey.sql')

    
    try:
        if 'exchange_id' not in data or 'api_credentials' not in data:
            raise ValueError("Invalid request data. 'exchange_id' and 'api_credentials' are required.")
        
        api_credentials = {
            "api_key": data['api_credentials'].get('api_key', None),
            "secret_key": data['api_credentials'].get('secret_key', None),
            "passphrase": data['api_credentials'].get('passphrase', None)
        }

        with get_db_connection() as db_client:
            params = (
                user_id,
                data['exchange_id'],
                json.dumps(api_credentials),
            )
            db_client.insert_data(query, params)
        return jsonify({"message": "User API key saved successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error saving user API key: {str(e)}")
        return jsonify({"error": str(e)}), 500

def remove_user_apikey(user_id, exchange_id):
    """
    Remove as credenciais de API de um usuário para uma exchange.
    """
    query = load_query('delete_user_apikey.sql')
    try:
        with get_db_connection() as db_client:
            params = (user_id, exchange_id)
            db_client.insert_data(query, params)
        return jsonify({"message": "User API key removed successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error removing user API key: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_user_apikeys(user_id):
    """
    Busca todas as credenciais de API de um usuário.
    """
    if isinstance(user_id, Response):
        # Garante que nunca caia aqui com um objeto de erro Response
        return user_id

    query = load_query('select_user_apikeys.sql')
    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query, (user_id,))
            apikeys = []

            for row in results:
                api_credentials = row[3] if isinstance(row[3], dict) else {}

                apikey = {
                    "api_key_id": row[0],
                    "exchange_id": row[1],
                    "exchange_name": row[2],
                    "api_credentials": api_credentials,
                    "created_at": row[4],
                    "name":row[5]
                }
                apikeys.append(apikey)

            return jsonify({"user_apikeys": apikeys}), 200
    except Exception as e:
        general_logger.error(f"Erro ao buscar API Keys: {e}")
        return jsonify({"error": "Erro ao buscar API Keys"}), 500
    

def search_symbols(api_key_id: str, query: str = '', limit: int = 20):
    """
    Busca símbolos vinculados à exchange de uma API Key com filtro textual.
    """
    sql = load_query("select_symbols_by_api_key.sql")

    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(sql, (api_key_id, f"{query}%", limit))
            symbols = [row[0] for row in results]
            return jsonify({"symbols": symbols}), 200
    except Exception as e:
        general_logger.error(f"Erro ao buscar símbolos para api_key_id={api_key_id}, query='{query}': {e}")
        return jsonify({"error": "Erro ao buscar símbolos"}), 500
    
def get_symbols_by_api(api_key_id: str):
    """
    Retorna todos os símbolos vinculados à API Key informada.
    """
    query = load_query("select_symbols_by_api_key.sql")

    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query, (api_key_id, '%', 10000))  # % para todos
            symbols = [row[0] for row in results]
            return jsonify({"symbols": symbols}), 200
    except Exception as e:
        general_logger.error(f"Erro ao buscar símbolos por API Key ID={api_key_id}: {e}")
        return jsonify({"error": "Erro ao buscar símbolos"}), 500
