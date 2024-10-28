import os
import re
import logging
import psycopg2
from configparser import ConfigParser
from flask import Flask, request, jsonify

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

# Rota do webhook para receber dados POST
@app.route('/webhook', methods=['POST'])
def webhook_listener():
    raw_data = request.form.get('data')
    if raw_data and validate_data(raw_data):
        data = model_data(raw_data)  # Modela os dados se a validação for bem-sucedida
        insert_data_to_db(data)      # Insere os dados no banco de dados
        return jsonify({"message": "Data processed and stored successfully"}), 200
    else:
        logging.warning("Requisição falhou devido a dados inválidos.")
        return jsonify({"error": "Invalid data format"}), 400

# Inicializa o servidor Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
