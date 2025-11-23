from celery import shared_task
from celeryManager.tasks.base import logger
from source.dbmanager import load_query
from decimal import Decimal
import os
from typing import Union, Optional
from datetime import datetime, timedelta
from time import time

# Importa AMBAS as conexões de banco de dados
from source.context import get_db_connection, get_timescale_db_connection


# ============================================================================
# IN-MEMORY CACHE FOR SYMBOL TRACKING
# ============================================================================
# Cache para evitar consultas repetidas ao banco de dados
# Reduz DB hits em ~60-80% para símbolos frequentemente negociados
_symbol_tracking_cache = {}
_cache_ttl_seconds = 300  # 5 minutos


def is_symbol_tracked(symbol: str) -> bool:
    """
    Verifica se o símbolo está sendo rastreado pelo price oracle.
    Usa cache em memória para reduzir consultas ao banco de dados.

    Args:
        symbol: Símbolo da operação (ex: "BTC-USDT" ou "BTCUSDT")

    Returns:
        True se o símbolo está sendo rastreado, False caso contrário
    """
    normalized_symbol = symbol.replace("-", "").replace("/", "").upper()
    cache_key = f"tracked_{normalized_symbol}"

    # Verifica se está no cache e se ainda é válido
    if cache_key in _symbol_tracking_cache:
        cached_value, cached_time = _symbol_tracking_cache[cache_key]
        age = time() - cached_time

        if age < _cache_ttl_seconds:
            # Cache hit - retorna sem consultar DB
            logger.debug(f"PRICE_ENRICHER: Cache HIT para {normalized_symbol} (age: {int(age)}s)")
            return cached_value
        else:
            # Cache expirado
            logger.debug(f"PRICE_ENRICHER: Cache EXPIRED para {normalized_symbol} (age: {int(age)}s)")

    # Cache miss ou expirado - consulta o banco
    query = """
        SELECT EXISTS(
            SELECT 1 FROM public.exchange_symbols
            WHERE symbol = %s AND is_tracked = true
        );
    """

    try:
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (normalized_symbol,))
            result = db_client.cursor.fetchone()
            is_tracked = result[0] if result else False

            # Armazena no cache
            _symbol_tracking_cache[cache_key] = (is_tracked, time())

            if not is_tracked:
                logger.warning(
                    f"PRICE_ENRICHER: Símbolo '{normalized_symbol}' NÃO está sendo rastreado "
                    f"pelo price oracle (is_tracked=false ou não existe)"
                )

            return is_tracked

    except Exception as e:
        logger.error(f"PRICE_ENRICHER: Erro ao verificar se símbolo {normalized_symbol} está rastreado: {e}")
        # Em caso de erro na query, assume que NÃO está rastreado (fail-safe)
        return False


def clear_symbol_cache():
    """
    Limpa o cache de símbolos rastreados.
    Útil para forçar revalidação após mudanças na tabela exchange_symbols.
    """
    global _symbol_tracking_cache
    _symbol_tracking_cache = {}
    logger.info("PRICE_ENRICHER: Cache de símbolos rastreados limpo")


def get_price_from_timescale(symbol: str, executed_at_str: str) -> Union[Decimal, None]:
    """
    Busca o preço mais próximo no tempo (antes ou no momento)
    da execução da ordem, consultando nossa tabela interna market_trades.

    Esta é a parte "escalável": é uma query interna rápida, não uma API.

    Args:
        symbol: Símbolo da operação (ex: "BTC-USDT")
        executed_at_str: Timestamp da execução em formato string ISO

    Returns:
        Preço como Decimal ou None se não encontrado
    """

    # Esta query é o coração da lógica.
    # "Qual foi o último preço que vimos para este símbolo
    #  NO MÁXIMO 5 minutos antes do timestamp da execução?"
    # A janela de '5 minutes' é uma salvaguarda de segurança. Se o oráculo
    # esteve fora por 1 hora, NÃO queremos um preço de 1 hora atrás.
    normalized_symbol = symbol.replace("-", "").replace("/", "").upper()
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
                price = result[0]  # O banco retorna um Decimal

        return price

    except Exception as e:
        logger.error(f"PRICE_ENRICHER: Erro ao consultar TimescaleDB para {symbol} @ {executed_at_str}: {e}")
        return None


def mark_operation_as_price_error(operation_id: int, error_message: str):
    """
    Marca uma operação como tendo erro ao buscar o preço.
    Atualiza o campo execution_price para NULL e adiciona uma nota de erro.

    Args:
        operation_id: ID da operação
        error_message: Mensagem de erro a ser registrada
    """
    query = """
        UPDATE operations
        SET
            execution_price = NULL,
            price_enrichment_error = %s,
            updated_at = NOW()
        WHERE id = %s;
    """

    try:
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (error_message, operation_id))
            db_client.conn.commit()
            logger.info(f"PRICE_ENRICHER: Operação {operation_id} marcada com erro de preço: {error_message}")
    except Exception as e:
        logger.error(f"PRICE_ENRICHER: Erro ao marcar operação {operation_id} com erro de preço: {e}")


