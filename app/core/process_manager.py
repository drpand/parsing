"""
Process Manager - Управление процессами бота
🔐 Кроссплатформенное решение (Windows + Linux)
"""

import os
import signal
import time
from app.utils.logger import logger

PID_FILE = "bot.pid"


def kill_previous_instance():
    """
    🔐 УБИВАЕМ старый процесс бота (если был запущен)
    
    Читает PID файл и отправляет SIGTERM старому процессу.
    Работает на Windows и Linux.
    """
    if not os.path.exists(PID_FILE):
        logger.info("ℹ️ PID файл не найден — первый запуск")
        return

    try:
        with open(PID_FILE, 'r') as f:
            pid_str = f.read().strip()
            if not pid_str.isdigit():
                logger.warning(f"⚠️ Некорректный PID в файле: {pid_str}")
                return
            old_pid = int(pid_str)

        current_pid = os.getpid()
        if old_pid == current_pid:
            logger.info(f"ℹ️ PID совпадает с текущим — это тот же процесс")
            return

        logger.info(f"🔄 Найден старый процесс (PID: {old_pid}). Отправка SIGTERM...")
        
        # 🔐 Кроссплатформенное убийство процесса
        # Windows: os.kill() с SIGTERM работает в Python 3.7+
        # Linux: стандартный POSIX сигнал
        try:
            os.kill(old_pid, signal.SIGTERM)
            logger.info(f"✅ SIGTERM отправлен процессу {old_pid}")
            
            # Ждём graceful shutdown (2 секунды на закрытие БД и сессий)
            time.sleep(2)
            
            # Проверяем что процесс действительно умер
            try:
                os.kill(old_pid, 0)  # Сигнал 0 проверяет существование
                logger.warning(f"⚠️ Процесс {old_pid} всё ещё жив, пробуем ещё раз...")
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(1)
            except OSError:
                logger.info(f"✅ Процесс {old_pid} успешно завершён")
                
        except ProcessLookupError:
            logger.info(f"ℹ️ Процесс {old_pid} уже завершён (ProcessLookupError)")
        except OSError as e:
            # На Windows может быть OSError вместо ProcessLookupError
            logger.debug(f"ℹ️ Старый процесс недоступен: {e}")

    except FileNotFoundError:
        logger.debug("ℹ️ PID файл не найден (уже удалён)")
    except PermissionError as e:
        logger.error(f"❌ Нет прав на завершение процесса {old_pid}: {e}")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось завершить старый процесс: {e}")


def save_current_pid():
    """
    ✅ СОХРАНЯЕМ текущий PID в файл
    
    Позволяет следующему экземпляру бота найти и завершить этот процесс.
    """
    try:
        current_pid = os.getpid()
        
        with open(PID_FILE, 'w') as f:
            f.write(str(current_pid))
        
        logger.info(f"✅ Текущий процесс (PID: {current_pid}) записан в {PID_FILE}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка записи PID файла: {e}")


def cleanup_pid_file():
    """
    🧹 Удаляем PID файл при корректном завершении
    
    Вызывать в on_shutdown() диспетчера.
    """
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info(f"🧹 PID файл {PID_FILE} удалён")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить PID файл: {e}")


def get_current_pid() -> int:
    """Получить текущий PID"""
    return os.getpid()


def get_stored_pid() -> int | None:
    """Получить PID из файла (если существует)"""
    if not os.path.exists(PID_FILE):
        return None
    
    try:
        with open(PID_FILE, 'r') as f:
            pid_str = f.read().strip()
            if pid_str.isdigit():
                return int(pid_str)
    except Exception:
        pass
    
    return None
