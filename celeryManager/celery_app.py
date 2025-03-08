from celery import Celery
import os

# Configuração do RabbitMQ via variáveis de ambiente
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "149.102.154.104")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

CELERY_BROKER_URL = f"pyamqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}//"

# Inicializa o Celery
celery = Celery("celery_manager", broker=CELERY_BROKER_URL)

celery.conf.broker_connection_retry_on_startup = True
#celery.autodiscover_tasks(["tasks"])
