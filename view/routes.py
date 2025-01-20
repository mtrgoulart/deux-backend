from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash, send_file, current_app
from .auth import AuthService
from source.dbmanager import load_query
from source.context import get_db_connection
from .bot import save_strategy,delete_strategy
import os
import json
from .indicators import get_indicators, save_indicators,remove_indicators
from .exchanges import save_exchange, remove_exchange, get_exchanges, save_user_apikey, remove_user_apikey, get_user_apikeys
from functools import wraps
from .instances import save_instance,get_instances,remove_instance,start_instance_operation, stop_instance_operation
from .data import get_instance_operations

#BLUEPRINT================================================
main_bp = Blueprint('main', __name__)

#AUTHSERVICE==============================================
auth_service = AuthService()

def get_user_id_from_token():
    token = session.get('user_token')
    if not token:
        return None
    user_id = auth_service.validate_token(token)
    if not user_id:
        session.pop('user_token', None)
    return user_id

#CONFIG_FILE_PATH=========================================
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "routes_config.json")

def load_html_templates():
    """
    Carrega as configurações de mapeamento de templates HTML.
    """
    try:
        with open(CONFIG_FILE_PATH, "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading routes configuration: {e}")
        return {}

#LOAD HTML===============================================
HTML_TEMPLATES = load_html_templates()  
def get_html_template(page_name):
    """
    Retorna o arquivo HTML associado a uma rota específica.
    """
    return HTML_TEMPLATES.get(page_name, "templates/default.html")  # Retorna 'default.html' se a chave não existir

@main_bp.route('/get_html_template/<page_name>', methods=['GET'])
def get_html_template_route(page_name):
    """
    Retorna o conteúdo do arquivo HTML associado à página solicitada.
    """
    # Obtém o nome do arquivo do template
    template_file = get_html_template(page_name)
    # Constrói o caminho absoluto a partir do root do projeto
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_path = os.path.join(root_dir, "templates", template_file)

    # Log para verificar o caminho gerado
    #print(f"Buscando template: {template_path}")

    try:
        return send_file(template_path, mimetype='text/html')
    except FileNotFoundError:
        print(f"Template não encontrado: {template_path}")
        return "Template not found.", 404
    
#USER====================================================

#REGISTER
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required!", "error")
            return render_template(get_html_template("register"))

        if auth_service.register_user(username, password):
            return redirect(url_for('main.login'))
        return render_template(get_html_template("register"))

    return render_template(get_html_template("register"))

#LOGOUT
@main_bp.route('/logout')
def logout():
    session.pop('user_token', None)
    return redirect(url_for('main.login'))

#LOGIN
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        result = auth_service.login_user(username, password)
        if "token" in result:
            session['user_token'] = result["token"]
            return redirect(url_for('main.home'))
        return render_template(get_html_template("login"), error="Login failed. Please check your credentials.")
    return render_template(get_html_template("login"))


@main_bp.route('/get_user', methods=['GET'])
def get_user():
    """
    Retorna informações sobre o usuário logado.
    """
    # Recupera o token JWT da sessão
    token = session.get('user_token')
    if not token:
        return jsonify({"error": "User not logged in"}), 401

    # Valida o token e obtém o ID do usuário
    auth_service = AuthService()  # Instancia o serviço de autenticação
    user_id = auth_service.validate_token(token)
    if not user_id:
        return jsonify({"error": "Invalid or expired token"}), 401

    # Consulta o banco de dados para obter o nome de usuário
    try:
        with auth_service.get_db_connection() as db_client:
            query = 'SELECT username FROM neouser WHERE id = %s'
            db_client.cursor.execute(query, (user_id,))
            user = db_client.cursor.fetchone()

        if user:
            return jsonify({"name": user[0]})  # Retorna o nome do usuário
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        print(f"Error fetching user: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
#HOME==============================================

@main_bp.route('/')
def home():
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))
    return render_template(get_html_template("home"), user_id=user_id)

#STRATEGY==========================================

