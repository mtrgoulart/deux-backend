from contextlib import contextmanager
from .pp import ConfigLoader
from .dbmanager import DatabaseClient

@contextmanager
def get_db_connection():
    config = ConfigLoader()
    db_client = DatabaseClient(
        dbname=config.get('database', 'dbname'),
        user=config.get('database', 'user'),
        password=config.get('database', 'password'),
        host=config.get('database', 'host'),
        port=int(config.get('database', 'port'))
    )
    try:
        db_client.connect()
        yield db_client
    finally:
        db_client.close()
