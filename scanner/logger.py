import logging
import os

def setup_logger(name='web_scanner', log_file='logs/scanner.log'):
    """Логгер"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Обработчик для файла
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Обработчик для консоли
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Формат ввода
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Добавляем обработчик
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger