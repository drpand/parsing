"""
Admin Products Handler v1.1 — Товары (список, карточка, публикация)
© 2026 All Rights Reserved.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from app.core.config import settings
from app.db.database import database
from app.db.models import Product
from app.utils.logger import logger
from app.bots.handlers.admin_settings import get_setting_value
from aiogram.fsm.state import State, StatesGroup
import json
import requests

# 🔐 ДОПОЛНИТЕЛЬНЫЕ СОСТОЯНИЯ ДЛЯ РЕДАКТИРОВАНИЯ
class ProductEditStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_in_stock = State()
    waiting_for_delete_confirm = State()
    waiting_for_edit_action = State()

router = Router()

ITEMS_PER_PAGE = 10


# ===== ОБРАБОТКА КНОПКИ "📦 Товары" (ТЕКСТ) =====

@router.message(F.text == "📦 Товары")
async def admin_products_text(message: Message, state: FSMContext):
    """📦 Обработка кнопки 'Товары' из главного меню"""
    await state.clear()

    user_id = message.from_user.id
    is_admin = user_id in settings.admin_ids
    is_manager = False
    if not is_admin:
        async with database.get_session() as session:
            from app.db.repositories import ManagerRepository
            repo = ManagerRepository(session)
            managers = await repo.get_all_active()
            is_manager = any(m.telegram_id == str(user_id) for m in managers)

    if not is_admin and not is_manager:
        return

    logger.info(f"{'Manager' if is_manager else 'Admin'} {user_id} clicked 'Товары' button")

    try:
        async with database.get_session() as session:
            total = (await session.execute(select(func.count(Product.id)))).scalar() or 0

            if total == 0:
                await message.answer("📭 База товаров пуста!")
                return

            await show_products_page(message, state, page=1)

    except Exception as e:
        logger.error(f"❌ Ошибка при просмотре товаров: {type(e).__name__}: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка при загрузке товаров!\n\n"
            f"{str(e)[:200]}\n\n"
            "Попробуйте позже или проверьте логи.",
        )


async def show_products_page(callback, state: FSMContext, page: int = 1):
    """📄 Показать страницу товаров"""
    await state.clear()

    user_id = callback.from_user.id
    is_admin = user_id in settings.admin_ids
    is_manager = False
    if not is_admin:
        async with database.get_session() as session:
            from app.db.repositories import ManagerRepository
            repo = ManagerRepository(session)
            managers = await repo.get_all_active()
            is_manager = any(m.telegram_id == str(user_id) for m in managers)

    if not is_admin and not is_manager:
        return

    try:
        async with database.get_session() as session:
            total = (await session.execute(select(func.count(Product.id)))).scalar() or 0
            total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            page = max(1, min(page, total_pages))

            offset = (page - 1) * ITEMS_PER_PAGE
            result = await session.execute(
                select(Product).order_by(Product.created_at.desc()).offset(offset).limit(ITEMS_PER_PAGE)
            )
            products = result.scalars().all()

            keyboard = InlineKeyboardBuilder()
            for product in products:
                title = product.title[:40]
                price = f"{product.price_rub:,.0f}₽"
                keyboard.row(InlineKeyboardButton(text=f"{title} | {price}", callback_data=f"product_view:{product.id}"))

            nav = []
            if page > 1:
                nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"products_page:{page-1}"))
            nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
            if page < total_pages:
                nav.append(InlineKeyboardButton(text="➡️", callback_data=f"products_page:{page+1}"))
            keyboard.row(*nav)
            keyboard.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back" if is_admin else "back"))

            text = f"📦 Товары: {total}" if total > 0 else "📭 Пусто"

            if isinstance(callback, CallbackQuery):
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
                except:
                    await callback.message.answer(text, reply_markup=keyboard.as_markup())
            else:
                await callback.answer(text, reply_markup=keyboard.as_markup())

    except Exception as e:
        logger.error(f"Products list error: {e}")


@router.callback_query(F.data.startswith("products_page:"))
async def products_pagination(callback: CallbackQuery, state: FSMContext):
    """📄 Пагинация"""
    await callback.answer()
    page = int(callback.data.split(":")[1])
    await show_products_page(callback, state, page)


# ===== ПРОСМОТР ТОВАРА =====

@router.callback_query(F.data.startswith("product_view:"))
async def product_view(callback: CallbackQuery, state: FSMContext):
    """👁️ Просмотр товара — Админы и Менеджеры"""
    if callback.from_user.id not in settings.admin_ids:
        # Проверка для менеджеров
        async with database.get_session() as session:
            from app.db.repositories import ManagerRepository
            repo = ManagerRepository(session)
            managers = await repo.get_all_active()
            is_manager = any(m.telegram_id == str(callback.from_user.id) for m in managers)
            if not is_manager:
                await callback.answer("❌ Доступ запрещён", show_alert=True)
                return

    product_id = int(callback.data.split(":")[1])
    logger.info(f"Viewing product: {product_id}")

    try:
        async with database.get_session() as session:
            result = await session.execute(select(Product).where(Product.id == product_id))
            product = result.scalar()

            if not product:
                await callback.answer("❌ Товар не найден", show_alert=True)
                return

            # 🔐 ПОЛУЧАЕМ КУРСЫ ИЗ БД
            usd_inr = await get_setting_value("usd_inr", 91.0)
            usd_rub = await get_setting_value("usd_rub", 80.0)

            # 🔐 РАСЧЁТ ЦЕНЫ: INR → USD → RUB
            price_usd = product.price_inr / usd_inr
            price_rub = int(price_usd * usd_rub)

            # 🔐 НАВИГАЦИЯ: получаем ID предыдущего и следующего товара
            all_ids_result = await session.execute(
                select(Product.id).order_by(Product.created_at.desc())
            )
            all_ids = [row[0] for row in all_ids_result.all()]

            try:
                current_index = all_ids.index(product_id)
            except ValueError:
                current_index = -1

            prev_id = all_ids[current_index + 1] if current_index >= 0 and current_index + 1 < len(all_ids) else None
            next_id = all_ids[current_index - 1] if current_index > 0 else None

            # 🔐 ФОРМИРУЕМ КАРТОЧКУ
            text = f"🛍 <b>{product.title[:100]}</b>\n\n"

            if product.original_price_inr and product.discount_percent > 0:
                text += f"🔥 СКИДКА {int(product.discount_percent)}%\n"
                text += f"<s>₹{product.original_price_inr:,.0f}</s> → <b>₹{product.price_inr:,.0f}</b>\n"
                text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"
            else:
                text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"

            text += f"{'✅' if product.in_stock else '❌'} В наличии\n\n"

            if product.is_active:
                if product.last_posted_at:
                    from datetime import timedelta
                    local_time = product.last_posted_at + timedelta(hours=5, minutes=30)
                    date_str = local_time.strftime("%d.%m.%Y %H:%M")
                    text += f"📊 Опубликован: {date_str} (IST)\n\n"
                else:
                    text += f"📊 Опубликован: Дата не указана\n\n"
            else:
                text += f"📊 Не опубликован\n\n"

            # 🔐 ФОТО И ОРИГИНАЛ - С ССЫЛКАМИ!
            if product.images:
                images = json.loads(product.images) if isinstance(product.images, str) else product.images
                if images:
                    text += f"🖼 <a href='{images[0]}'>Фото товара</a>\n\n"

            if product.source_url:
                text += f"🔗 <a href='{product.source_url}'>Оригинал на сайте</a>\n\n"

            text += f"🆔 ID: <code>{product.id}</code>"
            text += f"\n\n📊 Позиция: {current_index + 1} из {len(all_ids)}"

            # 🔐 КНОПКИ СО СТРЕЛКАМИ НАВИГАЦИИ
            keyboard = InlineKeyboardBuilder()

            # 🔐 СТРЕЛКИ НАВИГАЦИИ (первый ряд)
            nav_buttons = []
            if prev_id:
                nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"product_view:{prev_id}"))
            else:
                nav_buttons.append(InlineKeyboardButton(text="⚪", callback_data="empty"))

            nav_buttons.append(InlineKeyboardButton(text="🔙 К списку", callback_data="products_page:1"))

            if next_id:
                nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"product_view:{next_id}"))
            else:
                nav_buttons.append(InlineKeyboardButton(text="⚪", callback_data="empty"))

            keyboard.row(*nav_buttons)

            # 🔐 КНОПКИ ССЫЛОК (фото и оригинал)
            link_buttons = []
            if product.images:
                images = json.loads(product.images) if isinstance(product.images, str) else product.images
                if images and images[0].startswith('http'):
                    link_buttons.append(InlineKeyboardButton(text="🖼 Фото товара", url=images[0]))
            
            if product.source_url:
                link_buttons.append(InlineKeyboardButton(text="🔗 Оригинал", url=product.source_url))
            
            if link_buttons:
                keyboard.row(*link_buttons)

            # Кнопки действий
            keyboard.row(InlineKeyboardButton(text="📤 Опубликовать", callback_data=f"product_publish:{product.id}"))
            keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"product_edit:{product.id}"))

            # 🔐 ТЕПЕРЬ УБИРАЕМ ССЫЛКИ ИЗ ТЕКСТА (они будут в кнопках)
            text = f"🛍 <b>{product.title[:100]}</b>\n\n"

            if product.original_price_inr and product.discount_percent > 0:
                text += f"🔥 СКИДКА {int(product.discount_percent)}%\n"
                text += f"<s>₹{product.original_price_inr:,.0f}</s> → <b>₹{product.price_inr:,.0f}</b>\n"
                text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"
            else:
                text += f"<b>💰 Цена: {price_rub:,} ₽</b>\n\n"

            text += f"{'✅' if product.in_stock else '❌'} В наличии\n\n"

            if product.is_active:
                if product.last_posted_at:
                    from datetime import timedelta
                    local_time = product.last_posted_at + timedelta(hours=5, minutes=30)
                    date_str = local_time.strftime("%d.%m.%Y %H:%M")
                    text += f"📊 Опубликован: {date_str} (IST)\n\n"
                else:
                    text += f"📊 Опубликован: Дата не указана\n\n"
            else:
                text += f"📊 Не опубликован\n\n"

            text += f"🆔 ID: <code>{product.id}</code>"
            text += f"\n\n📊 Позиция: {current_index + 1} из {len(all_ids)}"

            # 🔐 ОТПРАВЛЯЕМ С ФОТО И КНОПКАМИ
            try:
                if product.images:
                    images = json.loads(product.images) if isinstance(product.images, str) else product.images
                    if images and images[0].startswith('http'):
                        response = requests.get(images[0], timeout=10)
                        if response.status_code == 200:
                            photo = BufferedInputFile(response.content, filename=f"product_{product.id}.jpg")
                            await callback.message.answer_photo(
                                photo=photo,
                                caption=text,
                                reply_markup=keyboard.as_markup(),
                                parse_mode="HTML",
                            )
                            await callback.answer()
                            return
            except Exception as e:
                logger.warning(f"Failed to send photo: {e}")

            # Если фото не удалось — отправляем текст
            await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            await callback.answer()

    except Exception as e:
        logger.error(f"Product view error: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)


# ===== РЕДАКТИРОВАНИЕ =====

@router.callback_query(F.data.startswith("product_edit:"))
async def product_edit_start(callback: CallbackQuery, state: FSMContext):
    """✏️ Редактирование товара"""
    await state.clear()

    user_id = callback.from_user.id
    is_admin = user_id in settings.admin_ids
    is_manager = False
    if not is_admin:
        async with database.get_session() as session:
            from app.db.repositories import ManagerRepository
            repo = ManagerRepository(session)
            managers = await repo.get_all_active()
            is_manager = any(m.telegram_id == str(user_id) for m in managers)

    if not is_admin and not is_manager:
        return

    product_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()

        if not product:
            await callback.answer("❌ Товар не найден", show_alert=True)
            return

        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="📝 Название", callback_data=f"edit_field:title:{product.id}"))
        keyboard.row(InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_field:price:{product.id}"))
        keyboard.row(InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_field:description:{product.id}"))
        keyboard.row(InlineKeyboardButton(text="🔙 Назад", callback_data=f"product_view:{product.id}"))

        text = f"✏️ Редактирование #{product.id}\n\n"
        text += f"Название: {product.title[:50]}...\n"
        text += f"Цена: ₹{product.price_inr:,.0f}\n\n"
        text += "Выберите поле:"

        try:
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        except:
            await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("edit_field:"))
async def product_edit_field(callback: CallbackQuery, state: FSMContext):
    """✏️ Редактирование поля"""
    parts = callback.data.split(":")
    field = parts[1]
    product_id = int(parts[2])

    await state.update_data(edit_product_id=product_id)

    if field == "title":
        await state.set_state(ProductEditStates.waiting_for_title)
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"product_edit:{product_id}"))
        await callback.message.edit_text("📝 Новое название:", reply_markup=keyboard.as_markup())
    elif field == "price":
        await state.set_state(ProductEditStates.waiting_for_price)
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"product_edit:{product_id}"))
        await callback.message.edit_text("💰 Новая цена (INR):", reply_markup=keyboard.as_markup())
    elif field == "description":
        await state.set_state(ProductEditStates.waiting_for_description)
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"product_edit:{product_id}"))
        await callback.message.edit_text("📝 Новое описание:", reply_markup=keyboard.as_markup())


@router.message(ProductEditStates.waiting_for_title)
async def product_edit_title_save(message: Message, state: FSMContext):
    """💾 Сохранение названия"""
    data = await state.get_data()
    product_id = data.get("edit_product_id")
    if not product_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return

    new_title = message.text.strip()[:200]
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        if product:
            product.title = new_title
            await session.commit()

    await message.answer(f"✅ Название обновлено: {new_title[:50]}")
    await state.clear()

    from app.bots.handlers.manager import send_product_card
    await send_product_card(message, product_id)


@router.message(ProductEditStates.waiting_for_price)
async def product_edit_price_save(message: Message, state: FSMContext):
    """💾 Сохранение цены"""
    data = await state.get_data()
    product_id = data.get("edit_product_id")
    if not product_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return

    try:
        new_price = float(message.text.strip())
    except:
        await message.answer("❌ Неверный формат")
        return

    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        if product:
            product.price_inr = new_price
            await session.commit()

    await message.answer(f"✅ Цена обновлена: ₹{new_price:,.0f}")
    await state.clear()

    from app.bots.handlers.manager import send_product_card
    await send_product_card(message, product_id)


@router.message(ProductEditStates.waiting_for_description)
async def product_edit_description_save(message: Message, state: FSMContext):
    """💾 Сохранение описания"""
    data = await state.get_data()
    product_id = data.get("edit_product_id")
    if not product_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return

    new_desc = message.text.strip()[:1000]
    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()
        if product:
            product.description = new_desc
            await session.commit()

    await message.answer("✅ Описание обновлено")
    await state.clear()

    from app.bots.handlers.manager import send_product_card
    await send_product_card(message, product_id)


# ===== ПУБЛИКАЦИЯ =====

@router.callback_query(F.data.startswith("product_publish:"))
async def product_publish_now(callback: CallbackQuery):
    """📤 Публикация товара"""
    await callback.answer()

    user_id = callback.from_user.id
    is_admin = user_id in settings.admin_ids
    is_manager = False
    if not is_admin:
        async with database.get_session() as session:
            from app.db.repositories import ManagerRepository
            repo = ManagerRepository(session)
            managers = await repo.get_all_active()
            is_manager = any(m.telegram_id == str(user_id) for m in managers)

    if not is_admin and not is_manager:
        return

    product_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar()

        if not product:
            await callback.answer("❌ Товар не найден", show_alert=True)
            return

        from app.services.poster_service import poster_service
        if not poster_service:
            await callback.answer("❌ Сервис не инициализирован", show_alert=True)
            return

        # Получаем активные группы для публикации
        from app.db.models import PostGroup
        groups_result = await session.execute(
            select(PostGroup).where(PostGroup.is_active == True)
        )
        groups = groups_result.scalars().all()

        if not groups:
            await callback.answer("❌ Нет активных групп для публикации!", show_alert=True)
            return

        # Публикуем в первую активную группу
        group = groups[0]
        success = await poster_service._send_post(group, product)

        if success:
            # Записываем дату публикации
            from datetime import datetime
            product.last_posted_at = datetime.utcnow()
            product.is_active = True
            await session.commit()

            # 🔐 ОТПРАВЛЯЕМ СООБЩЕНИЕ В ЧАТ ВМЕСТО show_alert
            await callback.message.answer(
                f"✅ <b>Товар опубликован в {group.chat_username}!</b>\n\n"
                f"🛍 {product.title[:50]}...\n"
                f"💰 {product.price_rub:,.0f} ₽",
                parse_mode="HTML"
            )
            logger.info(f"{'Manager' if is_manager else 'Admin'} {user_id} published product {product_id} to {group.chat_username}")
        else:
            await callback.answer("❌ Не удалось опубликовать товар", show_alert=True)
            logger.error(f"Failed to publish product {product_id}")
