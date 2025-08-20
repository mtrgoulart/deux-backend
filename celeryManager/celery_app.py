## celeryManager/celery_app.py

import os
from dotenv import load_dotenv
from celery import Celery
from kombu import Queue

# Carrega variáveis de ambiente do arquivo .env.prd
# Garante que este arquivo esteja no diretório raiz do projeto
load_dotenv('.env.prd')

# --- Configuração do Broker e Backend ---
# ATENÇÃO: Verifique se seu .env.prd define as variáveis corretas.
# A imagem do RabbitMQ espera 'RABBITMQ_DEFAULT_USER' e 'RABBITMQ_DEFAULT_PASS'.
# Se você manteve 'RABBITMQ_USER' no seu .env.prd, este código está correto.
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_PWD = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

# URL de conexão com o RabbitMQ (broker)
CELERY_BROKER_URL = f"pyamqp://{RABBITMQ_USER}:{RABBITMQ_PWD}@{RABBITMQ_HOST}//"

# --- Instância do Celery ---
# O primeiro argumento é o nome do módulo principal do seu projeto Celery
celery = Celery("celeryManager")

# --- Configurações do Celery ---
celery.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='America/Sao_Paulo',
    enable_utc=True,
)

# === DEFINIÇÃO EXPLÍCITA DAS FILAS ===
# Define as filas que os workers irão consumir. Cada fila representa um tipo de trabalho.
celery.conf.task_queues = (
    Queue('webhook', routing_key='webhook.#'),   # Para recebimento rápido de webhooks
    Queue('logic',   routing_key='logic.#'),     # Para processamento de lógica de negócio
    Queue('ops',     routing_key='ops.#'),       # Para operações com a exchange (API)
    Queue('db',      routing_key='db.#'),        # Para interações com o banco de dados
    Queue('sharing', routing_key='sharing.#'),   # Para operações de compartilhamento
)

# === ROTEAMENTO DAS TAREFAS (ÚNICA FONTE DA VERDADE) ===
# Mapeia o nome exato da tarefa para a fila e a chave de roteamento desejadas.
# Isso centraliza toda a lógica de roteamento aqui.
celery.conf.task_routes = {
    'webhook.receipt':              {'queue': 'webhook', 'routing_key': 'webhook.receipt'},
    'webhook.processor':            {'queue': 'logic',   'routing_key': 'logic.process'},
    'trade.execute_operation':      {'queue': 'ops',     'routing_key': 'ops.execute'},
    'trade.save_operation':         {'queue': 'db',      'routing_key': 'db.save'},
    'process_sharing_operations':   {'queue': 'sharing', 'routing_key': 'sharing.process'},
}

# === DESCOBERTA AUTOMÁTICA DE TAREFAS ===
# O Celery irá procurar por tarefas nos arquivos dentro do pacote especificado.
# Garanta que sua estrutura de pastas seja `celeryManager/tasks/`.
celery.autodiscover_tasks(['celeryManager.tasks'])