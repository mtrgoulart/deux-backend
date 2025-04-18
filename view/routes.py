from flask import Blueprint, redirect, url_for, session, request, jsonify, flash, current_app, Response
from .auth import AuthService
from source.dbmanager import load_query
from source.context import get_db_connection
from .bot import save_strategy, delete_strategy
import os
import json
from .indicators import get_indicators, save_indicators, remove_indicators
from .exchanges import save_exchange, remove_exchange, get_exchanges, save_user_apikey, remove_user_apikey, get_user_apikeys,search_symbols, get_symbols_by_api
from functools import wraps
from .instances import save_instance, get_instances, remove_instance, start_instance_operation, stop_instance_operation
from .data import get_instance_operations

main_bp = Blueprint('main', __name__, url_prefix='/api')
auth_service = AuthService()

def get_user_id_from_token(json_response=False):
    token = session.get('user_token')
    if not token:
        session.pop('user_token', None)
        response = jsonify({"error": "Unauthorized"})
        response.status_code = 401
        return response if json_response else None

    user_id = auth_service.validate_token(token)
    if not user_id:
        session.pop('user_token', None)
        response = jsonify({"error": "Invalid token"})
        response.status_code = 401
        return response if json_response else None

    return user_id

@main_bp.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    if auth_service.register_user(username, password):
        return jsonify({"success": True}), 200
    return jsonify({"error": "Registration failed"}), 400

@main_bp.route('/logout')
def logout():
    session.pop('user_token', None)
    return jsonify({"success": True})

@main_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    result = auth_service.login_user(username, password)
    if isinstance(result, dict) and "token" in result:
        session['user_token'] = result["token"]
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "Credenciais inválidas"}), 401

