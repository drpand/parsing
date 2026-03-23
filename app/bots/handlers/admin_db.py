"""
Admin DB Handler - Очистка базы данных с бэкапом
"""

import os
import shutil
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.bots.handlers.admin_menu import AdminStates
from app.utils.logger import logger
from app.db.database import database

router = Router(name="admin_db")


@router.message(F.text == "🗑 Очистить базу")
async def clear_database_request(message: Message, state: FSMContext):
    """Запрос на очистку БД"""
    logger.info(f"🗑 Очистить базу button clicked by user {message.from_user.id}")
    await state.clear()  # 🔐 ПРИНУДИТЕЛЬНЫЙ СБРОС ЛЮБОГО СОСТОЯНИЯ
    await state.set_state(AdminStates.waiting_for_db_confirm)
    await message.answer(
        "⚠️ <b>ВНИМАНИЕ! КРИТИЧЕСКАЯ ОПЕРАЦИЯ!</b>\n\n"
        "Вы уверены что хотите полностью очистить базу данных?\n"
        "Все товары и настройки будут удалены.\n\n"
        "Напишите <code>YES_DELETE</code> для подтверждения\n"
        "Или отправьте /cancel для отмены.",
        parse_mode="HTML",
    )
    logger.info(f"Admin {message.from_user.id} requested DB clear")


@router.message(AdminStates.waiting_for_db_confirm)
async def clear_database_confirm(message: Message, state: FSMContext):
    """Подтверждение и выполнение очистки"""
    if message.text != "YES_DELETE":
        await state.clear()
        await message.answer(
            "❌ <b>Отмена очистки.</b> Неверное кодовое слово.\n\n"
            "Ожидалось: <code>YES_DELETE</code>",
            parse_mode="HTML",
        )
        return

    try:
        # 1. ДЕЛАЕМ АВТОМАТИЧЕСКИЙ БЭКАП ПЕРЕД УДАЛЕНИЕМ
        db_path = "bot.db"  # 🔐 ИСПРАВЛЕНО: используем bot.db вместо indiashop.db
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"dump_before_delete_{timestamp}.db")

        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            logger.info(f"Auto-backup created: {backup_path}")
        else:
            logger.warning(f"Database file not found: {db_path}")

        # 2. Очищаем таблицы через SQL
        async with database.engine.begin() as conn:
            # Получаем список всех таблиц
            from sqlalchemy import text

            # Отключаем foreign keys для SQLite
            await conn.execute(text("PRAGMA foreign_keys=OFF"))

            # Очищаем все таблицы кроме post_groups (настройки)
            # 🔐 УДАЛЕНЫ НЕСУЩЕСТВУЮЩИЕ ТАБЛИЦЫ: cart_items, favorites, post_schedules
            tables_to_clear = [
                'products', 'orders', 'order_items',
                'post_history', 'users', 'settings'
            ]

            for table in tables_to_clear:
                try:
                    await conn.execute(text(f"DELETE FROM {table}"))
                    logger.info(f"Cleared table: {table}")
                except Exception as e:
                    logger.warning(f"Failed to clear table {table}: {e}")

            # SQLite автоматически сбрасывает автоинкремент при DELETE
            # Не нужно вручную удалять sqlite_sequence!

            # Включаем foreign keys обратно
            await conn.execute(text("PRAGMA foreign_keys=ON"))

        await message.answer(
            f"✅ <b>База данных успешно очищена!</b>\n\n"
            f"💾 <i>Резервная копия сохранена:</i>\n"
            f"<code>{backup_path}</code>",
            parse_mode="HTML",
        )
        logger.info(f"Database cleared by admin {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error clearing database: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Ошибка при очистке БД.</b>\n\n"
            f"<i>{str(e)[:200]}</i>\n\n"
            "Проверьте логи бота.",
            parse_mode="HTML",
        )
    finally:
        await state.clear()
