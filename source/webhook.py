from flask import Flask, request, jsonify
from .manager import OKX_interface
from .pp import Market, ConfigLoader,WebhookData
import json
from pyngrok import ngrok
import os
import signal
import threading
import requests
import time
import sys
import logging
import re
log = logging.getLogger('werkzeug')
log.disabled = True
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

class NgrokLinkGenerator:
    def __init__(self, port=5000):
        self.port = port

    def generate_link(self):
        public_url = ngrok.connect(self.port, bind_tls=True)
        formatted_url = f"{public_url}/webhookcallback"
        print(f"URL pública para webhook '{formatted_url}'")
        return formatted_url

    def stop_ngrok(self):
        ngrok.disconnect(self.port)
        ngrok.kill()

class WebhookHandler:
    def __init__(self, webhook_url):
        self.app = Flask(__name__)
        self.app.add_url_rule('/webhookcallback', view_func=self.hook, methods=['POST'])
        self.text_handler = TextHandler()
        self.server_thread = None
        self.stop_event = threading.Event()
        self.pp = ConfigLoader()
        self.webhook_data_manager = WebhookData()
        self.webhook_url = webhook_url

    def hook(self):
        text_data = request.data.decode('utf-8')

        #Check data
        if re.match(self.pp.get('pattern', 'webhook_str'), text_data):
            result = self.text_handler.process_text(text_data)
            if result['status'] == 'success':

                
                obj = result['object']
                required_fields = ['symbol', 'side', 'indicator']
                print(obj)

                if all(field in obj for field in required_fields):
                    
                    market_object = Market(
                        symbol=obj.get('symbol', None),
                        order_type=obj.get('order_type', None),
                        side=obj.get('side', None),
                        size=obj.get('size', None),
                        price=obj.get('price', None),
                        operation=obj.get('operation', None),
                        indicator=obj.get('indicator',None)
                    )

                    # Save formatted data
                    self.webhook_data_manager.add_data(result['data'])
                    self.webhook_data_manager.add_object(market_object)
                else:
                    return jsonify({"error": "Missing required fields in object"}), 400

            return jsonify({'mensagem':'sucesso?'}),200
        else:
            return jsonify({"error": "Invalid or missing data"}), 400

    def run(self, host='0.0.0.0', port=5000):
        def run_flask():
            self.app.run(host=host, port=port, use_reloader=False)

        self.server_thread = threading.Thread(target=run_flask)
        self.server_thread.start()

        print("\nURL pública para webhook:\n\n")
        print(self.webhook_url)
        print("\n\nColocar los siguientes parámetros en el webhook: \n\nsymbol=BTC-USDT, order_type=market, size=0.01, side=" + r'{{strategy.market_position}}')

    def stop(self):
        self.stop_event.set()
        if self.server_thread is not None:
            self.server_thread.join()

    def stop_in_thread(self):
        stop_thread = threading.Thread(target=self.stop)
        stop_thread.start()


class TextHandler:
    def model_text(self, text_data):
        # Supondo que os dados sejam uma string formatada
        data_pairs = text_data.split(',')
        data_dict = {}
        for pair in data_pairs:
            key, value = pair.split('=')
            data_dict[key.strip()] = value.strip()

        # Tentativa de conversão de tipos de dados automaticamente
        for key, value in data_dict.items():
            if value.isdigit():
                data_dict[key] = int(value)
            else:
                try:
                    data_dict[key] = float(value)
                except ValueError:
                    pass  # Mantém o valor como string se não for numérico

        return data_dict

    def process_text(self, text_data):
        try:
            dynamic_data = self.model_text(text_data)
            print(f'Processed data: {dynamic_data}')
        except Exception as e:
            print(f'Error on process_text: {e}')
            return {"status": "error", "message": str(e)}
        
        return {"status": "success", "data": text_data, "object": dynamic_data}


if __name__ == "__main__":
    handler = WebhookHandler()
    handler.run()
