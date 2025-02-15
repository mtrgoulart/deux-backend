#from view.webapp import app  # Importe a aplicação Flask definida no webapp.py
from view import create_app
from log.log import general_logger
import os

app=create_app()

if __name__ == "__main__":
    general_logger.info("Iniciando aplicação Flask a partir de main.py.")
    app.run(host='0.0.0.0',port=5001)
