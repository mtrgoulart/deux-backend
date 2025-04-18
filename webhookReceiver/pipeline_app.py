import os
import sys

# Define o caminho da pasta raiz do projeto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # webhookReceiver/
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../"))  # Diretório raiz do projeto
sys.path.insert(0, os.path.abspath(os.path.join(BASE_DIR, '..')))  # Adiciona a raiz ao sys.path

import re
import logging
from configparser import ConfigParser
from flask import Flask, request, jsonify
from celeryManager.tasks import process_webhook 



# Função para carregar configurações a partir do config.ini
def load_config(filename="config.ini"):
    parser = ConfigParser()
    parser.read(filename)
    config = {section: {param[0]: param[1] for param in parser.items(section)} for section in parser.sections()}
    return config

# Configuração do logger
def setup_logging(log_file, log_level):
    logging.basicConfig(
        filename=log_file,
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


# Carregar configurações e configurar logger
config = load_config()
db_params = config["database"]
data_config = config["data"]
table_config = config["table"]


setup_logging(config["logging"]["log_file"], config["logging"]["log_level"])

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Função para validar o formato dos dados
def validate_data(data):
    pattern = data_config["regex_pattern"]
    is_valid = bool(re.fullmatch(pattern, data))
    if not is_valid:
        logging.warning("Dados inválidos recebidos: %s", data)
    return is_valid

# Função para modelar os dados
def model_data(data):
    parsed_data = dict(item.split('=') for item in data.split(','))
    logging.info("Dados modelados com sucesso: %s", parsed_data)

    # Ordena os dados conforme os campos especificados em data_fields
    fields = data_config["data_fields"].split(",")
    return {field: parsed_data.get(field) for field in fields}

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    try:
        # Captura o corpo da requisição como texto
        raw_body = request.get_data(as_text=True)
        raw_data = dict(item.split("=") for item in raw_body.split(","))
        
        # Lógica para capturar o dado a ser validado
        
        if raw_data and isinstance(raw_data, dict) and 'data' in raw_data:
            data_to_validate = raw_data['data']
        else:
            data_to_validate = raw_body


        # Valida os dados
        if validate_data(data_to_validate):
            
            modeled_data = model_data(data_to_validate)  # Modela os dados validados
            print(modeled_data)
            try:
                process_webhook.apply_async(kwargs={"data": modeled_data})
            except Exception as e:
                print(f'Não possivel processar o webhook {e}')

            print(f'Mensagem enviada para celery com sucesso')
            return jsonify({"message": "Data processed and stored successfully"}), 200
        else:
            logging.warning("Requisição falhou devido a dados inválidos.")
            return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        logging.error(f"Erro ao processar a requisição: {str(e)}")
        return jsonify({"error": "Internal server error "}), 500
    
# Inicializa o servidor Flask
if __name__ == '__main__':
    print('iniciando webhook')
    app.run(host='0.0.0.0', port=5000, debug=True)
