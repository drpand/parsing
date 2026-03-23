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
    manager_username = message.from_user.username

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        managers = await repo.get_all_active()

        # 🔐 ПРОВЕРКА 1: По telegram_id (если уже обновлён)
        is_manager = any(m.telegram_id == str(message.from_user.id) for m in managers)

        # 🔐 ПРОВЕРКА 2: По username (если telegram_id = temp_{username})
        if not is_manager and manager_username:
            for m in managers:
                if m.telegram_id.startswith("temp_") and m.telegram_id.replace("temp_", "") == manager_username:
                    # 🔐 НАЙДЕН МЕНЕДЖЕР ПО USERNAME — ОБНОВЛЯЕМ telegram_id
                    await repo.update(m.id, {"telegram_id": str(message.from_user.id)})
                    logger.info(f"✅ Manager @{manager_username} telegram_id updated: {m.telegram_id} → {message.from_user.id}")
                    is_manager = True
                    break

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


@router.callback_query(F.data.startswith("client_product_view:"))
async def client_view_product(callback: CallbackQuery):
    """🛍 Просмотр товара клиентом"""
    from sqlalchemy import select
    from app.db.models import Product
    import json
    
    product_id = int(callback.data.split(":")[1])
    logger.info(f"Client {callback.from_user.id} viewing product: {product_id}")
    
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Расчёт цены в RUB
    price_rub = int(product.price_inr * 0.9)
    
    text = f"🛍 <b>{product.title[:100]}</b>\n\n"
    text += f"💰 <b>Цена: {price_rub:,} ₽</b>\n\n"
    
    if product.in_stock:
        text += "✅ В наличии\n\n"
    else:
        text += "❌ Нет в наличии\n\n"
    
    # Фото
    if product.images:
        images = json.loads(product.images) if isinstance(product.images, str) else product.images
        if images and images[0].startswith('http'):
            text += f"🖼 <a href='{images[0]}'>Фото товара</a>\n\n"
    
    # Оригинал
    if product.source_url:
        text += f"🔗 <a href='{product.source_url}'>Оригинал</a>\n\n"
    
    text += f"🆔 <b>ID:</b> <code>{product.id}</code>\n\n"
    text += "💡 <i>Для заказа напишите менеджеру</i>"
    
    # Кнопки
    keyboard = InlineKeyboardBuilder()
    
    if product.images:
        images = json.loads(product.images) if isinstance(product.images, str) else product.images
        if images and images[0].startswith('http'):
            keyboard.button(text="🖼 Фото", url=images[0])
    
    if product.source_url:
        keyboard.button(text="🔗 Оригинал", url=product.source_url)
    
    keyboard.row()
    keyboard.button(text="📞 Связаться с менеджером", callback_data="client_contact_manager")
    keyboard.row()
    keyboard.button(text="🔙 В каталог", callback_data="client_catalog_back")
    
    try:
        await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending product to client: {e}")
        await callback.message.answer(text, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "client_catalog_back")
async def client_catalog_back(callback: CallbackQuery):
    """🔙 Возврат в каталог"""
    from sqlalchemy import select
    from app.db.models import Product
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    await callback.message.delete()
    
    async with database.get_session() as session:
        result = await session.execute(
            select(Product).where(Product.is_active == True).limit(20)
        )
        products = result.scalars().all()
    
    text = "🛍 <b>Каталог товаров</b>\n\n"
    text += f"Найдено товаров: {len(products)}\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    for product in products[:10]:
        price_rub = int(product.price_inr * 0.9)
        btn_text = f"💰 {product.title[:35]}... | {price_rub:,}₽"
        keyboard.button(
            text=btn_text,
            callback_data=f"client_product_view:{product.id}"
        )
    
    keyboard.adjust(1)
    keyboard.row()
    keyboard.button(text="🔙 В главное меню", callback_data="main_menu")
    
    await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "client_contact_manager")
async def client_contact_manager(callback: CallbackQuery):
    """📞 Связь с менеджером"""
    from sqlalchemy import select
    from app.db.models import Manager
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    async with database.get_session() as session:
        result = await session.execute(
            select(Manager).where(Manager.is_active == True)
        )
        managers = result.scalars().all()
    
    if not managers:
        await callback.answer("Нет активных менеджеров", show_alert=True)
        return
    
    text = "📞 <b>Наши менеджеры</b>\n\n"
    keyboard = InlineKeyboardBuilder()
    
    for manager in managers:
        username = manager.username.strip('@') if manager.username else None
        if username:
            keyboard.button(
                text=f"✉️ @{username}",
                url=f"https://t.me/{username}"
            )
    
    keyboard.adjust(2)
    keyboard.row()
    keyboard.button(text="🔙 Назад", callback_data="client_catalog_back")
    
    await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.message(F.text == "🛍 Каталог товаров")
