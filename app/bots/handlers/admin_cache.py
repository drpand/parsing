"""
Admin Cache Handler — Управление кэшем парсинга
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from app.core.config import settings
from app.utils.logger import logger
import sqlite3
import os

router = Router(name="admin_cache")


@router.message(F.text == "💾 Кэш")
async def cmd_cache_menu(message: Message, state: FSMContext):
    """
    🔐 Меню управления кэшем парсинга
    """
    logger.info(f"💾 Кэш button clicked by user {message.from_user.id}")
    await state.clear()  # 🔐 СБРОС СОСТОЯНИЯ

    if message.from_user.id not in settings.admin_ids:
        await message.answer("🚫 <b>Доступ запрещён</b>", parse_mode="HTML")
        return

    DB_PATH = "bot_cache.db"

    if not os.path.exists(DB_PATH):
        await message.answer(
            "🗑 <b>Кэш пуст</b>\n\n"
            "Кэш ещё не создавался.\n\n"
            "<i>Кэш автоматически создаётся при парсинге товаров и хранится 24 часа.</i>",
            parse_mode="HTML"
        )
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM product_cache")
    count = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM product_cache")
    row = cursor.fetchone()

    conn.close()

    text = f"🗃 <b>Кэш парсинга</b>\n\n"
    text += f"📊 Записей: <b>{count}</b>\n"
    if row[0]:
        text += f"📅 Первый кэш: <code>{row[0]}</code>\n"
    if row[1]:
        text += f"📅 Последний кэш: <code>{row[1]}</code>\n"
    text += f"⏳ Срок жизни: 24 часа\n\n"
    text += f"<i>Кэш ускоряет повторный парсинг тех же товаров и экономит API запросы.</i>"

    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Очистить кэш", callback_data="cache_clear")
    builder.button(text="❌ Отмена", callback_data="admin_back")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    logger.info(f"Admin {message.from_user.id} opened cache menu")


@router.callback_query(F.data == "cache_clear")
async def cache_clear_confirm(callback: CallbackQuery):
    """Подтверждение очистки кэша"""
    conn = sqlite3.connect("bot_cache.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM product_cache")
    count = cursor.rowcount
    conn.commit()
    conn.close()

    await callback.answer(f"✅ Удалено записей: {count}", show_alert=True)

    # Обновляем отображение
    await cmd_cache_menu(callback.message)
