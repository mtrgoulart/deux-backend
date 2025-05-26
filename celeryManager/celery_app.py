import os
from dotenv import load_dotenv
from celery import Celery

# Carrega variáveis de ambiente do .env.prd
load_dotenv('.env.prd')

# === RabbitMQ ===
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PWD = os.getenv("RABBITMQ_PWD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

# === Backend opcional (Postgres, Redis, etc) ===
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

# === Caminho do broker RabbitMQ ===
CELERY_BROKER_URL = f"pyamqp://{RABBITMQ_USER}:{RABBITMQ_PWD}@{RABBITMQ_HOST}//"

# === Cria instância do Celery ===
celery = Celery("celery_manager", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# === Retry automático de conexão no startup ===
celery.conf.broker_connection_retry_on_startup = True

# === Descobre tasks automaticamente na pasta ===
celery.autodiscover_tasks(['tasks'])
