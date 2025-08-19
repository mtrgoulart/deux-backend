from celery import shared_task
from celeryManager.tasks.base import logger
from interface.webhook_auth import authenticate_signal
# SOLUÇÃO: Importamos a tarefa com um novo nome ('alias') para evitar conflito.
from celeryManager.tasks.webhook_processor import process_webhook as process_webhook_task

@shared_task(name="webhook.receipt", bind=True)
def process_webhook_receipt(self, data): # O nome da função também foi ajustado para clareza
    task_id = self.request.id
    log_prefix = f"[WebhookTaskID: {task_id}]"
    logger.info(f"{log_prefix} Iniciando processamento rápido do webhook.")
    
    try:
        key = data.get("key")
        side = data.get("side")

        if not key or side not in ["buy", "sell"]:
            logger.warning(f"{log_prefix} Parâmetros ausentes ou inválidos. Key: '{key}', Side: '{side}'.")
            return {"status": "error", "message": "Parâmetros ausentes ou inválidos"}

        # ÚNICA CONSULTA AO BANCO NESTA TAREFA
        signal_data = authenticate_signal(key)
        
        if not signal_data:
            logger.warning(f"{log_prefix} Autenticação falhou: ...{key[-4:]}")
            return {"status": "error", "message": "Invalid signal"}
        
        logger.info(f"{log_prefix} Sinal autenticado. Delegando para a fila de lógica.")

        # SOLUÇÃO: Chamamos a tarefa importada com o novo nome.
        process_webhook_task.delay(
            signal_data=signal_data, 
            side=side, 
            original_key=key
        )
        
        return {"status": "queued", "message": "Sinal aceito e enfileirado para processamento."}

    except Exception as e:
        logger.error(f"{log_prefix} Erro no processador de webhook: {e}", exc_info=True)
        raise