async def show_catalog(message: Message):
    """🛍 Каталог товаров для клиента"""
    from sqlalchemy import select
    from app.db.models import Product
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    logger.info(f"User {message.from_user.id} opened catalog")
    
    # Получаем товары из БД (только опубликованные и активные)
    async with database.get_session() as session:
        result = await session.execute(
            select(Product).where(Product.is_active == True).limit(20)
        )
        products = result.scalars().all()
    
    if not products:
        await message.answer(
            "🛍 <b>Каталог товаров</b>\n\n"
            "В каталоге пока нет товаров.\n"
            "Загляните позже!",
            parse_mode="HTML"
        )
        return
    
    # Показываем первые 10 товаров
    text = f"🛍 <b>Каталог товаров</b>\n\n"
    text += f"Найдено товаров: {len(products)}\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    for product in products[:10]:
        price_rub = int(product.price_inr * 0.9)  # Примерный расчёт
        btn_text = f"💰 {product.title[:35]}... | {price_rub:,}₽"
        keyboard.button(
            text=btn_text,
            callback_data=f"client_product_view:{product.id}"
        )
    
    keyboard.adjust(1)
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@router.message(F.text == "📞 Связаться с менеджером")
async def contact_manager(message: Message):
    """📞 Связь с активными менеджерами"""
    from sqlalchemy import select
    from app.db.models import Manager
    
    logger.info(f"User {message.from_user.id} wants to contact manager")
    
    # Получаем активных менеджеров из БД
    async with database.get_session() as session:
        result = await session.execute(
            select(Manager).where(Manager.is_active == True)
        )
        managers = result.scalars().all()
    
    if not managers:
        await message.answer(
            "📞 <b>Связаться с менеджером</b>\n\n"
            "В данный момент нет активных менеджеров.\n"
            "Попробуйте позже или напишите в поддержку.",
            parse_mode="HTML"
        )
        return
    
    # Формируем список менеджеров
    text = "📞 <b>Наши менеджеры</b>\n\n"
    text += "Выберите менеджера для связи:\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    for manager in managers:
        username = manager.username.strip('@') if manager.username else None
        if username:
            text += f"👤 <b>{manager.first_name or 'Менеджер'}</b>\n"
            text += f"   @{username}\n\n"
            keyboard.button(
                text=f"✉️ Написать @{username}",
                url=f"https://t.me/{username}"
            )
    
    keyboard.adjust(1)
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    """ℹ️ Информация о боте"""
    version = get_full_version()
    info = get_version_info()
    
    await message.answer(
        f"ℹ️ <b>О боте IndiaShop</b>\n\n"
        f"📦 <b>Версия:</b> {version}\n"
        f"📅 <b>Дата сборки:</b> {info['build_date']}\n"
        f"📊 <b>Статус:</b> {info['status']}\n\n"
        f"🛍 <b>Возможности:</b>\n"
        f"• Просмотр каталога товаров\n"
        f"• Связь с менеджерами\n"
        f"• Оформление заказов (в разработке)\n\n"
        f"📞 <b>Поддержка:</b>\n"
        f"Нажмите '📞 Связаться с менеджером' для помощи.\n\n"
        f"{info['copyright']}",
        parse_mode="HTML",
    )
    logger.info(f"User {message.from_user.id} viewed 'About bot'")


@router.message(F.text == "👋 Привет")
async def say_hello(message: Message):
    """Приветствие (устарело, оставлено для совместимости)"""
    version = get_full_version()
    await message.answer(
        f"👋 <b>Привет!</b>\n\n"
        f"Я бот IndiaShop <b>{version}</b>.\n"
        f"Выберите раздел в меню:",
        parse_mode="HTML",
    )
    logger.info(f"User {message.from_user.id} said hello")


@router.message(F.text == "📞 Помощь")
async def show_help(message: Message):
    """Помощь (устарело, оставлено для совместимости)"""
    version = get_full_version()
    await message.answer(
        f"📞 <b>Помощь</b>\n\n"
        f"Я бот IndiaShop <b>{version}</b>.\n\n"
        f"📋 <b>Команды:</b>\n"
        f"/start - Главное меню\n"
        f"/version - Версия бота\n\n"
        f"Нажмите '📞 Связаться с менеджером' для помощи.",
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
