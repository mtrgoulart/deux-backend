import os
import sys

# Define o caminho da pasta raiz do projeto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # webhookReceiver/
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../"))  # Diretório raiz do projeto
sys.path.insert(0, ROOT_DIR)  # Adiciona a raiz ao sys.path

import re
import logging
import psycopg
from configparser import ConfigParser
from flask import Flask, request, jsonify
from celery_manager.tasks import process_webhook  # Agora Celery Manager é encontrado corretamente
from celery_manager.celery_app import create_queue



# Função para carregar configurações a partir do config.ini
def load_config(filename="webhookreceiver/config.ini"):
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
rabbitmq_host=config['rabbitmq']['host']
rabbitmq_webhook_queue=config['rabbitmq']['queue_name']
rabbitmq_user=config['rabbitmq']['user']
rabbitmq_password=config['rabbitmq']['pwd']

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

# Envio para o rabbitmq
def send_to_rabbitmq(data):
    try:
        user_id = data.get("key", "unknown")
        instance_id = data.get("instance_id", "unknown")

        queue_name = f"user_{user_id}_instance_{instance_id}"
        TTL_MS = 600000  # 10 minutos (600.000 milissegundos)

        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
        parameters = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=5672,
            virtual_host="/",
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declara a fila com tempo de vida por inatividade
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={'x-expires': TTL_MS}  # Define o tempo de vida da fila
        )

        # Publica a mensagem na fila específica
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        connection.close()
        logging.info(f"Dados enviados para fila: {queue_name}")
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem para RabbitMQ: {e}")



@app.route('/webhook', methods=['POST'])
def webhook_listener():
    try:
        # Captura o corpo da requisição como texto
        raw_body = request.get_data(as_text=True)

        # Tenta processar os dados como JSON
        try:
            raw_data = request.json
            #logging.info(f'Dados processados como JSON: {raw_data}')
        except Exception:
            raw_data = None

        # Lógica para capturar o dado a ser validado
        if raw_data and isinstance(raw_data, dict) and 'data' in raw_data:
            # Se 'data' estiver presente, usa apenas o valor dele
            data_to_validate = raw_data['data']
            #logging.info(f'Parâmetro "data" extraído: {data_to_validate}')
        else:
            # Caso contrário, usa o corpo da requisição diretamente
            data_to_validate = raw_body
            logging.info(f'Usando corpo bruto para validação: {data_to_validate}')

        # Valida os dados
        if validate_data(data_to_validate):
            modeled_data = model_data(data_to_validate)  # Modela os dados validados
            create_queue(modeled_data['user_id'], modeled_data['instance_id'])
            
            # Envia para o Celery with the dynamic queue
            process_webhook.apply_async(args=[modeled_data], queue=f'queue_{modeled_data['user_id']}_{modeled_data['instance_id']}')
            return jsonify({"message": "Data processed and stored successfully"}), 200
        else:
            logging.warning("Requisição falhou devido a dados inválidos.")
            return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        logging.error(f"Erro ao processar a requisição: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
# Inicializa o servidor Flask
if __name__ == '__main__':
    print('iniciando webhook')
    app.run(host='0.0.0.0', port=5000, debug=True)
