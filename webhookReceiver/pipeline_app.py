import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from celeryManager.celery_app import celery as celery_app
from log.log import general_logger

# Carrega variáveis de ambiente
load_dotenv(".env.prd")

# --- App Flask ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 # Limite de 16KB para o corpo da requisição

# === Funções de Utilidade (Validação) ===
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
        
        # 2. Envia a tarefa para o Celery
        try:
            # CORREÇÃO: Envia para a task 'webhook.receipt'
            celery_app.send_task(
                "webhook.receipt", 
                kwargs={"data": parsed_data}
            )
            general_logger.info(
                "Sinal recebido e enfileirado para key: ...%s", 
                parsed_data['key'][-4:]
            )
        except Exception as e:
            general_logger.error("Erro ao enfileirar task no Celery: %s", e, exc_info=True)
            raise RuntimeError("Falha ao enfileirar para processamento assíncrono.")

        return jsonify({"message": "Sinal recebido e enfileirado para processamento"}), 202 # 202 Accepted é mais apropriado aqui

    except Exception as e:
        general_logger.exception("Erro inesperado no endpoint do webhook")
        return jsonify({"error": "Erro interno no servidor"}), 500

if __name__ == '__main__':
    general_logger.info('Iniciando listener de Webhook do Flask')
    # O modo debug é controlado pela variável de ambiente FLASK_DEBUG
    DEBUG_MODE = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)