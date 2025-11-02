from contextlib import contextmanager
from .pp import ConfigLoader
from .dbmanager import DatabaseClient
import psycopg2
import os

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


@contextmanager
def get_timescale_db_connection():
    """
    Context manager para conexões com o banco de dados TimescaleDB (leitura de preços).
    Lê as variáveis de ambiente TIMESCALE_*.
    """
    try:
        # Pega as credenciais do .env.prd (que o Docker injeta)
        # O host 'db_timescale' é o nome do serviço no docker-compose
        conn = psycopg2.connect(
            dbname=os.getenv("TIMESCALE_DB"),
            user=os.getenv("TIMESCALE_USER"),
            password=os.getenv("TIMESCALE_PASSWORD"),
            host=os.getenv("TIMESCALE_HOST", "db_timescale"), 
            port="5432" # Porta interna do Docker
        )
        cursor = conn.cursor()
        yield cursor  # Fornece o cursor para o bloco 'with'
    except Exception as e:
        # Em um cenário real, logger.error(f"Erro de conexão com TimescaleDB: {e}")
        print(f"Erro de conexão com TimescaleDB: {e}")
        raise
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()