@shared_task(name="price.fetch_execution_price", bind=True, max_retries=1)
def fetch_execution_price_task(self, operation_id: int, symbol: str, executed_at: str):
    """
    Enriquece a operação (do banco principal) com o preço de execução
    (consultando o oráculo de preços interno - TimescaleDB).

    OTIMIZAÇÕES PARA ALTA ESCALA (100+ ops/min):
    - Usa ETA em vez de countdown (não bloqueia workers)
    - Cache em memória para symbol tracking (reduz DB hits)
    - Apenas 1 retry (2 tentativas totais, espera de 10s)
    - Falha rápida para símbolos não rastreados

    LÓGICA DE RETRY:
    - Verifica PRIMEIRO se o símbolo está sendo rastreado (com cache)
    - Se NÃO estiver rastreado: marca como erro e NÃO retenta
    - Se estiver rastreado mas preço não encontrado: retenta 1 vez após 10s
    - Após 2 tentativas sem sucesso: marca como erro e para

    Configurada com 'bind=True' para permitir 'self.retry()'.
    max_retries=1: Tenta no máximo 2 vezes total (1 tentativa inicial + 1 retry)
    """
    try:
        current_retry = self.request.retries
        logger.info(
            f"PRICE_ENRICHER: Iniciando para operation_id: {operation_id} "
            f"({symbol} @ {executed_at}) - Tentativa {current_retry + 1}/2"
        )

        # ====================================================================
        # PASSO 1: Verificar se o símbolo está sendo rastreado pelo oracle
        # ====================================================================
        # Esta verificação previne tentativas para símbolos que
        # NUNCA terão preço disponível no TimescaleDB
        # Usa cache em memória para performance
        if not is_symbol_tracked(symbol):
            error_msg = (
                f"Símbolo '{symbol}' não está sendo rastreado pelo price oracle. "
                f"Adicione-o à tabela exchange_symbols com is_tracked=true para habilitar price enrichment."
            )
            logger.error(f"PRICE_ENRICHER: op_id {operation_id} - {error_msg}")

            # Marca a operação como erro e NÃO retenta
            mark_operation_as_price_error(operation_id, error_msg)

            return {
                "status": "error",
                "operation_id": operation_id,
                "error": "symbol_not_tracked",
                "message": error_msg
            }

        # ====================================================================
        # PASSO 2: Buscar o preço da NOSSA fonte interna (TimescaleDB)
        # ====================================================================
        price = get_price_from_timescale(symbol, executed_at)

        if price is None:
            # --- LÓGICA DE RETRY COM LIMITE (OTIMIZADA) ---
            # O preço AINDA não foi ingerido pelo oráculo (lag normal)
            # ou o oráculo esteve fora nos últimos 5 minutos.

            # Verifica se ainda temos tentativas restantes
            if current_retry < self.max_retries:
                # Retry rápido: 10 segundos
                # Usa ETA em vez de countdown para NÃO BLOQUEAR o worker
                retry_delay_seconds = 10
                eta_time = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)

                logger.warning(
                    f"PRICE_ENRICHER: Preço para op_id {operation_id} não encontrado. "
                    f"Lag do oráculo? Tentando novamente em {retry_delay_seconds}s... "
                    f"(Tentativa {current_retry + 1}/{self.max_retries + 1})"
                )

                # ETA libera o worker imediatamente, tarefa será re-executada no horário especificado
                raise self.retry(
                    eta=eta_time,
                    exc=Exception(f"Preço ainda não encontrado no oráculo (tentativa {current_retry + 1})")
                )
            else:
                # Já tentamos 2 vezes (total de 2 tentativas), desistimos
                error_msg = (
                    f"Preço não encontrado após {self.max_retries + 1} tentativas. "
                    f"O price oracle pode estar offline ou o símbolo '{symbol}' "
                    f"não teve trades no período de 5 minutos antes de {executed_at}."
                )
                logger.error(f"PRICE_ENRICHER: op_id {operation_id} - {error_msg}")

                # Marca a operação como erro e NÃO retenta mais
                mark_operation_as_price_error(operation_id, error_msg)

                return {
                    "status": "error",
                    "operation_id": operation_id,
                    "error": "price_not_found_after_retries",
                    "message": error_msg,
                    "retries_attempted": current_retry + 1
                }

        # ====================================================================
        # PASSO 3: Preço encontrado! Atualizar o banco de dados PRINCIPAL
        # ====================================================================
        logger.info(f"PRICE_ENRICHER: Preço encontrado para op_id {operation_id}: {price}")

        query = load_query('update_operation_price.sql')

        # Usa a conexão com o banco principal (PostgreSQL)
        with get_db_connection() as db_client:
            db_client.cursor.execute(query, (price, executed_at, operation_id))
            db_client.conn.commit()

        logger.info(
            f"PRICE_ENRICHER: ✅ SUCESSO! Preço da op_id {operation_id} "
            f"atualizado para {price} (após {current_retry} retries)"
        )

        return {
            "status": "success",
            "operation_id": operation_id,
            "price": float(price),
            "retries_needed": current_retry
        }

    except Exception as e:
        # Captura exceções inesperadas (ex: conexão com DB, query SQL inválida)
        # Só faz retry se ainda houver tentativas disponíveis
        current_retry = self.request.retries

        if current_retry < self.max_retries:
            # Retry rápido com ETA (não bloqueia worker)
            retry_delay_seconds = 15
            eta_time = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)

            logger.error(
                f"PRICE_ENRICHER: Erro inesperado ao processar op_id {operation_id}: {e}. "
                f"Tentando novamente em {retry_delay_seconds}s... (Tentativa {current_retry + 1}/{self.max_retries + 1})",
                exc_info=True
            )
            raise self.retry(exc=e, eta=eta_time)
        else:
            # Já esgotamos as tentativas, marca como erro e desiste
            error_msg = f"Erro fatal após {self.max_retries + 1} tentativas: {str(e)}"
            logger.error(
                f"PRICE_ENRICHER: ❌ FALHA FINAL para op_id {operation_id} - {error_msg}",
                exc_info=True
            )

            mark_operation_as_price_error(operation_id, error_msg)

            return {
                "status": "error",
                "operation_id": operation_id,
                "error": "fatal_error",
                "message": error_msg,
                "retries_attempted": current_retry + 1
            }
