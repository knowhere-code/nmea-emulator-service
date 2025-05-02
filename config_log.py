import logging
import sys
from logging.handlers import RotatingFileHandler

# Создаем логгер
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Минимальный уровень для обработки


# Форматтер для сообщений
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 1. Хендлер для записи в ФАЙЛ (только INFO и выше)
file_handler = handler = RotatingFileHandler(
    'nmeasrv.log',
    maxBytes=5*1024*1024,
    backupCount=3,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)


# 2. Хендлер для вывода в КОНСОЛЬ (DEBUG и выше)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Добавляем оба хендлера в логгер
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Пример использования
# logger.debug('Отладочное сообщение (только в консоль)')
# logger.info('Информационное сообщение (в консоль и файл)')
# logger.warning('Предупреждение (в консоль и файл)')
# logger.error('Ошибка (в консоль и файл)')