#SAVE
@main_bp.route('/save_strategy', methods=['POST'])
def save_strategy_route():
    """
    Rota para salvar uma estratégia no banco de dados (Buy e Sell).
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    data = request.json
    return save_strategy(data, user_id)

#DELETE
@main_bp.route('/delete_strategy', methods=['POST'])
def delete_strategy_route():
    """
    Rota para deletar uma estratégia (Buy e Sell) associada ao strategy_id.
    """
    data = request.json
    strategy_id = data.get('strategy_id')
    user_id = get_user_id_from_token()

    if not strategy_id or not user_id:
        return jsonify({"error": "Invalid request"}), 400

    # Delegando a exclusão para a função do bot.py
    return delete_strategy(strategy_id, user_id)

#GET
@main_bp.route('/get_strategies', methods=['GET'])
def get_strategies():
    """
    Rota para buscar todas as estratégias salvas do usuário logado.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    query = load_query('select_strategy_by_user.sql')

    with get_db_connection() as db_client:
        strategies = db_client.fetch_data(query, (user_id,))
        if not strategies:
            return jsonify({"operations": []}), 200

        # Dicionário temporário para agrupar estratégias por strategy_id
        grouped_strategies = {}
        for row in strategies:
            strategy_id = row[0]  # ID da estratégia
            symbol = row[1]
            side = row[2]         # 'buy' ou 'sell'

            if strategy_id not in grouped_strategies:
                grouped_strategies[strategy_id] = {
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "buy": None,
                    "sell": None,
                    "status": row[7],
                }

            # Adiciona os detalhes de buy ou sell no local correto
            grouped_strategies[strategy_id][side] = {
                "percent": row[3],
                "condition_limit": row[4],
                "interval": row[5],
                "simultaneous_operations": row[6] if side == 'buy' else None,
            }

        # Transforma o dicionário em uma lista para o JSON final
        response = list(grouped_strategies.values())

        return jsonify({"operations": response}), 200

@main_bp.route('/get_instance_strategies/<int:instance_id>', methods=['GET'])
def get_instance_strategies(instance_id):
    """
    Busca as estratégias associadas a uma instância específica.
    """
    query = load_query('select_strategies_by_instance.sql')  # Certifique-se de que esta query está correta.
    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query, (instance_id,))
            
            # Estrutura para agrupar estratégias por strategy_uuid
            grouped_strategies = {}
            for row in results:
                strategy_uuid = row[1]  # UUID da estratégia
                if strategy_uuid not in grouped_strategies:
                    grouped_strategies[strategy_uuid] = {
                        "strategy_id": row[0],  # ID da estratégia (PK na tabela)
                        "strategy_uuid": strategy_uuid,  # UUID da estratégia
                        "symbol": row[2],  # Símbolo
                        "buy": None,  # Inicialmente vazio
                        "sell": None,  # Inicialmente vazio
                        "status": row[8],  # Status
                    }

                # Preenche os detalhes de 'buy' ou 'sell' com base no lado
                if row[3] == "buy":
                    grouped_strategies[strategy_uuid]["buy"] = {
                        "percent": row[4],
                        "condition_limit": row[5],
                        "interval": row[6],
                        "simultaneous_operations": row[7],  # Apenas para 'buy'
                    }
                elif row[3] == "sell":
                    grouped_strategies[strategy_uuid]["sell"] = {
                        "percent": row[4],
                        "condition_limit": row[5],
                        "interval": row[6],
                    }

            # Retorna as estratégias agrupadas em um formato JSON
            return jsonify({"strategies": list(grouped_strategies.values())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#GENERATE ID
@main_bp.route('/generate_strategy_id', methods=['GET'])
def generate_strategy_id():
    import uuid
    strategy_id = str(uuid.uuid4())  # Gera um UUID único
    return jsonify({"strategy_id": strategy_id}), 200

#SYMBOL==========================================

SYMBOLS_FILE_PATH = os.path.join(os.path.dirname(__file__), "symbols.json")

#GET
@main_bp.route('/get_symbols', methods=['GET'])
def get_symbols():
    """
    Retorna a lista de symbols definidos no arquivo JSON.
    """
    try:
        with open(SYMBOLS_FILE_PATH, "r") as file:
            data = json.load(file)
            return jsonify(data.get("symbols", [])), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load symbols: {str(e)}"}), 500
    

#INDICATOR==========================================

#SAVE
@main_bp.route('/save_indicators', methods=['POST'])
def save_indicators_route():
    """
    Rota para salvar indicadores.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    data = request.json
    return save_indicators(data, user_id)

#GET
@main_bp.route('/get_indicators', methods=['GET'])
def get_indicators_route():
    """
    Rota para buscar indicadores associados a uma estratégia.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    strategy_id = request.args.get('strategy_id')
    side = request.args.get('side')

    if not strategy_id or not side:
        return jsonify({"error": "Invalid request"}), 400

    return get_indicators(strategy_id, side, user_id)

#REMOVE
@main_bp.route('/remove_indicators', methods=['POST'])
def remove_indicators_route():
    """
    Rota para remover indicadores do banco de dados.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    data = request.json
    return remove_indicators(data, user_id)

#EXCHANGE ROUTES=========================================

@main_bp.route('/save_exchange', methods=['POST'])
def save_exchange_route():
    """
    Rota para salvar uma exchange no banco de dados.
    """
    data = request.json
    if not data or 'name' not in data or 'is_demo' not in data:
        return jsonify({"error": "Invalid data"}), 400
    return save_exchange(data)

@main_bp.route('/remove_exchange', methods=['POST'])
def remove_exchange_route():
    """
    Rota para remover uma exchange do banco de dados.
    """
    data = request.json
    exchange_id = data.get('exchange_id')
    if not exchange_id:
        return jsonify({"error": "Exchange ID is required"}), 400
    return remove_exchange(exchange_id)

@main_bp.route('/get_exchanges', methods=['GET'])
def get_exchanges_route():
    """
    Rota para buscar todas as exchanges registradas.
    """
    return get_exchanges()

# USER API KEYS ROUTES ===================================

@main_bp.route('/save_user_apikey', methods=['POST'])
def save_user_apikey_route():
    """
    Rota para salvar as credenciais de API de um usuário para uma exchange.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    data = request.json
    if not data or 'exchange_id' not in data or 'api_credentials' not in data:
        return jsonify({"error": "Invalid data"}), 400
    return save_user_apikey(data, user_id)

@main_bp.route('/remove_user_apikey', methods=['POST'])
def remove_user_apikey_route():
    """
    Rota para remover as credenciais de API de um usuário para uma exchange.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    data = request.json
    exchange_id = data.get('exchange_id')
    if not exchange_id:
        return jsonify({"error": "Exchange ID is required"}), 400
    return remove_user_apikey(user_id, exchange_id)

@main_bp.route('/get_user_apikeys', methods=['GET'])
def get_user_apikeys_route():
    """
    Rota para buscar todas as credenciais de API de um usuário.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))
    return get_user_apikeys(user_id)

