import sys
import os
import logging
from dotenv import load_dotenv

# Carrega variáveis do .env.prd
load_dotenv()

# Configuração global de log
LOG_FILE = os.getenv("LOG_FILE", "worker.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# === Banco de dados (psycopg connection dict) ===
try:
    db_params = {
        "host": os.environ["DB_HOST"],
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "port": os.environ.get("DB_PORT", 5432)
    }
except KeyError as e:
    logger.error(f"[ENV] Variável de ambiente ausente: {e}")
    sys.exit("Erro na configuração do banco de dados.")

# === Data / Tabela ===
try:
    data_config = {
        "regex_pattern": os.environ["REGEX_PATTERN"],
        "data_fields": os.environ["DATA_FIELDS"]
    }

    table_config = {
        "table_name": os.environ["TABLE_NAME"]
    }

except KeyError as e:
    logger.error(f"[ENV] Variável de ambiente ausente: {e}")
    sys.exit("Erro na configuração de dados ou tabela.")
