"""
Admin Posting Handler - Авто-постинг и управление группами
"""

import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from app.core.config import settings
from app.db.database import database
from app.db.repositories import PostGroupRepository, ProductRepository
from app.db.models import PostGroup
from app.utils.logger import logger
from app.bots.handlers.admin_menu import AdminStates

router = Router(name="admin_posting")


class AddChannelState(StatesGroup):
    """Состояния для добавления канала"""
    waiting_for_channel_id = State()


@router.message(F.text == "📢 Авто-постинг")
async def admin_auto_post(message: Message, state: FSMContext):
    """Меню авто-постинга"""
    await state.clear()  # 🔐 ПРИНУДИТЕЛЬНЫЙ СБРОС ЛЮБОГО СОСТОЯНИЯ
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Добавить группу", callback_data="post_add_group"),
        InlineKeyboardButton(text="📋 Список групп", callback_data="post_list_groups"),
    )
    builder.row(
        InlineKeyboardButton(text="🧪 Тестовый пост", callback_data="post_test"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"),
    )

    await message.answer(
        "📢 <b>Авто-постинг</b>\n\n"
        "✅ <b>Функции:</b>\n"
        "• Добавление Telegram каналов\n"
        "• Авто-постинг товаров\n"
        "• Тестовая отправка поста\n\n"
        "Управление группами и расписанием:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "post_add_group")
async def post_add_group(call: CallbackQuery, state: FSMContext):
    """Добавление группы/канала"""
    text = (
        "<b>➕ Добавление канала для автопостинга</b>\n\n"
        "1️⃣ Добавьте меня (<b>@tatastu_bot</b>) в ваш канал или группу.\n"
        "2️⃣ Назначьте меня <b>Администратором</b> (нужны права на публикацию).\n"
        "3️⃣ Пришлите мне <code>@username</code> канала или <b>перешлите любое сообщение</b> оттуда.\n\n"
        "💡 <i>Отмена: /cancel</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AddChannelState.waiting_for_channel_id)
    await call.answer()


@router.message(AddChannelState.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    """Обработка добавления канала/группы"""
    try:
        bot = message.bot
        
        # 🔐 ШАГ 1: Определяем chat_id
        chat_id = None
        
        # Если юзер переслал сообщение из канала/группы
        if message.forward_from_chat:
            chat_id = message.forward_from_chat.id
            logger.info(f"Forwarded from chat: {message.forward_from_chat}")
        else:
            # Если юзер скинул @username или ID
            chat_identifier = message.text.strip()
            if not chat_identifier:
                await message.answer(
                    "❌ <b>Пустое сообщение</b>\n\n"
                    "Пришлите @username или перешлите сообщение из канала.",
                    parse_mode="HTML",
                )
                return
            
            chat_id = chat_identifier
        
        # 🔐 ШАГ 2: Проверяем что бот видит чат
        await message.answer("⏳ <b>Проверяю канал...</b>", parse_mode="HTML")
        
        chat = await bot.get_chat(chat_id)
        
        # 🔐 ШАГ 3: КРИТИЧЕСКАЯ ПРОВЕРКА - есть ли у бота права админа
        bot_member = await chat.get_member(bot.id)
        
        if bot_member.status not in ["administrator", "creator"]:
            await message.answer(
                "❌ <b>Я не администратор!</b>\n\n"
                f"Канал: <b>{html.escape(chat.title)}</b>\n\n"
                "1. Добавьте бота @tatastu_bot в канал\n"
                "2. Назначьте его <b>Администратором</b>\n"
                "3. Попробуйте снова",
                parse_mode="HTML",
            )
            await state.clear()
            return
        
        # 🔐 ШАГ 4: Проверяем дубликат
        async with database.get_session() as session:
            group_repo = PostGroupRepository(session)
            
            existing = await group_repo.get_by_chat_id(str(chat.id))
            if existing:
                await message.answer(
                    "⚠️ <b>Уже добавлено!</b>\n\n"
                    f"Канал: <b>{html.escape(chat.title)}</b>\n"
                    f"ID: <code>{chat.id}</code>\n\n"
                    "Используйте эту группу для постинга.",
                    parse_mode="HTML",
                )
                await state.clear()
                return
            
            # 🔐 ШАГ 5: Сохраняем в БД
            group = await group_repo.create({
                "chat_id": str(chat.id),
                "chat_name": chat.title[:100],
                "chat_username": chat.username,
                "chat_type": chat.type,
                "is_active": True,
            })
        
        await message.answer(
            "✅ <b>Канал успешно добавлен!</b>\n\n"
            f"📢 <b>{html.escape(chat.title)}</b>\n"
            f"🆔 ID: <code>{chat.id}</code>\n"
            f"📝 Запись #{group.id}\n\n"
            "Теперь вы можете отправить <b>тестовый пост</b>!",
            parse_mode="HTML",
        )
        
        await state.clear()
        
    except TelegramAPIError as e:
        logger.error(f"Telegram API error: {e}")
        await message.answer(
            f"❌ <b>Ошибка Telegram</b>\n\n"
            f"<i>{html.escape(str(e)[:200])}</i>\n\n"
            "Убедитесь что:\n"
            "• Бот добавлен в канал\n"
            "• Вы отправили правильный @username\n"
            "• Или перешлите сообщение из канала",
            parse_mode="HTML",
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Add channel error: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка</b>\n\n"
            f"<i>{html.escape(str(e)[:200])}</i>\n\n"
            "Попробуйте снова или обратитесь в поддержку.",
            parse_mode="HTML",
        )
        await state.clear()


@router.callback_query(F.data == "post_list_groups")
async def post_list_groups(callback: CallbackQuery):
    """Список групп для постинга"""
    try:
        from sqlalchemy import select
        
        async with database.get_session() as session:
            # Получаем все группы
            result = await session.execute(select(PostGroup).order_by(PostGroup.created_at.desc()))
            groups_list = result.scalars().all()

            if not groups_list:
                await callback.message.answer(
                    "📢 <b>Группы не найдены</b>\n\n"
                    "Добавьте первую группу для автопостинга.",
                    parse_mode="HTML",
                )
                await callback.answer()
                return

            text = "📢 <b>Группы для постинга</b>\n\n"
            for i, group in enumerate(groups_list, 1):
                status = "✅" if group.is_active else "❌"
                text += f"{i}. {status} {html.escape(group.chat_name)}\n"
                if group.chat_username:
                    text += f"   @{group.chat_username}\n"
                text += f"   ID: {group.chat_id}\n\n"

            await callback.message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"List groups error: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)


@router.callback_query(F.data == "post_test")
async def post_test(callback: CallbackQuery):
    """Тестовый пост - выбор группы и товара"""
    try:
        logger.info("Test post requested")
        
        async with database.get_session() as session:
            group_repo = PostGroupRepository(session)
            product_repo = ProductRepository(session)

            # Получаем активные группы
            groups = await group_repo.get_all_active()

            if not groups:
                await callback.message.answer(
                    "🧪 <b>Нет групп для теста!</b>\n\n"
                    "Сначала добавьте группу для автопостинга.",
                    parse_mode="HTML",
                )
                await callback.answer()
                return

            # Получаем последний товар
            products = await product_repo.get_all(limit=1)

            if not products:
                await callback.message.answer(
                    "🧪 <b>Нет товаров для теста!</b>\n\n"
                    "Сначала добавьте товары в каталог.",
                    parse_mode="HTML",
                )
                await callback.answer()
                return

            # Отправляем тестовый пост в первую группу
            group = groups[0]
            product = products[0]
            
            logger.info(f"Test post: group={group.chat_name} (id={group.id}, chat_id={group.chat_id}), product={product.title[:50]}")

            from app.services.poster_service import poster_service

            if not poster_service:
                await callback.message.answer(
                    "❌ <b>Сервис постинга не инициализирован!</b>",
                    parse_mode="HTML",
                )
                await callback.answer()
                return

            success = await poster_service.test_post(group.id, product.id)
            
            logger.info(f"Test post result: success={success}")

            if success:
                await callback.message.answer(
                    "✅ <b>Тестовый пост отправлен!</b>\n\n"
                    f"📢 Группа: {group.chat_name}\n"
                    f"🛍 Товар: {product.title[:50]}...\n\n"
                    "Проверьте группу в Telegram.",
                    parse_mode="HTML",
                )
            else:
                await callback.message.answer(
                    "❌ <b>Ошибка отправки!</b>\n\n"
                    "Проверьте логи бота.\n\n"
                    "Возможные причины:\n"
                    "• Бот не администратор в группе\n"
                    "• Неверный chat_id группы\n"
                    "• Telegram API временно недоступен",
                    parse_mode="HTML",
                )

    except Exception as e:
        logger.error(f"Test post error: {type(e).__name__}: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n"
            f"<i>{str(e)[:200]}</i>",
            parse_mode="HTML",
        )

    await callback.answer()
