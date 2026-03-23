"""
Process Cleaner - Принудительная очистка процессов ChromeDriver
© 2026 All Rights Reserved.

Используется для очистки зависших процессов chromedriver.exe после остановки бота.
"""

import subprocess
import psutil
from app.utils.logger import logger


def kill_chromedriver_processes():
    """
    🔐 ПРИНУДИТЕЛЬНАЯ ОЧИСТКА: Убивает все процессы chromedriver.exe
    """
    killed_count = 0
    
    try:
        # 🔐 СПОСОБ 1: Через taskkill (Windows)
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'chromedriver.exe'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Подсчитаем сколько убито
            killed_count = result.stdout.count('SUCCESS')
            logger.info(f"✅ Убито процессов chromedriver (taskkill): {killed_count}")
        else:
            # Если процессов нет - это нормально
            if 'not found' in result.stdout or 'not found' in result.stderr:
                logger.info("ℹ️ Процессы chromedriver не найдены (это нормально)")
            else:
                logger.warning(f"⚠️ taskkill вернул ошибку: {result.stderr}")
                
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при очистке через taskkill: {e}")
    
    # 🔐 СПОСОБ 2: Через psutil (дополнительная проверка)
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'chromedriver' in proc.info['name'].lower():
                    proc.kill()
                    killed_count += 1
                    logger.info(f"✅ Убит процесс chromedriver (psutil): PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при очистке через psutil: {e}")
    
    if killed_count > 0:
        logger.info(f"🎯 ИТОГО: Убито процессов chromedriver: {killed_count}")
    else:
        logger.info("✅ Зависших процессов chromedriver не обнаружено")
    
    return killed_count


def kill_chrome_processes():
    """
    ⚠️ ОСТОРОЖНО: Убивает ВСЕ процессы Chrome (включая пользовательские)
    Используйте только в крайних случаях!
    """
    killed_count = 0
    
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'chrome.exe'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            killed_count = result.stdout.count('SUCCESS')
            logger.warning(f"⚠️ Убито процессов Chrome: {killed_count}")
        else:
            if 'not found' in result.stdout or 'not found' in result.stderr:
                logger.info("ℹ️ Процессы Chrome не найдены")
            else:
                logger.warning(f"⚠️ taskkill вернул ошибку: {result.stderr}")
                
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при очистке Chrome: {e}")
    
    return killed_count


def cleanup_all_browser_processes():
    """
    🔐 ПОЛНАЯ ОЧИСТКА: Chrome + ChromeDriver
    """
    logger.info("🧹 Запуск полной очистки процессов браузера...")
    
    cd_killed = kill_chromedriver_processes()
    chrome_killed = kill_chrome_processes()
    
    total = cd_killed + chrome_killed
    logger.info(f"✅ Очистка завершена. Всего убито процессов: {total}")
    
    return total


if __name__ == "__main__":
    # Ручной запуск для очистки
    print("🧹 Очистка процессов ChromeDriver...")
    killed = kill_chromedriver_processes()
    print(f"✅ Убито процессов: {killed}")
