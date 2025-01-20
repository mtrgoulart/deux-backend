from flask import jsonify
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
    query = load_query('select_user_apikeys.sql')
    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query, (user_id,))
            apikeys = []

            for row in results:
                # Decodifica o JSON armazenado no campo api_credentials
                api_credentials = row[3] if isinstance(row[3], dict) else {}

                apikey = {
                    "api_key_id": row[0],  # ID da API Key
                    "exchange_id": row[1],  # ID da exchange
                    "exchange_name": row[2],  # Nome da exchange
                    "api_credentials": api_credentials,  # Diretamente os valores salvos no JSON
                    "created_at": row[4],  # Data de criação
                }
                apikeys.append(apikey)

            return jsonify({"user_apikeys": apikeys}), 200
    except Exception as e:
        general_logger.error(f"Error fetching user API keys: {str(e)}")
        return jsonify({"error": str(e)}), 500
