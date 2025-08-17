from celery import shared_task
# Logger do Celery já está configurado, vamos usá-lo
from celeryManager.tasks.base import logger
from interface.webhook_auth import authenticate_signal, insert_data_to_db
from interface.instance import get_instance_status, execute_instance_operation

# 1. Adicionado `bind=True` para acessar o contexto da task (self)
@shared_task(name="process_webhook", queue="webhook", bind=True)
def process_webhook(self, data):
    # 2. Usar o ID da task do Celery como nosso ID de execução principal.
    task_id = self.request.id
    log_prefix = f"[TaskID: {task_id}]"

    #logger.info(f"{log_prefix} Iniciando processamento do webhook.")
    # Use DEBUG para dados brutos/verbosos.
    logger.debug(f"{log_prefix} Dados recebidos: {data}")

    try:
        key = data.get("key")
        side = data.get("side")

        # --- Etapa: Validação de Parâmetros ---
        if not key or not side:
            # 3. Log claro sobre o motivo da saída prematura.
            logger.warning(f"{log_prefix} Parâmetros obrigatórios ausentes. Key: '{key}', Side: '{side}'.")
            return {"status": "error", "message": "Parâmetros ausentes"}

        signal_data = authenticate_signal(key)
        
        if not signal_data:
            logger.warning(f"{log_prefix} Autenticação falhou. Chave de sinal inválida: ...{key[-4:]}")
            return {"status": "error", "message": "Invalid signal"}

        # 4. Enriquecendo o contexto do log com dados da autenticação.
        user_id = signal_data['user_id']
        instance_id = signal_data['instance_id']
        symbol = signal_data.get('symbol')
        
        log_prefix = f"[TaskID: {task_id}] [Instance: {instance_id}] [User: {user_id}] [Side: {side}]"
        # --- Etapa: Verificação de Status da Instância ---
        status = get_instance_status(instance_id, user_id)

        if status is None:
            logger.error(f"{log_prefix} Instância não encontrada no banco de dados.")
            return {"status": "error", "message": "Instance not found"}

        if status == 1: # Not running
            logger.info(f"{log_prefix} Instância não está em execução (status=1). Finalizando tarefa como esperado.")
            return {"status": "ignored", "message": "Instance not running"}

        if status != 2: # Unexpected status
            logger.error(f"{log_prefix} Status desconhecido ou não manipulado: {status}.")
            return {"status": "error", "message": f"Unknown status {status}"}

        # --- Etapa: Execução (Status == 2) ---
        logger.info(f"{log_prefix} Instância está ativa (status=2). Processando operação para o lado '{side}'.")
        if side not in ["buy", "sell"]:
            logger.error(f"{log_prefix} Lado (side) inválido recebido: '{side}'.")
            return {"status": "error", "message": "Invalid side"}
        
        db_data = {
            "key": key,
            "symbol": symbol,
            "side": side,
            "indicator_id": signal_data.get('indicator_id'),
            "instance_id": instance_id
        }
        
        logger.info(f"{log_prefix} Inserindo dados do webhook no DB.")
        insert_data_to_db(db_data)
        logger.info(f"{log_prefix} Dados inseridos. Disparando execução da operação na instância.")
        
        result = execute_instance_operation(instance_id, user_id, side)
        logger.info(f"{log_prefix} Operação da instância executada. Resultado: {result}")
        return result

    except Exception as e:
        # 5. Captura de exceções inesperadas para não perder o erro.
        logger.error(f"{log_prefix} Ocorreu uma exceção não tratada durante o processamento. Erro: {e}", exc_info=True)
        # Re-lançar a exceção fará com que o Celery marque a task como FALHA.
        raise
    finally:
        # 6. Log final que sempre será executado.
        logger.info(f"{log_prefix} Finalizando processamento do webhook.")