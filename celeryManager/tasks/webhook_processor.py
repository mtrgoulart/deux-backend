from celery import shared_task
from celeryManager.tasks.base import logger
from interface.instance import get_instance_status, execute_instance_operation
from interface.webhook_auth import insert_data_to_db

@shared_task(name="webhook.processor", bind=True)
def process_webhook(self, signal_data, side, original_key):
    """
    Executa a lógica de negócio pesada de forma assíncrona.
    """
    task_id = self.request.id
    instance_id = signal_data['instance_id']
    user_id = signal_data['user_id']
    symbol = signal_data.get('symbol')

    log_prefix = f"[OrchestratorTaskID: {task_id}] [Instance: {instance_id}] [User: {user_id}]"
    logger.info(f"{log_prefix} Iniciando orquestração da lógica de trade.")

    try:
        status = get_instance_status(instance_id, user_id)

        if status is None:
            logger.error(f"{log_prefix} Instância não encontrada.")
            return {"status": "error", "message": "Instance not found"}
        if status != 2:
            logger.info(f"{log_prefix} Instância não está em execução (status={status}). Finalizando.")
            return {"status": "ignored", "message": f"Instance not running (status={status})"}

        logger.info(f"{log_prefix} Instância ativa. Inserindo dados no DB.")
        db_data = {
            "key": original_key, "symbol": symbol, "side": side,
            "indicator_id": signal_data.get('indicator_id'), "instance_id": instance_id
        }
        insert_data_to_db(db_data)
        
        logger.info(f"{log_prefix} Dados inseridos. Disparando execução da operação.")
        result = execute_instance_operation(instance_id, user_id, side)
        logger.info(f"{log_prefix} Operação executada. Resultado: {result}")
        return result
    except Exception as e:
        logger.error(f"{log_prefix} Exceção na orquestração: {e}", exc_info=True)
        raise