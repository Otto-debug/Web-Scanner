import logging

def setup_logger():
    """Логгер"""
    logger = logging.getLogger('web_scanner')
    logger.setLevel(logging.INFO)

    # Обработчик для файла
    file_handler = logging.FileHandler('logs/scanner.log')
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