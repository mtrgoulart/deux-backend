import os
from dotenv import load_dotenv
from celery import Celery
from kombu import Queue

# Carrega variáveis de ambiente do .env.prd
load_dotenv('.env.prd')

# ... (configuração do RabbitMQ e Backend permanecem iguais) ...
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PWD = os.getenv("RABBITMQ_PWD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_BROKER_URL = f"pyamqp://{RABBITMQ_USER}:{RABBITMQ_PWD}@{RABBITMQ_HOST}//"

celery = Celery("celery_manager", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
celery.conf.broker_connection_retry_on_startup = True

# === DEFINIÇÃO EXPLÍCITA DAS FILAS ===
celery.conf.task_queues = (
    Queue('webhook', routing_key='webhook.#'),
    Queue('logic',   routing_key='logic.#'),
    Queue('ops',     routing_key='ops.#'),
    Queue('db',      routing_key='db.#'),
    Queue('sharing', routing_key='sharing.#'),
)

# === ROTEAMENTO DAS TAREFAS PARA AS FILAS (CORRIGIDO) ===
# Mapeia o nome da tarefa para a fila e a chave de roteamento corretas.
celery.conf.task_routes = {
    'webhook.receipt': {'queue': 'webhook', 'routing_key': 'webhook.receipt'}, # Nome corrigido
    'webhook.processor': {'queue': 'logic', 'routing_key': 'logic.process'},     # Nome corrigido e roteado para 'logic'
    'trade.execute_operation': {'queue': 'ops', 'routing_key': 'ops.execute'},
    'trade.save_operation': {'queue': 'db', 'routing_key': 'db.save'},
    'process_sharing_operations': {'queue': 'sharing', 'routing_key': 'sharing.process'},
}

# === Descobre tasks automaticamente na pasta ===
# Certifique-se de que os arquivos com as tarefas estejam nesta pasta para serem encontrados
celery.autodiscover_tasks(['celeryManager.tasks'])