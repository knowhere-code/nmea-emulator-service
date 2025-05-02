import logging
import sys

# Создаем логгер
logger = logging.getLogger('nmea_server')
logger.setLevel(logging.DEBUG)  # Минимальный уровень для обработки

# Форматтер для сообщений
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 1. Хендлер для записи в ФАЙЛ (только WARNING и выше)
file_handler = logging.FileHandler('nmeasrv.log')
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