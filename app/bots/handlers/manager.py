"""
Manager Handler — Уведомления менеджеру когда клиент пишет о товаре
© 2026 All Rights Reserved.

Proprietary and Confidential.
"""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, Command
from sqlalchemy import select
import re

from app.core.config import settings
from app.db.database import database
from app.db.models import Product, Manager, Setting
from app.db.repositories import ManagerRepository
from app.bots.handlers.admin_settings import get_setting_value
from app.utils.logger import logger
from datetime import timedelta
import random

router = Router(name="manager")


async def get_active_managers() -> list:
    """Получить список активных менеджеров из БД"""
    async with database.get_session() as session:
        repo = ManagerRepository(session)
        managers = await repo.get_all_active()
        return managers


async def get_manager_for_notification() -> str:
    """
    Получить username менеджера для уведомления.
    Если есть менеджеры в БД — выбираем случайного.
    Если нет — берём из настроек (старый формат).
    """
    managers = await get_active_managers()

    if managers:
        # Выбираем случайного менеджера (балансировка нагрузки)
        selected = random.choice(managers)
        return selected.username

    # Фоллбэк на старый формат из настроек
    async with database.get_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "manager_username"))
        setting = result.scalar()
        manager_username = setting.value if setting else "tatastu"
        return manager_username.lstrip('@')


@router.message(Command("find"))
async def cmd_find_product(message: Message):
    """
    🔐 Команда для менеджера: /find <ID>
    Показывает товар по ID
    """
    # Проверяем что это менеджер (через БД)
    if not message.from_user.username:
        return

    # Проверяем есть ли пользователь в менеджерах
    managers = await get_active_managers()
    is_manager = any(m.telegram_id == str(message.from_user.id) for m in managers)

    # Если нет в БД, проверяем старый формат (username из настроек)
    if not is_manager:
        async with database.get_session() as session:
            result = await session.execute(select(Setting).where(Setting.key == "manager_username"))
            setting = result.scalar()
            manager_username = setting.value if setting else "tatastu"
            manager_usernames = [m.strip().lstrip('@') for m in manager_username.split(',')]
            is_manager = message.from_user.username.lower() in [m.lower() for m in manager_usernames]

    if not is_manager:
        await message.answer("❌ Доступ запрещён")
        return

    # Получаем ID из команды
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ <b>Использование:</b>\n\n"
            "<code>/find 123</code>\n\n"
            "Где 123 — ID товара",
            parse_mode="HTML"
        )
        return

    try:
        product_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return

    await send_product_card(message, product_id)


