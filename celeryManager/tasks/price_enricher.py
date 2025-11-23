from celery import shared_task
from celeryManager.tasks.base import logger
from source.dbmanager import load_query
from decimal import Decimal
import os
from typing import Union

# Importa AMBAS as conexões de banco de dados
from source.context import get_db_connection, get_timescale_db_connection

def get_price_from_timescale(symbol: str, executed_at_str: str) -> Union[Decimal, None]:
    """
    Busca o preço mais próximo no tempo (antes ou no momento) 
    da execução da ordem, consultando nossa tabela interna market_trades.
    
    Esta é a parte "escalável": é uma query interna rápida, não uma API.
    """
    
    # Esta query é o coração da lógica.
    # "Qual foi o último preço que vimos para este símbolo
    #  NO MÁXIMO 5 minutos antes do timestamp da execução?"
    # A janela de '5 minutes' é uma salvaguarda de segurança. Se o oráculo
    # esteve fora por 1 hora, NÃO queremos um preço de 1 hora atrás.
    normalized_symbol = symbol.replace("-", "").upper()
    query = """
        SELECT price 
        FROM market_trades
        WHERE 
            symbol = %s 
            AND timestamp <= %s::timestamptz
            AND timestamp >= (%s::timestamptz - '5 minutes'::interval)
        ORDER BY timestamp DESC
        LIMIT 1;
    """
    
    price = None
    try:
        # Usa a NOVA função de conexão com o TimescaleDB
        with get_timescale_db_connection() as ts_cursor:
            ts_cursor.execute(query, (normalized_symbol, executed_at_str, executed_at_str))
            result = ts_cursor.fetchone()
            if result:
                price = result[0] # O banco retorna um Decimal
                
        return price
        
    except Exception as e:
        logger.error(f"Erro ao consultar TimescaleDB para {symbol} @ {executed_at_str}: {e}")
        return None


@shared_task(name="price.fetch_execution_price", bind=True, max_retries=10)
def fetch_execution_price_task(self, operation_id: int, symbol: str, executed_at: str):
    """
    Enriquece a operação (do banco principal) com o preço de execução 
    (consultando o oráculo de preços interno - TimescaleDB).
    
    Configurada com 'bind=True' para permitir 'self.retry()'.
    """
    try:
        logger.info(f"PRICE_ENRICHER: Iniciando para operation_id: {operation_id} ({symbol} @ {executed_at})")
        
        # 1. Buscar o preço da NOSSA fonte interna (TimescaleDB)
        price = get_price_from_timescale(symbol, executed_at)

        if price is None:
            # --- LÓGICA DE ESCALABILIDADE E RESILIÊNCIA ---
            # O preço AINDA não foi ingerido pelo oráculo (lag normal)
            # ou o oráculo esteve fora nos últimos 5 minutos.
            # Vamos tentar novamente (backoff exponencial).
            # 1ª vez: 30s, 2ª: 60s, 3ª: 120s ...
            countdown = 30 * (2 ** self.request.retries)
            logger.warning(f"PRICE_ENRICHER: Preço para op_id {operation_id} não encontrado. Lag do oráculo? Tentando novamente em {countdown}s...")
            raise self.retry(countdown=countdown, exc=Exception("Preço (ainda) não encontrado no oráculo interno"))

        logger.info(f"PRICE_ENRICHER: Preço encontrado para op_id {operation_id}: {price}")

        # 2. Atualizar o banco de dados PRINCIPAL (PostgreSQL)
        query = load_query('update_operation_price.sql')
        
        # Usa a conexão ANTIGA (banco principal)
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (price, executed_at, operation_id))
            db_client.conn.commit()
            
        logger.info(f"PRICE_ENRICHER: Sucesso! Preço da op_id {operation_id} atualizado para {price}")
        return {"status": "success", "operation_id": operation_id, "price": float(price)}

    except Exception as e:
        # Se falhar (ex: conexão com DB, query SQL), o Celery faz o retry
        logger.error(f"PRICE_ENRICHER: Erro fatal ao buscar preço para op_id {operation_id}: {e}", exc_info=True)
        # Reagendamento com backoff exponencial
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))