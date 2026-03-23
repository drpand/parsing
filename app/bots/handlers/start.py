from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.bots.keyboards.main import get_main_keyboard
from app.utils.logger import logger
from app.core.version import get_full_version, get_version_info
from app.core.config import settings
from sqlalchemy import select
from app.db.database import database
from app.db.models import Product
from app.bots.handlers.admin_settings import get_setting_value
from datetime import timedelta
import json

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Главное меню + обработка deep link от клиента"""
    logger.info(f"User {message.from_user.id} started the bot: text='{message.text}'")

    # 🔐 ПРОВЕРЯЕМ НА DEEP LINK (order_35) — 🔐 ОТКЛЮЧЕНО ДЛЯ КЛИЕНТОВ
    # Клиентская часть в разработке — показываем главное меню
    # args = message.text.split() if message.text else []
    # if len(args) >= 2 and args[1].startswith('order_'):
    #     logger.info(f"🔐 Deep link detected: {args[1]}")
    #     from app.bots.handlers.manager import handle_order_deep_link
    #     await handle_order_deep_link(message, args[1])
    #     return

    # 🔐 ПРОВЕРЯЕМ: МЕНЕДЖЕР ЛИ ЭТО?
    from app.db.database import database
    from app.db.repositories import ManagerRepository
    from app.bots.keyboards.main import get_manager_keyboard

    is_manager = False
    async with database.get_session() as session:
        repo = ManagerRepository(session)
        managers = await repo.get_all_active()
        is_manager = any(m.telegram_id == str(message.from_user.id) for m in managers)

    # Показываем меню в зависимости от роли
    if is_manager:
        await message.answer(
            "🏠 <b>Меню менеджера</b>\n\n"
            "Выберите раздел:",
            reply_markup=get_manager_keyboard(),
            parse_mode="HTML",
        )
        logger.info(f"Manager {message.from_user.id} opened manager menu")
    else:
        # Обычный /start — показываем меню
        await message.answer(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите раздел:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )


@router.message(Command("version"))
async def cmd_version(message: Message):
    """Показать версию бота"""
    version = get_full_version()
    info = get_version_info()

    await message.answer(
        f"📦 <b>Версия бота</b>\n\n"
        f"🔖 Версия: <b>{version}</b>\n"
        f"📅 Дата сборки: {info['build_date']}\n"
        f"📊 Статус: <i>{info['status']}</i>",
        parse_mode="HTML",
    )


@router.message(Command("product"))
async def cmd_product(message: Message):
    """
    🔐 Команда для менеджера: /product <ID>
    Показывает товар по ID
    """
    # Проверяем что это админ
    if message.from_user.id not in settings.admin_ids:
        await message.answer("❌ Доступ запрещён")
        return

    # Получаем ID товара из команды
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ <b>Использование:</b>\n\n"
            "<code>/product 123</code>\n\n"
            "Где 123 — ID товара",
            parse_mode="HTML"
        )
        return

    try:
        product_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return

    # Ищем товар в БД
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()

    if not product:
        await message.answer(f"❌ Товар #{product_id} не найден")
        return

    # 🔐 ПОЛУЧАЕМ КУРСЫ ИЗ БД
    usd_inr = await get_setting_value("usd_inr", 91.0)
    usd_rub = await get_setting_value("usd_rub", 80.0)

    # 🔐 РАСЧЁТ ЦЕНЫ: INR → USD → RUB
    price_usd = product.price_inr / usd_inr
    price_rub = int(price_usd * usd_rub)

    # Формируем карточку
    text = f"🛍 <b>{product.title[:100]}</b>\n\n"

    if product.original_price_inr and product.discount_percent > 0:
        text += f"🔥 <b>СКИДКА {int(product.discount_percent)}%</b>\n"
        text += f"<s>₹{product.original_price_inr:,.0f}</s> → <b>₹{product.price_inr:,.0f}</b>\n"
        text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"
    else:
        text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"

    text += f"{'✅' if product.in_stock else '❌'} В наличии\n\n"

    if product.is_active:
        if product.last_posted_at:
            local_time = product.last_posted_at + timedelta(hours=5, minutes=30)
            date_str = local_time.strftime("%d.%m.%Y %H:%M")
            text += f"📊 <b>Опубликован:</b> {date_str} (IST)\n\n"
        else:
            text += f"📊 <b>Опубликован:</b> Дата не указана\n\n"
    else:
        text += f"📊 <b>Не опубликован</b>\n\n"

    if product.images:
        images = json.loads(product.images) if isinstance(product.images, str) else product.images
        if images:
            text += f"🖼 <a href='{images[0]}'>Фото</a>\n\n"

    if product.source_url:
        text += f"🔗 <a href='{product.source_url}'>Оригинал</a>\n\n"

    text += f"<b>🆔 ID:</b> <code>{product.id}</code>"

    # Кнопки
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back")
    )

    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(F.text == "👋 Привет")
async def say_hello(message: Message):
    """Приветствие"""
    version = get_full_version()
    await message.answer(
        f"👋 <b>Привет!</b>\n\n"
        f"Я бот IndiaShop <b>{version}</b>.\n"
        f"Сейчас я нахожусь в разработке, но скоро смогу помочь вам с покупками!",
        parse_mode="HTML",
    )
    logger.info(f"User {message.from_user.id} said hello")


@router.message(F.text == "📞 Помощь")
async def show_help(message: Message):
    """Помощь"""
    version = get_full_version()
    await message.answer(
        f"📞 <b>Помощь</b>\n\n"
        f"Я бот IndiaShop <b>{version}</b>.\n\n"
        "🛠 <b>Текущий статус:</b>\n"
        "Бот находится в активной разработке.\n"
        "Пользовательский функционал будет доступен в следующей версии.\n\n"
        "📋 <b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/admin - Админ-панель (для администраторов)\n"
        f"/version - Версия бота ({version})",
        parse_mode="HTML",
    )
    logger.info(f"User {message.from_user.id} requested help")


@router.message(F.text == "🔙 В главное меню")
async def back_to_main(message: Message, state: FSMContext):
    """Возврат в главное меню (универсальный)"""
    await state.clear()  # 🔐 ПРИНУДИТЕЛЬНЫЙ СБРОС ЛЮБОГО СОСТОЯНИЯ
    from app.bots.keyboards.main import get_main_keyboard

    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User {message.from_user.id} returned to main menu")


# ===== 🔐 ОБРАБОТЧИКИ МЕНЕДЖЕРА =====
# 🔐 УДАЛЕНО: manager_products — теперь используется admin_products_text с проверкой прав

@router.message(F.text == "🔍 Поиск по ID")
async def manager_search_by_id(message: Message):
    """🔍 Менеджер: Поиск товара по ID"""
    from app.bots.keyboards.main import get_manager_keyboard

    await message.answer(
        "🔍 <b>Поиск товара по ID</b>\n\n"
        "Отправьте ID товара (число) или используйте команду:\n"
        "<code>/find 123</code>\n\n"
        "Где 123 — ID товара",
        parse_mode="HTML",
        reply_markup=get_manager_keyboard()
    )
