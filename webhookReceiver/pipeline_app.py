import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from celeryManager.celery_app import celery as celery_app
from log.log import general_logger
from source.tracing import generate_trace_id

# Carrega variáveis de ambiente
load_dotenv(".env.prd")

# --- App Flask ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 # Limite de 16KB para o corpo da requisição

# === Funções de Utilidade (Validação) ===

# Valid values for each pattern
VALID_SIDES = ["buy", "sell"]
VALID_PROCESSES = ["panic_stop", "resume_restart", "resume_no_restart"]


def parse_data(text: str) -> dict:
    """
    Parse and validate webhook input for dual-pattern messages.

    Pattern 1 (Instance-level): 'key:value,side:buy|sell'
    Pattern 2 (User-level): 'key:value,process:panic_stop|resume_restart|resume_no_restart'

    Returns:
        dict with keys: key, pattern ('instance' or 'user'), action (the side or process value)
    """
    try:
        entries = [entry.strip() for entry in text.split(",") if ":" in entry]
        data = {}

        for entry in entries:
            key, value = entry.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key not in ["key", "side", "process"]:
                raise ValueError(f"Chave inválida: '{key}' (somente 'key', 'side' e 'process' são permitidas)")
            if not value:
                raise ValueError(f"Valor vazio para a chave: '{key}'")

            data[key] = value

        # Validate 'key' is always present
        if "key" not in data:
            raise ValueError("A chave 'key' é obrigatória")

        # Detect pattern and validate
        has_side = "side" in data
        has_process = "process" in data

        if has_side and has_process:
            raise ValueError("Não é permitido enviar 'side' e 'process' juntos")

        if not has_side and not has_process:
            raise ValueError("É necessário enviar 'side' ou 'process'")

        if has_side:
            # Instance-level pattern
            side_value = data["side"].lower()
            if side_value not in VALID_SIDES:
                raise ValueError(f"O valor de 'side' deve ser um de: {VALID_SIDES}")

            return {
                "key": data["key"],
                "pattern": "instance",
                "action": side_value
            }

        else:
            # User-level pattern
            process_value = data["process"].lower()
            if process_value not in VALID_PROCESSES:
                raise ValueError(f"O valor de 'process' deve ser um de: {VALID_PROCESSES}")

            return {
                "key": data["key"],
                "pattern": "user",
                "action": process_value
            }

    except Exception as e:
        raise ValueError(f"Erro ao analisar os dados: {e}")

# === Rota Principal do Webhook ===
@app.route('/webhook', methods=['POST'])
def webhook_listener():
    """
    Recebe o sinal, valida o formato e o despacha para a primeira fila do Celery.
    """
    try:
        raw_body = request.get_data(as_text=True).strip()
        if not raw_body:
            general_logger.warning("Corpo da requisição vazio.")
            return jsonify({"error": "Corpo da requisição está vazio"}), 400

        # 1. Valida os dados recebidos
        try:
            parsed_data = parse_data(raw_body)
        except ValueError as e:
            general_logger.warning("Falha na validação dos dados: %s", e)
            return jsonify({"error": str(e)}), 400
        
        # 2. Gera trace_id (o registro será criado pelo primeiro worker)
        trace_id = generate_trace_id()
        key_suffix = parsed_data['key'][-4:]
        parsed_data['trace_id'] = trace_id

        # 3. Envia a tarefa para o Celery
        try:
            celery_app.send_task(
                "webhook.receipt",
                kwargs={"data": parsed_data}
            )
            general_logger.info(
                "[TraceID: %s] Sinal recebido e enfileirado para key: ...%s",
                trace_id, key_suffix
            )
        except Exception as e:
            general_logger.error("Erro ao enfileirar task no Celery: %s", e, exc_info=True)
            raise RuntimeError("Falha ao enfileirar para processamento assíncrono.")

        return jsonify({"message": "Sinal recebido e enfileirado para processamento", "trace_id": trace_id}), 202

    except Exception as e:
        general_logger.exception("Erro inesperado no endpoint do webhook")
        return jsonify({"error": "Erro interno no servidor"}), 500

if __name__ == '__main__':
    general_logger.info('Iniciando listener de Webhook do Flask')
    # O modo debug é controlado pela variável de ambiente FLASK_DEBUG
    DEBUG_MODE = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)