async def handle_order_deep_link(message: Message, deep_link: str):
    """
    🔐 Обработка deep link order_{product_id}
    Вызывается из start.py при обнаружении deep link
    """
    # Извлекаем product_id
    product_id = int(deep_link.replace("order_", ""))
    logger.info(f"🔐 Handling order deep link: product_id={product_id}, user={message.from_user.id}")

    # 🔐 ПОЛУЧАЕМ ТОВАР ИЗ БД
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()

    if not product:
        await message.answer("❌ Товар не найден")
        return

    # 🔐 ПОЛУЧАЕМ КУРСЫ
    usd_inr = await get_setting_value("usd_inr", 91.0)
    usd_rub = await get_setting_value("usd_rub", 80.0)

    # 🔐 РАСЧЁТ ЦЕНЫ
    price_usd = product.price_inr / usd_inr
    price_rub = int(price_usd * usd_rub)

    # 1. ✅ ОТПРАВЛЯЕМ ПОДТВЕРЖДЕНИЕ КЛИЕНТУ (ПРОСТОЕ)
    client_text = f"✅ <b>Ваш запрос принят!</b>\n\n"
    client_text += f"🛍 <b>{product.title[:80]}</b>\n\n"
    client_text += f"💰 Цена: {price_rub:,} ₽\n\n"
    client_text += f"📝 <b>Менеджер свяжется с вами в ближайшее время!</b>\n\n"
    client_text += f"💬 <i>Ответим в этом чате.</i>"

    await message.answer(client_text, parse_mode="HTML")

    # 2. ✅ ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ МЕНЕДЖЕРУ (НЕСКОЛЬКИМ МЕНЕДЖЕРАМ)
    manager_username = await get_manager_for_notification()

    manager_text = f"📬 <b>Новый запрос от клиента!</b>\n\n"
    manager_text += f"🛍 <b>{product.title[:100]}</b>\n\n"
    manager_text += f"💰 Цена: {price_rub:,} ₽\n\n"
    manager_text += f"👤 <b>Клиент:</b> @{message.from_user.username or 'ник скрыт'}\n"
    manager_text += f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
    manager_text += f"💬 <i>Напишите клиенту в этом чате!</i>"

    # 🔐 КНОПКА ДЛЯ МЕНЕДЖЕРА - ПРОСТО НАПОМИНАНИЕ
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="ℹ️ Написать в ЛС", url=f"tg://user?id={message.from_user.id}")
    )

    # Отправляем уведомление всем активным менеджерам
    managers = await get_active_managers()

    for manager in managers:
        try:
            # Пробуем с фото
            if product.images:
                import json
                images = json.loads(product.images) if isinstance(product.images, str) else product.images
                if images and images[0].startswith('http'):
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(images[0]) as resp:
                            if resp.status == 200:
                                photo = await resp.read()
                                await message.bot.send_photo(
                                    chat_id=manager.telegram_id,
                                    photo=photo,
                                    caption=manager_text,
                                    reply_markup=keyboard.as_markup(),
                                    parse_mode="HTML"
                                )
                                return
            # Если фото не удалось — отправляем текст
            await message.bot.send_message(
                chat_id=manager.telegram_id,
                text=manager_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to notify manager {manager.username}: {e}")

    # Фоллбэк: уведомляем админов если нет менеджеров
    if not managers:
        for admin_id in settings.admin_ids:
            if admin_id != message.from_user.id:
                try:
                    await message.bot.send_message(
                        chat_id=admin_id,
                        text=manager_text,
                        reply_markup=keyboard.as_markup(),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin_id}: {e}")

    logger.info(f"✅ Manager(s) notified about product #{product_id} (client: @{message.from_user.username})")


# ===== ХЭНДЛЕР НА /start order_{product_id} =====

@router.message(F.text.regexp(r"^/start order_(\d+)"))
async def manager_order_notification(message: Message):
    """
    🔐 Клиент нажал "Заказать" → бот присылает карточку менеджеру
    """
    # 🔐 ИЗВЛЕКАЕМ PRODUCT_ID ИЗ СООБЩЕНИЯ
    match = re.match(r"^/start order_(\d+)", message.text.strip())

    if not match:
        logger.warning(f"⚠️ Failed to extract product_id from: {message.text}")
        return

    product_id = int(match.group(1))
    logger.info(f"🔐 Received /start order_{product_id} from user {message.from_user.id}")

    # 🔐 ПОЛУЧАЕМ ТОВАР ИЗ БД
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()

    if not product:
        await message.answer("❌ Товар не найден")
        return

    # 🔐 ПОЛУЧАЕМ КУРСЫ
    usd_inr = await get_setting_value("usd_inr", 91.0)
    usd_rub = await get_setting_value("usd_rub", 80.0)

    # 🔐 РАСЧЁТ ЦЕНЫ
    price_usd = product.price_inr / usd_inr
    price_rub = int(price_usd * usd_rub)

    # 1. ✅ ОТПРАВЛЯЕМ ПОДТВЕРЖДЕНИЕ КЛИЕНТУ
    # 🔐 ПОЛУЧАЕМ МЕНЕДЖЕРА ИЗ БД
    manager_username = await get_manager_for_notification()

    client_text = f"✅ <b>Ваш запрос принят!</b>\n\n"
    client_text += f"🛍 <b>{product.title[:80]}</b>\n\n"
    client_text += f"💰 Цена: {price_rub:,} ₽\n\n"
    client_text += f"📝 <b>Менеджер уже уведомлён и скоро свяжется с вами!</b>\n\n"
    client_text += f"👤 <b>Ваш менеджер:</b> @{manager_username}\n\n"
    client_text += f"💬 <i>Менеджер напишет вам в этот чат в ближайшее время.</i>"

    # 🔐 КНОПКА НА МЕНЕДЖЕРА (просто ссылка, не обязательна)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="📝 Написать менеджеру заранее", url=f"https://t.me/{manager_username}")
    )

    await message.answer(client_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

    # 2. ✅ ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ МЕНЕДЖЕРУ (НЕСКОЛЬКИМ МЕНЕДЖЕРАМ)
    manager_text = f"📬 <b>Новый запрос от клиента!</b>\n\n"
    manager_text += f"🛍 <b>{product.title[:100]}</b>\n\n"

    if product.original_price_inr and product.discount_percent > 0:
        manager_text += f"🔥 <b>СКИДКА {int(product.discount_percent)}%</b>\n"
        manager_text += f"<s>₹{product.original_price_inr:,.0f}</s> → <b>₹{product.price_inr:,.0f}</b>\n"
        manager_text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"
    else:
        manager_text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"

    manager_text += f"{'✅' if product.in_stock else '❌'} В наличии\n\n"
    manager_text += f"👤 <b>Клиент:</b> @{message.from_user.username or 'без username'}\n"
    manager_text += f"🆔 <b>ID клиента:</b> <code>{message.from_user.id}</code>\n\n"
    manager_text += f"🔗 <a href='{product.source_url}'>Оригинал</a>\n\n"
    manager_text += f"💬 <i>Нажмите кнопку ниже чтобы написать клиенту!</i>"

    # 🔐 КНОПКИ ДЛЯ МЕНЕДЖЕРА
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✍️ Написать клиенту", url=f"tg://user?id={message.from_user.id}")
    )

    # Отправляем уведомление всем активным менеджерам
    managers = await get_active_managers()

    for manager in managers:
        try:
            # Пробуем с фото
            if product.images:
                import json
                images = json.loads(product.images) if isinstance(product.images, str) else product.images
                if images and images[0].startswith('http'):
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(images[0]) as resp:
                            if resp.status == 200:
                                photo = await resp.read()
                                await message.bot.send_photo(
                                    chat_id=manager.telegram_id,
                                    photo=photo,
                                    caption=manager_text,
                                    reply_markup=keyboard.as_markup(),
                                    parse_mode="HTML"
                                )
                                return
            # Если фото не удалось — отправляем текст
            await message.bot.send_message(
                chat_id=manager.telegram_id,
                text=manager_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to notify manager {manager.username}: {e}")

    # Фоллбэк: уведомляем админов если нет менеджеров
    if not managers:
        for admin_id in settings.admin_ids:
            if admin_id != message.from_user.id:
                try:
                    await message.bot.send_message(
                        chat_id=admin_id,
                        text=manager_text,
                        reply_markup=keyboard.as_markup(),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin_id}: {e}")

    logger.info(f"✅ Manager(s) notified about product #{product_id} (client: @{message.from_user.username})")


# ===== ХЭНДЛЕР НА СООБЩЕНИЯ МЕНЕДЖЕРУ =====

@router.callback_query(F.data.startswith("copy_artifact:"))
async def copy_artifact_callback(callback: CallbackQuery):
    """
    🔐 Копирование артикула товара
    """
    product_id = callback.data.split(":")[1]

    await callback.answer(
        f"📋 Артикул #{product_id} скопирован!\n\n"
        f"Отправьте его менеджеру.",
        show_alert=True
    )


@router.message()
async def manager_message_handler(message: Message):
    """
    🔐 Обработка сообщений которые получает менеджер от клиентов
    Автоматически присылает карточку товара если есть артикул или пересланное сообщение
    """
    # Проверяем что это менеджер (через БД)
    if not message.from_user.username:
        return

    # Проверяем есть ли пользователь в менеджерах
    managers = await get_active_managers()
    is_manager = any(m.telegram_id == str(message.from_user.id) for m in managers)

    # Если нет в БД, проверяем старый формат (username из настроек)
    if not is_manager:
        async with database.get_session() as session:
            result = await session.execute(select(Setting).where(Setting.key == "manager_username"))
            setting = result.scalar()
            manager_username = setting.value if setting else "tatastu"
            manager_usernames = [m.strip().lstrip('@') for m in manager_username.split(',')]
            is_manager = message.from_user.username.lower() in [m.lower() for m in manager_usernames]

    if not is_manager:
        return

    # 🔐 ПРОВЕРКА ПЕРЕСЛАННОГО СООБЩЕНИЯ ИЗ КАНАЛА
    if message.forward_from_chat:
        # Это переслано из канала! Ищем ID товара в подписи
        caption = message.forward_from_message.caption if message.forward_from_message else ""
        if caption:
            # Ищем ID в формате "🆔 ID: <code>123</code>" или "#123"
            match = re.search(r'🆔 ID:\s*<code>(\d+)</code>|#(\d+)', caption)
            if match:
                product_id = int(match.group(1) or match.group(2))
                await send_product_card(message, product_id)
                return

    # Ищем артикул в сообщении (формат: #123 или Артикул: #123)
    text = message.text or message.caption
    if not text:
        return

    # 🔐 ПАРСИНГ АРТИКУЛА
    match = re.search(r'#(\d+)', text)
    if not match:
        return

    product_id = int(match.group(1))
    await send_product_card(message, product_id)


async def send_product_card(message: Message, product_id: int):
    """Отправляет карточку товара менеджеру"""
    logger.info(f"🔐 Sending product card #{product_id} to manager")

    # 🔐 ПОЛУЧАЕМ ТОВАР ИЗ БД
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()

    if not product:
        await message.answer(f"❌ Товар #{product_id} не найден")
        return

    # 🔐 ПОЛУЧАЕМ КУРСЫ
    usd_inr = await get_setting_value("usd_inr", 91.0)
    usd_rub = await get_setting_value("usd_rub", 80.0)

    # 🔐 РАСЧЁТ ЦЕНЫ
    price_usd = product.price_inr / usd_inr
    price_rub = int(price_usd * usd_rub)

    # 🔐 ФОРМИРУЕМ КАРТОЧКУ
    text = f"🛍 <b>Товар из запроса клиента</b>\n\n"
    text += f"<b>{product.title[:100]}</b>\n\n"

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

    # 🔐 ССЫЛКИ ТЕПЕРЬ В КНОПКАХ, а не в тексте

    text += f"<b>🆔 ID:</b> <code>{product.id}</code>"

    # 🔐 КНОПКИ ДЛЯ МЕНЕДЖЕРА
    keyboard = InlineKeyboardBuilder()

    # 🔐 КНОПКИ ССЫЛОК (фото и оригинал)
    link_buttons = []
    if product.images:
        import json
        images = json.loads(product.images) if isinstance(product.images, str) else product.images
        if images and images[0].startswith('http'):
            link_buttons.append(InlineKeyboardButton(text="🖼 Фото товара", url=images[0]))
    
    if product.source_url:
        link_buttons.append(InlineKeyboardButton(text="🔗 Оригинал", url=product.source_url))
    
    if link_buttons:
        keyboard.row(*link_buttons)

    keyboard.row(
        InlineKeyboardButton(text="📤 Опубликовать", callback_data=f"product_publish:{product.id}")
    )

    keyboard.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"product_edit:{product.id}")
    )

    keyboard.row(
        InlineKeyboardButton(text="🔙 В админку", callback_data="admin_back")
    )

    # 🔐 ОТПРАВЛЯЕМ КАРТОЧКУ МЕНЕДЖЕРУ
    try:
        if product.images:
            import json
            images = json.loads(product.images) if isinstance(product.images, str) else product.images
            if images and images[0].startswith('http'):
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(images[0]) as resp:
                        if resp.status == 200:
                            photo = await resp.read()
                            await message.answer_photo(
                                photo=photo,
                                caption=text,
                                reply_markup=keyboard.as_markup(),
                                parse_mode="HTML"
                            )
                            return
    except Exception as e:
        logger.warning(f"Failed to send photo to manager: {e}")

    # Если фото не удалось — отправляем текст
    await message.answer(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    logger.info(f"Manager notified about product #{product_id} (user: {message.from_user.username})")
