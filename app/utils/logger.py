import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "bot") -> logging.Logger:
    """
    Настройка логгера без дублирования.
    ✅ Очищает старые хендлеры
    ✅ propagate = False
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 🔐 ОЧИЩАЕМ СТАРЫЕ ХЕНДЛЕРЫ (чтобы не было дублей при релоаде)
    logger.handlers.clear()
    
    # 🔐 ЗАПРЕЩАЕМ ПЕРЕДАЧУ КОРНЕВОМУ ЛОГГЕРУ
    logger.propagate = False

    # Формат с цветами для консоли
    class ColoredFormatter(logging.Formatter):
        """Цветной форматтер для консоли"""

        grey = "\x1b[38;21m"
        blue = "\x1b[34;21m"
        yellow = "\x1b[33;21m"
        red = "\x1b[31;21m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format_str + reset,
            logging.INFO: blue + format_str + reset,
            logging.WARNING: yellow + format_str + reset,
            logging.ERROR: red + format_str + reset,
            logging.CRITICAL: bold_red + format_str + reset,
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            formatter._style._fmt = log_fmt
            return formatter.format(record)

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())

    # Ротация логов: максимум 5 файлов по 5 MB (итого 25 MB)
    file_handler = RotatingFileHandler(
        "bot.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Добавляем хендлеры
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Глобальный логгер
logger = setup_logger()
