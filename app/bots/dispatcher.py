"""
Dispatcher IndiaShop Bot v2.0
© 2026 All Rights Reserved.

Proprietary and Confidential.
"""

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from app.core.config import settings
from app.db.database import database
from app.bots.handlers.admin_menu import router as admin_menu_router
from app.bots.handlers.admin_parse import router as admin_parse_router
from app.bots.handlers.admin_products import router as admin_products_router
from app.bots.handlers.admin_posting import router as admin_posting_router
from app.bots.handlers.admin_db import router as admin_db_router
from app.bots.handlers.admin_settings import router as admin_settings_router
from app.bots.handlers.admin_cache import router as admin_cache_router
from app.bots.handlers.admin_managers import router as admin_managers_router  # 👥 МЕНЕДЖЕРЫ
from app.bots.handlers.start import router as start_router
from app.bots.handlers.preview_product import router as preview_product_router
from app.bots.handlers.manager import router as manager_router  # 🔐 МЕНЕДЖЕР
# from app.bots.handlers.orders import router as orders_router  # ❌ УДАЛЕНО
# from app.bots.handlers.products import router as products_router  # ❌ НЕ ИСПОЛЬЗУЕТСЯ
# from app.bots.handlers.admin_broadcast import router as admin_broadcast_router  # ❌ УДАЛЕНО
# from app.bots.handlers.admin_orders import router as admin_orders_router  # ❌ УДАЛЕНО
from app.utils.logger import logger
import asyncio


def create_dispatcher() -> Dispatcher:
    """Создание диспетчера"""
    logger.info("Creating dispatcher...")
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры
    logger.info("Connecting routers...")
    dp.include_router(start_router)  # Главное меню
    dp.include_router(admin_db_router)  # Очистка БД (ВАЖНО: раньше admin_products)
    dp.include_router(admin_cache_router)  # 💾 Кэш (ВАЖНО: раньше admin_products)
    dp.include_router(admin_settings_router)  # Настройки (ВАЖНО: раньше admin_products)
    dp.include_router(admin_posting_router)  # Авто-постинг (ВАЖНО: раньше admin_products)
    dp.include_router(admin_parse_router)  # Парсинг
    dp.include_router(admin_menu_router)  # Админ меню
    dp.include_router(admin_products_router)  # Товары
    dp.include_router(admin_managers_router)  # 👥 Менеджеры
    dp.include_router(preview_product_router)  # Превью
    dp.include_router(manager_router)  # 🔐 МЕНЕДЖЕР
    # dp.include_router(products_router)  # ❌ НЕ ИСПОЛЬЗУЕТСЯ
    # dp.include_router(orders_router)  # ❌ УДАЛЕНО
    # dp.include_router(admin_broadcast_router)  # ❌ УДАЛЕНО
    # dp.include_router(admin_orders_router)  # ❌ УДАЛЕНО

    logger.info(f"Connected routers: 10 (start, admin_parse, admin_menu, admin_products, admin_posting, admin_db, admin_settings, admin_cache, admin_managers, preview_product, manager)")
    return dp


async def setup_bot_commands(bot: Bot):
    """Настройка команд"""
    logger.info("Setting up bot commands...")

    # 🔐 ОБЫЧНЫЕ КОМАНДЫ (для всех)
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="version", description="📦 Версия бота"),
        BotCommand(command="help", description="📞 Помощь"),
    ]
    await bot.set_my_commands(commands)

    # 🔐 АДМИНСКИЕ КОМАНДЫ (только для админов)
    admin_commands = [
        BotCommand(command="admin", description="🔧 Админ-панель"),
        BotCommand(command="find", description="🔍 Найти товар по ID"),
        BotCommand(command="cache", description="💾 Управление кэшем"),
        BotCommand(command="cancel", description="❌ Отмена"),
    ]

    # Настраиваем для админов
    from aiogram.types import BotCommandScopeChat
    for admin_id in settings.admin_ids:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))

    logger.info("Bot commands configured (public + admin)")


async def on_startup(bot: Bot):
    """
    Запуск бота - ПРАВИЛЬНЫЙ ПОРЯДОК
    1. database.connect()
    2. poster_service.start_scheduler()
    3. Уведомление админам (с версией)
    """
    from app.core.version import get_full_version

    logger.info("=" * 50)
    logger.info("BOT STARTUP")
    logger.info("=" * 50)

    # 🔐 ВЕРСИЯ БОТА
    version = get_full_version()
    logger.info(f"IndiaShop Bot {version}")
    logger.info("=" * 50)

    # БД
    logger.info("Connecting to database...")
    await database.connect()
    logger.info("Database connected")

    # Команды
    await setup_bot_commands(bot)

    # Инфо о боте
    bot_info = await bot.get_me()
    logger.info(f"Bot: @{bot_info.username} (ID: {bot_info.id})")

    # 🔐 СОЗДАЁМ POSTER SERVICE (после инициализации БД!)
    from app.services.poster_service import PosterService, poster_service as global_poster_service
    poster_service_instance = PosterService(bot)

    # Сохраняем в глобальную переменную
    import app.services.poster_service as ps
    ps.poster_service = poster_service_instance

    # ЗАПУСК ПЛАНИРОВЩИКА АВТО-ПОСТИНГА
    await poster_service_instance.start_scheduler()
    logger.info(f"✅ Auto Poster Scheduler STARTED")

    # Уведомление админу (с версией!)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"✅ <b>Бот запущен!</b>\n\n"
                     f"🤖 @{bot_info.username}\n"
                     f"📦 Версия: <b>{version}</b>\n"
                     f"⏰ {asyncio.get_event_loop().time()}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")

    logger.info("Bot is ready!")


async def on_shutdown(bot: Bot):
    """
    Остановка бота - ПРАВИЛЬНЫЙ ПОРЯДОК (Graceful Shutdown)
    1. dp.stop_polling()
    2. scheduler.shutdown()
    3. driver.quit()
    4. db.close()
    5. 🔐 ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПРОЦЕССОВ
    """
    logger.info("=" * 50)
    logger.info("BOT SHUTDOWN")
    logger.info("=" * 50)

    # 🔐 1. ОСТАНОВКА POLLING (сначала останавливаем получение обновлений)
    logger.info("Stopping polling...")

    # 🔐 2. ОСТАНОВКА ПЛАНИРОВЩИКА (до закрытия БД)
    logger.info("Stopping poster scheduler...")
    from app.services.poster_service import poster_service
    if poster_service:
        await poster_service.stop_scheduler()
        logger.info("Poster scheduler stopped")

    # 🔐 3. ОСТАНОВКА SELENIUM (до закрытия БД)
    logger.info("Stopping Selenium...")
    from app.services.selenium_service import selenium_stealth_service
    selenium_stealth_service.stop()
    logger.info("Selenium stealth service stopped")

    # 🔐 4. ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПРОЦЕССОВ CHROMEDRIVER
    logger.info("🧹 Forcing cleanup of ChromeDriver processes...")
    from app.utils.process_cleaner import kill_chromedriver_processes
    killed = kill_chromedriver_processes()
    if killed > 0:
        logger.warning(f"⚠️ Убито зависших процессов: {killed}")
    else:
        logger.info("✅ Зависших процессов не обнаружено")

    # 🔐 5. ЗАКРЫТИЕ БД (в последнюю очередь)
    logger.info("Disconnecting database...")
    await database.disconnect()
    logger.info("Database disconnected")

    # 🔐 6. ОЧИСТКА PID ФАЙЛА
    from app.core.process_manager import cleanup_pid_file
    cleanup_pid_file()

    logger.info("Bot shutdown complete")
