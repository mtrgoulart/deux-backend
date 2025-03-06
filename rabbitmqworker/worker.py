import pika
import json
import logging
import psycopg
from configparser import ConfigParser
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from view.instances import execute_instance_operation
import cProfile
import pstats
import io

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

# 🔄 Habilitar ou desabilitar o profiling
ENABLE_PROFILING = False  # Defina como False para desativar o profiling

def process_webhook(data):
    """
    Processa mensagens da fila e executa operações de compra ou venda conforme necessário.
    """
    instance_id = data.get('instance_id')
    user_id = data.get('key')
    side = data.get('side')
    insert_data_to_db(data)
    
    if side in ['buy', 'sell']:
        logging.info(f'Executando operação de User ID: {user_id}, Instance ID={instance_id} e Side={side}')

        if ENABLE_PROFILING:
            # Iniciar profiling corretamente
            profiler = cProfile.Profile()
            profiler.enable()

            execute_instance_operation(instance_id, user_id, side)

            profiler.disable()  # Desativa o profiler após a execução
            
            # Salvar resultados
            result_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=result_stream)
            stats.strip_dirs().sort_stats("tottime").print_stats()

            # Salvar no log
            logging.info("Profiling Results:\n" + result_stream.getvalue())

            # Salvar em arquivo para análise posterior
            with open("cprofile_results.txt", "w") as f:
                f.write(result_stream.getvalue())
        else:
            # Executa normalmente sem profiling
            execute_instance_operation(instance_id, user_id, side)
            logging.info(f'Finalziado operação de User ID: {user_id}, Instance ID={instance_id} e Side={side}')


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

def callback(ch, method, properties, body):
    """Função que recebe mensagens do RabbitMQ"""
    data = json.loads(body)
    
    process_webhook(data)
    ch.basic_ack(delivery_tag=method.delivery_tag)  # Confirma processamento

def get_queues(channel):
    """Obtém todas as filas disponíveis no RabbitMQ que seguem o padrão user_*_instance_*"""
    try:
        queues = []
        for item in channel.queue_declare(queue='', passive=True):
            if item.startswith("user_") and "_instance_" in item:
                queues.append(item)
        return queues
    except Exception as e:
        logging.error(f"Erro ao obter filas do RabbitMQ: {e}")
        return []

def start_worker():
    """Inicia o worker para consumir mensagens do RabbitMQ"""
    try:
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

        # Obter todas as filas dinâmicas
        queues = get_queues(channel)
        if not queues:
            logging.info("Nenhuma fila encontrada para processar.")
            return

        for queue in queues:
            channel.basic_consume(queue=queue, on_message_callback=callback)

        logging.info(f"🔄 Worker rodando e aguardando mensagens nas filas: {queues}")
        channel.start_consuming()
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao RabbitMQ: {e}")

if __name__ == "__main__":
    start_worker()
