from flask import Flask, request, jsonify, render_template
#from log.log import general_logger
import subprocess
import json

app = Flask(__name__, template_folder='../templates')

operation_manager = None  # Variável global para armazenar a instância de OperationManager

# Rota para a interface HTML
@app.route('/')
def index():
    #general_logger.info("Acessou a página inicial.")
    return render_template('frontpage.html')  # Flask procurará automaticamente na pasta 'templates'

@app.route('/start_operation', methods=['POST'])
def start_operation():
    try:
        # Captura os dados recebidos no corpo da requisição
        data = request.get_json()
        
        # Verifica se os parâmetros obrigatórios estão presentes
        required_fields = ['percent', 'avaiable_size', 'condition_limit', 'interval', 'symbol', 'side']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required parameters"}), 400

        # Converte os dados para um JSON string (necessário para o curl)
        data_json = json.dumps(data)

        # Comando curl
        curl_command = [
            "curl",
            "-X", "POST",
            "http://172.20.0.1:8080/start_operation",
            "-H", "Content-Type: application/json",
            "-d", data_json
        ]

        # Executa o comando curl
        process = subprocess.run(curl_command, capture_output=True, text=True)

        # Verifica se o comando foi executado com sucesso
        if process.returncode != 0:
            return jsonify({"error": process.stderr.strip()}), 500

        # Retorna a resposta do comando curl
        return jsonify({"message": "Operation started successfully", "response": process.stdout.strip()}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stop_operation', methods=['POST'])
def stop_operation():
    try:
        # Captura os dados recebidos no corpo da requisição
        data = request.get_json()
        
        # Verifica se os parâmetros obrigatórios estão presentes
        required_fields = ['symbol', 'side']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required parameters"}), 400

        # Converte os dados para um JSON string (necessário para o curl)
        data_json = json.dumps(data)

        # Comando curl
        curl_command = [
            "curl",
            "-X", "POST",
            "http://172.20.0.1:8080/stop_operation",
            "-H", "Content-Type: application/json",
            "-d", data_json
        ]

        # Executa o comando curl
        process = subprocess.run(curl_command, capture_output=True, text=True)

        # Verifica se o comando foi executado com sucesso
        if process.returncode != 0:
            return jsonify({"error": process.stderr.strip()}), 500

        # Retorna a resposta do comando curl
        return jsonify({"message": "Operation stopped successfully", "response": process.stdout.strip()}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    #general_logger.info("Iniciando aplicação Flask.")
    app.run(host="0.0.0.0", port=5001)
