"""
IndiaShop Reseller Bot v3.5
© 2026 All Rights Reserved.

Proprietary and Confidential.
Unauthorized use, copying, or distribution is prohibited.

For licensing inquiries: @tatastu
"""

import asyncio
import logging
import os  # 🔐 Для отладки .env
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError

from app.core.config import settings
from app.bots.dispatcher import create_dispatcher, on_startup, on_shutdown
from app.services.selenium_service import selenium_stealth_service
from app.utils.logger import logger
from app.core.process_manager import kill_previous_instance, save_current_pid, cleanup_pid_file
from app.core.version import get_full_version


# 🔐 ПРИГЛУШЕНИЕ ЛОГОВ: urllib3 и Selenium слишком болтливы при очистке
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.ERROR)


async def main():
    """Основной цикл бота"""
    # 🔐 1. УБИВАЕМ СТАРЫЙ ПРОЦЕСС (если был запущен)
    kill_previous_instance()

    # 🔐 2. ЗАПИСЫВАЕМ НОВЫЙ PID
    save_current_pid()
    
    # 🔐 DEBUG: Проверка загрузки .env
    print(f"DEBUG ENV: OPENROUTER_MODEL = {os.getenv('OPENROUTER_MODEL')}")
    print(f"DEBUG ENV: settings.openrouter_model = {settings.openrouter_model}")

    # 🔐 ВЕРСИЯ БОТА
    from app.core.version import get_full_version
    version = get_full_version()

    logger.info("=" * 50)
    logger.info(f"INDIASHOP BOT {version}")
    logger.info("=" * 50)

    # Инициализация сервисов
    logger.info("Initializing services...")

    # Bot
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 🔐 POSTER SERVICE: Создаётся в on_startup (после инициализации БД!)
    from app.services.poster_service import PosterService
    # Не создаём здесь, создадим в on_startup

    # Selenium Stealth Service
    selenium_stealth_service.start()

    # Dispatcher
    dp = create_dispatcher()

    # Регистрируем он стартап/шандаун
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск
    logger.info("Starting polling...")

    try:
        await dp.start_polling(bot)
    except TelegramNetworkError as e:
        logger.error(f"Telegram error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        await bot.session.close()
        selenium_stealth_service.stop()
        logger.info("Bot stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
