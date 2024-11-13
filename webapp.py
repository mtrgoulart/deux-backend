from flask import Flask, request, jsonify, render_template
from source.director import OperationManager
from log.log import general_logger

app = Flask(__name__, template_folder='../templates')

operation_manager = None  # Variável global para armazenar a instância de OperationManager

# Rota para a interface HTML
@app.route('/')
def index():
    general_logger.info("Acessou a página inicial.")
    return render_template('index.html')  # Flask procurará automaticamente na pasta 'templates'

@app.route('/start_operation', methods=['POST'])
def start_operation():
    global operation_manager
    data = request.json
    general_logger.info("Requisição recebida para iniciar operação.")
    general_logger.debug(f"Dados recebidos para operação: {data}")
    try:
        percent = float(data.get('percent'))
        avaiable_size = float(data.get('avaiable_size'))
        condition_limit = data.get('condition_limit')
        interval = float(data.get('interval'))
        symbol = data.get('symbol')
        side = data.get('side')

        general_logger.info(f"Iniciando operação para o símbolo {symbol} ({side}).")
        operation_manager = OperationManager(percent, avaiable_size, condition_limit, interval, symbol, side)
        operation_manager.start_operation()
        general_logger.info("Operação iniciada com sucesso.")
        return jsonify({"message": "Operation started successfully"}), 200
    except Exception as e:
        general_logger.error(f"Erro ao iniciar operação: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/stop_operation', methods=['POST'])
def stop_operation():
    data = request.json
    symbol = data.get('symbol')
    side = data.get('side')
    general_logger.info(f"Requisição recebida para parar operação para {symbol} ({side}).")

    # Verifica se a operação específica está em execução
    global operation_manager
    if operation_manager and operation_manager.symbol == symbol and operation_manager.side == side:
        general_logger.info(f"Parando operação para {symbol} ({side}).")
        operation_manager.stop_operation()
        general_logger.info(f"Operação para {symbol} ({side}) parada com sucesso.")
        return jsonify({"message": f"Operation for {symbol} ({side}) stopped successfully"}), 200
    general_logger.warning(f"Nenhuma operação em execução para {symbol} ({side}).")
    return jsonify({"error": f"No operation running for {symbol} ({side})"}), 400

if __name__ == "__main__":
    general_logger.info("Iniciando aplicação Flask.")
    app.run(host="0.0.0.0", port=5000)

