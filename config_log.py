import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

def setup_logger(log_file='nmeasrv.log'):
    """Настройка логгера с трейсом, но без строк кода."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    # Очистка старых обработчиков
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Форматтер (дата + уровень + сообщение)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Файловый хендлер (INFO+)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 2. Консольный хендлер (DEBUG+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Пример использования
# logger.debug('Отладочное сообщение (только в консоль)')
# logger.info('Информационное сообщение (в консоль и файл)')
# logger.warning('Предупреждение (в консоль и файл)')
# logger.error('Ошибка (в консоль и файл)', exc_info=True)