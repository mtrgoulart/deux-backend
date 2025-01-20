import os
import re
import logging
import psycopg2
from configparser import ConfigParser
from flask import Flask, request, jsonify
import pika

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


# Função para enviar mensagens ao RabbitMQ
def send_to_rabbitmq(data):
    try:
        rabbitmq_params = config["rabbitmq"]
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_params["host"])
        )
        channel = connection.channel()

        # Declarar a fila
        queue_name = rabbitmq_params["queue_name"]
        channel.queue_declare(queue=queue_name, durable=True)

        # Publicar a mensagem
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=str(data),
            properties=pika.BasicProperties(delivery_mode=2)  # Mensagens persistentes
        )
        logging.info("Mensagem enviada ao RabbitMQ: %s", data)
        connection.close()
    except Exception as e:
        logging.error("Erro ao enviar mensagem ao RabbitMQ: %s", e)

# Carregar configurações e configurar logger
config = load_config()
db_params = config["postgresql"]
data_config = config["data"]
table_config = config["table"]

setup_logging(config["logging"]["log_file"], config["logging"]["log_level"])

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Função para validar o formato dos dados
def validate_data(data):
    pattern = data_config["regex_pattern"]
    is_valid = bool(re.fullmatch(pattern, data))
    if is_valid:
        logging.info("Dados válidos recebidos.")
    else:
        logging.warning("Dados inválidos recebidos: %s", data)
    return is_valid

# Função para modelar os dados
def model_data(data):
    parsed_data = dict(item.split('=') for item in data.split(','))
    logging.info("Dados modelados com sucesso: %s", parsed_data)

    # Ordena os dados conforme os campos especificados em data_fields
    fields = data_config["data_fields"].split(",")
    return {field: parsed_data.get(field) for field in fields}

# Função para inserir os dados no banco de dados PostgreSQL
def insert_data_to_db(data):
    table_name = table_config["table_name"]
    fields = data_config["data_fields"].split(",")
    
    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    
    try:
        with psycopg2.connect(**db_params) as conn:
            with conn.cursor() as cursor:
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                values = [data[field] for field in fields]
                cursor.execute(query, values)
                conn.commit()
                logging.info("Dados inseridos com sucesso no banco de dados.")
    except Exception as e:
        logging.error("Erro ao inserir dados no banco: %s", e)

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    try:
        # Captura o corpo da requisição como texto
        raw_body = request.get_data(as_text=True)
        logging.info(f'Dados recebidos no POST (raw body): {raw_body}')

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
            insert_data_to_db(modeled_data)  # Insere os dados no banco
            #send_to_rabbitmq(modeled_data)  # Envia para o RabbitMQ
            return jsonify({"message": "Data processed and stored successfully"}), 200
        else:
            logging.warning("Requisição falhou devido a dados inválidos.")
            return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        logging.error(f"Erro ao processar a requisição: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
# Inicializa o servidor Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
