import os
import logging

def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log_file_name = 'output/.logs/esida.log'
    os.makedirs(os.path.dirname(log_file_name), exist_ok=True)
    handler_file = logging.FileHandler(filename=log_file_name)
    handler_file.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if (logger.hasHandlers()):
        logger.handlers.clear()

    logger.addHandler(handler)
    logger.addHandler(handler_file)

    return logger