@main_bp.route('/get_user', methods=['GET'])
def get_user():
    token = session.get('user_token')
    if not token:
        return jsonify({"error": "User not logged in"}), 401

    user_id = auth_service.validate_token(token)
    if not user_id:
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        with auth_service.get_db_connection() as db_client:
            query = 'SELECT username FROM neouser WHERE id = %s'
            db_client.cursor.execute(query, (user_id,))
            user = db_client.cursor.fetchone()

        if user:
            return jsonify({"name": user[0]})
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        print(f"Error fetching user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@main_bp.route('/status')
def status():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id
    return jsonify({"message": "Backend is running", "user_id": user_id}), 200

@main_bp.route('/save_strategy', methods=['POST'])
def save_strategy_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    return save_strategy(data, user_id)


@main_bp.route('/delete_strategy', methods=['POST'])
def delete_strategy_route():
    data = request.json
    strategy_id = data.get('strategy_id')
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    if not strategy_id:
        return jsonify({"error": "Invalid request"}), 400

    return delete_strategy(strategy_id, user_id)


@main_bp.route('/get_strategies', methods=['GET'])
def get_strategies():
    user_id = get_user_id_from_token(json_response=True)
    print(f'printando user_id {user_id}')
    if isinstance(user_id, tuple):
        return user_id[0]

    query = load_query('select_strategy_by_user.sql')
    with get_db_connection() as db_client:
        strategies = db_client.fetch_data(query, (user_id,))
        if not strategies:
            return jsonify({"operations": []}), 200

        grouped_strategies = {}
        for row in strategies:
            strategy_id = row[0]
            symbol = row[1]
            side = row[2]

            if strategy_id not in grouped_strategies:
                grouped_strategies[strategy_id] = {
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "buy": None,
                    "sell": None,
                    "status": row[7],
                    "tp": row[8],
                    "sl": row[9]
                }

            grouped_strategies[strategy_id][side] = {
                "percent": row[3],
                "condition_limit": row[4],
                "interval": row[5],
                "simultaneous_operations": row[6] if side == 'buy' else None,
            }

        return jsonify({"strategies": list(grouped_strategies.values())}), 200


@main_bp.route('/get_instance_strategies/<int:instance_id>', methods=['GET'])
def get_instance_strategies(instance_id):
    query = load_query('select_strategies_by_instance.sql')
    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query, (instance_id,))
            grouped_strategies = {}
            for row in results:
                strategy_uuid = row[1]
                if strategy_uuid not in grouped_strategies:
                    grouped_strategies[strategy_uuid] = {
                        "strategy_id": row[0],
                        "strategy_uuid": strategy_uuid,
                        "symbol": row[2],
                        "buy": None,
                        "sell": None,
                        "status": row[8],
                    }

                if row[3] == "buy":
                    grouped_strategies[strategy_uuid]["buy"] = {
                        "percent": row[4],
                        "condition_limit": row[5],
                        "interval": row[6],
                        "simultaneous_operations": row[7],
                    }
                elif row[3] == "sell":
                    grouped_strategies[strategy_uuid]["sell"] = {
                        "percent": row[4],
                        "condition_limit": row[5],
                        "interval": row[6],
                    }

            return jsonify({"strategies": list(grouped_strategies.values())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route('/generate_strategy_id', methods=['GET'])
def generate_strategy_id():
    import uuid
    strategy_id = str(uuid.uuid4())
    return jsonify({"strategy_id": strategy_id}), 200

SYMBOLS_FILE_PATH = os.path.join(os.path.dirname(__file__), "symbols.json")

@main_bp.route('/get_symbols', methods=['GET'])
def get_symbols():
    try:
        with open(SYMBOLS_FILE_PATH, "r") as file:
            data = json.load(file)
            return jsonify(data.get("symbols", [])), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load symbols: {str(e)}"}), 500

@main_bp.route('/save_indicators', methods=['POST'])
def save_indicators_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    return save_indicators(data, user_id)

@main_bp.route('/get_indicators', methods=['GET'])
def get_indicators_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    strategy_id = request.args.get('strategy_id')
    side = request.args.get('side')

    if not strategy_id or not side:
        return jsonify({"error": "Invalid request"}), 400

    return get_indicators(strategy_id, side, user_id)


@main_bp.route('/remove_indicators', methods=['POST'])
def remove_indicators_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    return remove_indicators(data, user_id)


@main_bp.route('/save_exchange', methods=['POST'])
def save_exchange_route():
    data = request.json
    if not data or 'name' not in data or 'is_demo' not in data:
        return jsonify({"error": "Invalid data"}), 400
    return save_exchange(data)

@main_bp.route('/remove_exchange', methods=['POST'])
def remove_exchange_route():
    data = request.json
    exchange_id = data.get('exchange_id')
    if not exchange_id:
        return jsonify({"error": "Exchange ID is required"}), 400
    return remove_exchange(exchange_id)

@main_bp.route('/get_exchanges', methods=['GET'])
def get_exchanges_route():
    return get_exchanges()

@main_bp.route('/save_user_apikey', methods=['POST'])
def save_user_apikey_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    if not data or 'exchange_id' not in data or 'api_credentials' not in data:
        return jsonify({"error": "Invalid data"}), 400
    return save_user_apikey(data, user_id)


@main_bp.route('/remove_user_apikey', methods=['POST'])
def remove_user_apikey_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    exchange_id = data.get('exchange_id')
    if not exchange_id:
        return jsonify({"error": "Exchange ID is required"}), 400
    return remove_user_apikey(user_id, exchange_id)


@main_bp.route('/get_user_apikeys', methods=['GET'])
def route_get_user_apikeys():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id  # Retorna o erro 401 diretamente

    return get_user_apikeys(user_id)

@main_bp.route('/save_instance', methods=['POST'])
def save_instance_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    return save_instance(data, user_id)


@main_bp.route('/remove_instance', methods=['POST'])
def remove_instance_route():
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({"error": "Instance ID is required"}), 400

    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    return remove_instance(instance_id, user_id)


@main_bp.route('/start_instance', methods=['POST'])
def start_instance_route():
    data = request.json
    instance_id = data.get('instance_id')
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    if not instance_id:
        return jsonify({"error": "Instance ID is required"}), 400

    success, message = start_instance_operation(instance_id, user_id)

    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 500


@main_bp.route('/stop_instance', methods=['POST'])
def stop_instance_route():
    data = request.json
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({"error": "Instance ID is required"}), 400

    return stop_instance_operation(instance_id)

@main_bp.route('/get_instances', methods=['GET'])
def get_instances_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    api_key_id = request.args.get('api_key_id')
    if not api_key_id:
        return jsonify({"error": "API Key ID is required"}), 400

    try:
        return get_instances(api_key_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/get_instance_operations', methods=['POST'])
def get_instance_operations_route():
    user_id = get_user_id_from_token(json_response=True)
    if isinstance(user_id, Response):
        return user_id

    data = request.json
    if not data or "instance_id" not in data:
        return jsonify({"error": "Instance ID is required"}), 400

    return get_instance_operations({"instance_id": data["instance_id"], "user_id": user_id})


@main_bp.route('/search_symbols', methods=['GET'])
def search_symbols_route():
    search = request.args.get('query', '').upper()
    api_key_id = request.args.get('api_key_id')
    limit = int(request.args.get('limit', 20))

    if not api_key_id:
        return jsonify({'error': 'Parâmetro api_key_id é obrigatório'}), 400
    
    return search_symbols(api_key_id=api_key_id, query=search, limit=limit)


@main_bp.route('/get_symbols_by_api', methods=['GET'])
def get_symbols_by_api_route():
    api_key_id = request.args.get('id')
    if not api_key_id:
        return jsonify({'error': 'Parâmetro "id" é obrigatório'}), 400

    return get_symbols_by_api(api_key_id)