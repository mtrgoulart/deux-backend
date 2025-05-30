import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from celeryManager.celery_app import celery as celery_app
from log.log import general_logger

# Carrega variáveis de ambiente
load_dotenv(".env")

# Configuração do logger
LOG_FILE = "webhook.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024

# === Funções de utilidade ===
def parse_data(text: str) -> dict:
    """Valida e parseia entrada no formato 'key:valor,side:buy|sell'."""
    try:
        entries = [entry.strip() for entry in text.split(",") if ":" in entry]
        data = {}

        for entry in entries:
            key, value = entry.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key not in ["key", "side"]:
                raise ValueError(f"Chave inválida: '{key}' (somente 'key' e 'side' são permitidas)")
            if not value:
                raise ValueError(f"Valor vazio para a chave: '{key}'")

            data[key] = value

        if "key" not in data or "side" not in data:
            raise ValueError("As chaves 'key' e 'side' são obrigatórias")

        if data["side"].lower() not in ["buy", "sell"]:
            raise ValueError("O valor de 'side' deve ser 'buy' ou 'sell'")

        # Normaliza o valor de 'side' para minúsculo
        data["side"] = data["side"].lower()
        return data

    except Exception as e:
        raise ValueError(f"Erro ao analisar os dados: {e}")

def send_to_celery(data: dict):
    """Envia dados para o Celery processar."""
    try:
        celery_app.send_task("process_webhook", kwargs={"data": data}, queue="webhook")
        general_logger.info("Task sent to Celery for key ending with: ...%s", data['key'][-4:] if len(data['key']) > 4 else data['key'])
    except Exception as e:
        general_logger.error("Erro ao enviar task ao Celery: %s", e)
        raise RuntimeError("Falha ao enviar para processamento assíncrono.")


# === Rota principal ===
@app.route('/webhook', methods=['POST'])
def webhook_listener():
    try:
        raw_body = request.get_data(as_text=True).strip()
        if not raw_body:
            general_logger.warning("Corpo da requisição vazio.")
            return jsonify({"error": "Corpo da requisição está vazio"}), 400

        try:
            parsed_data = parse_data(raw_body)
        except ValueError as e:
            general_logger.warning("Falha na validação dos dados: %s", e)
            return jsonify({"error": str(e)}), 400
        send_to_celery(parsed_data)
        return jsonify({"message": "Dados recebidos e enviados para processamento"}), 200

    except Exception as e:
        general_logger.exception("Erro inesperado no processamento do webhook")
        return jsonify({"error": "Erro interno no servidor"}), 500
    
if __name__ == '__main__':
    general_logger.info('Iniciando webhook')
    # Debug mode should be controlled by environment variables like FLASK_DEBUG or FLASK_ENV.
    # By default, Flask runs with debug=False unless FLASK_DEBUG=1.
    # Explicitly setting debug=False if FLASK_ENV is 'production' is a good safeguard.
    # However, relying on Flask's default behavior when not in development is often sufficient.
    # For clarity, we can fetch an environment variable.
    DEBUG_MODE = os.getenv('FLASK_DEBUG', '0') == '1' # FLASK_DEBUG=1 enables debug
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)
