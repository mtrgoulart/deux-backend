# logger_config.py
import logging
import os

# Configura o logger
def setup_logger(name="general_logger", log_file="log.log", level=logging.INFO):
    """Configura o logger para gravar logs em um arquivo e no console."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Formato dos logs
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Configuração do handler para arquivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Configuração do handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Adiciona os handlers ao logger
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Cria um logger global que será usado por todos os scripts
general_logger = setup_logger()
