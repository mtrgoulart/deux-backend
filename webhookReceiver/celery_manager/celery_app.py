from celery import Celery
import os

# Configuração do RabbitMQ via variáveis de ambiente
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "149.102.154.104")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

CELERY_BROKER_URL = f"pyamqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}//"

# Inicializa o Celery
celery = Celery("celery_manager", broker=CELERY_BROKER_URL)

celery.conf.task_routes = {
    'process_webhook': {
        'queue': lambda user_id, instance_id, **kwargs: f'queue_{user_id}_{instance_id}',
    },
}

celery.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
}

# Dynamically create queues based on user_id and instance_id
def create_queue(user_id, instance_id):
    queue_name = f'queue_{user_id}_{instance_id}'
    celery.conf.task_queues[queue_name] = {
        'exchange': queue_name,
        'routing_key': queue_name,
    }
    
celery.conf.broker_connection_retry_on_startup = True

