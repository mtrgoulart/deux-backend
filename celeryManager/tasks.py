import sys
import os
import logging
from celery import Celery
import psycopg
from configparser import ConfigParser

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # Define `root/`
sys.path.insert(0, BASE_DIR)

# 📌 Agora importa corretamente a aplicação Celery e a função `execute_instance_operation`
from celeryManager.celery_app import celery
from view.instances import execute_instance_operation, get_instance_status  # Importação correta


# Configuração do logger
logging.basicConfig(
    filename="worker.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Função para carregar configurações a partir do config.ini
def load_config(filename="config.ini"):
    parser = ConfigParser()
    parser.read(filename)
    config = {section: {param[0]: param[1] for param in parser.items(section)} for section in parser.sections()}
    return config

# Carregar configurações
config = load_config()
if not config:
    sys.exit("Arquivo de configuração não encontrado ou inválido.")

try:
    db_params = config["database"]
    data_config = config["data"]
    table_config = config["table"]
    rabbitmq_host = config["rabbitmq"]["host"]
    rabbitmq_webhook_queue = config["rabbitmq"]["queue_name"]
    rabbitmq_user = config["rabbitmq"]["user"]
    rabbitmq_password = config["rabbitmq"]["pwd"]
except KeyError as e:
    logging.error(f"Chave de configuração ausente: {e}")
    sys.exit("Configuração incorreta. Verifique o arquivo config.ini.")


@celery.task(bind=True, name="process_webhook")
def process_webhook(self, data):
    """Processa a mensagem recebida e executa a operação"""
    user_id = data.get("key", None)
    instance_id = data.get("instance_id", None)
    side = data.get("side", None)

    if not user_id or not instance_id or not side:
        logging.info(f"Parâmetro nulo {user_id}, {instance_id}, {side}")
        return {"status": None, "message": "Parameter None"}


    instance_status = get_instance_status(instance_id, user_id)
    if not instance_status:
        logging.warning(f"Unkown status {instance_status} for instance {instance_id}")
        return {"status": "error", "message": f"Unknown status {instance_status}"}
    
    if instance_status == 1:
        logging.info(f"Instance {instance_id} not running")
        return {"status": None, "message": "Instance not running"}

    elif instance_status == 2:
        if side in ["buy", "sell"]:
            insert_data_to_db(data)
            #result = execute_instance_operation(instance_id, user_id, side)
            result=logging.info('Chegou no execute instance operation')
        else:
            logging.warning(f"⚠ Operação inválida: {side}")
            return {"status": "error", "message": "Invalid side"}

        return result

    logging.warning(f"Unkown status {instance_status} for instance {instance_id}")
    return {"status": "error", "message": f"Unknown status {instance_status}"}


def insert_data_to_db(data):
    table_name = table_config["table_name"]
    fields = data_config["data_fields"].split(",")
    
    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    
    try:
        with psycopg.connect(**db_params) as conn:
            with conn.cursor() as cursor:
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                values = [data[field] for field in fields]
                cursor.execute(query, values)
                conn.commit()
                logging.info("Dados inseridos com sucesso no banco de dados.")
    except Exception as e:
        logging.error("Erro ao inserir dados no banco: %s", e)