#Register API Key ===================================
@main_bp.route('/register-api-key', methods=['GET'])
def register_api_key():
    """
    Direciona para o HTML de registro de nova API Key.
    """
    return render_template(get_html_template("register_api_key"))


# INSTANCE ROUTES =========================================

@main_bp.route('/save_instance', methods=['POST'])
def save_instance_route():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    data = request.json
    return save_instance(data, user_id)

@main_bp.route('/remove_instance', methods=['POST'])
def remove_instance_route():
    """
    Rota para remover uma instância do banco de dados.
    """
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({"error": "Instance ID is required"}), 400

    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    return remove_instance(instance_id, user_id)


@main_bp.route('/start_instance', methods=['POST'])
def start_instance_route():
    data = request.json
    instance_id = data.get('instance_id')
    user_id = get_user_id_from_token()

    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    if not instance_id:
        return jsonify({"error": "Instance ID is required"}), 400

    return start_instance_operation(instance_id, user_id)

@main_bp.route('/stop_instance', methods=['POST'])
def stop_instance_route():
    data = request.json
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({"error": "Instance ID is required"}), 400

    return stop_instance_operation(instance_id)

@main_bp.route('/get_instances', methods=['GET'])
def get_instances_route():
    """
    Rota para buscar instâncias salvas com base em uma API Key específica.
    """
    # Obtém o user_id a partir do token
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    # Obtém o api_key_id da query string
    api_key_id = request.args.get('api_key_id')
    if not api_key_id:
        return jsonify({"error": "API Key ID is required"}), 400

    try:
        # Chama a função get_instances com o api_key_id
        return get_instances(api_key_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@main_bp.route('/get_instance_operations', methods=['POST'])
def get_instance_operations_route():
    """
    Rota para buscar as operações de uma instância específica e gerar um CSV.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    # Obtém os dados do corpo da requisição (POST)
    data = request.json
    if not data or "instance_id" not in data:
        return jsonify({"error": "Instance ID is required"}), 400

    return get_instance_operations({"instance_id": data["instance_id"], "user_id": user_id})


