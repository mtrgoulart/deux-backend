import psycopg
from celeryManager.tasks.base import db_params, data_config, table_config, logger

def insert_data_to_db(data):
    table_name = table_config["table_name"]
    fields = data_config["data_fields"].split(",")

    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    values = [data.get(field) for field in fields]

    try:
        with psycopg.connect(**db_params) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values
                )
                conn.commit()
                logger.info("Dados inseridos com sucesso no banco.")
    except Exception as e:
        logger.error(f"Erro ao inserir no banco: {e}")
