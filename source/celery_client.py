from celery import Celery
import os

def get_client():
    return Celery(
        "backend_client",
        broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
    )
