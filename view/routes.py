from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash, send_file, current_app
from .auth import AuthService
from source.dbmanager import load_query
from source.context import get_db_connection  # Importa o gerenciador de contexto
from .bot import start_bot_operation,stop_bot_operation, save_strategy,delete_strategy
import os
import json
from .indicators import get_indicators, save_indicators,remove_indicators

# Define o blueprint
main_bp = Blueprint('main', __name__)

# Inicializa o AuthService
auth_service = AuthService()

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

# Middleware para validar o token
def get_user_id_from_token():
    token = session.get('user_token')
    if not token:
        return None
    user_id = auth_service.validate_token(token)
    if not user_id:
        session.pop('user_token', None)
    return user_id

# Carrega o mapeamento das rotas do JSON
HTML_TEMPLATES = load_html_templates()  
def get_html_template(page_name):
    """
    Retorna o arquivo HTML associado a uma rota específica.
    """
    return HTML_TEMPLATES.get(page_name, "templates/default.html")  # Retorna 'default.html' se a chave não existir


# Rota para a página de login
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
    
# Rota para registro
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

# Rota para logout
@main_bp.route('/logout')
def logout():
    session.pop('user_token', None)
    return redirect(url_for('main.login'))

# Rota principal
@main_bp.route('/')
def home():
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))
    return render_template(get_html_template("home"), user_id=user_id)

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


# Rota para iniciar uma estratégia
@main_bp.route('/start_strategy', methods=['POST'])
def start_strategy():
    """
    Rota para iniciar ambas as subestratégias (Buy e Sell) associadas ao strategy_id.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return redirect(url_for('main.login'))

    data = request.json
    strategy_id = data.get('strategy_id')

    if not strategy_id:
        return jsonify({"error": "Strategy ID is required"}), 400

    # Encaminha para o bot.py
    return start_bot_operation({"strategy_id": strategy_id}, user_id)

# Rota para parar uma estratégia
@main_bp.route('/stop_strategy', methods=['POST'])
def stop_strategy():
    """
    Rota para parar ambas as subestratégias (Buy e Sell) associadas ao strategy_id.
    """
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    data = request.json
    strategy_id = data.get('strategy_id')

    if not strategy_id:
        return jsonify({"error": "Strategy ID is required"}), 400

    try:
        # Parar as operações de Buy e Sell
        buy_response, buy_status = stop_bot_operation({"strategy_id": strategy_id, "side": "buy"}, user_id)
        sell_response, sell_status = stop_bot_operation({"strategy_id": strategy_id, "side": "sell"}, user_id)

        # Atualiza o status para "stopped" no banco de dados apenas se ambas forem bem-sucedidas
        if buy_status == 200 and sell_status == 200:
            return jsonify({"message": "Both strategies stopped successfully"}), 200

        # Retorna erros detalhados se uma ou ambas falharem
        return jsonify({
            "error": "Failed to stop one or both strategies",
            "buy_response": buy_response,
            "sell_response": sell_response
        }), 400
    except Exception as e:
        print(f"Error stopping strategies for strategy_id {strategy_id}: {e}")
        return jsonify({"error": "An error occurred while stopping the strategies"}), 500


# Rota para buscar operações do usuário
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

@main_bp.route('/generate_strategy_id', methods=['GET'])
def generate_strategy_id():
    import uuid
    strategy_id = str(uuid.uuid4())  # Gera um UUID único
    return jsonify({"strategy_id": strategy_id}), 200

# Caminho para o arquivo de símbolos
SYMBOLS_FILE_PATH = os.path.join(os.path.dirname(__file__), "symbols.json")

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