"""
Admin Managers Handler v1.2 — Управление менеджерами
Добавление, просмотр, деактивация и удаление менеджеров
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.db.database import database
from app.db.models import Manager
from app.db.repositories import ManagerRepository
from app.core.config import settings
from app.utils.logger import logger
from app.bots.keyboards.managers import (
    get_managers_list_keyboard,
    get_manager_detail_keyboard,
    get_add_manager_keyboard,
    get_confirm_add_manager_keyboard,
)

router = Router(name="admin_managers")


class ManagerStates(StatesGroup):
    """Состояния для управления менеджерами"""
    waiting_for_username = State()
    waiting_for_confirm = State()


# ===== ГЛАВНОЕ МЕНЮ МЕНЕДЖЕРОВ =====

@router.callback_query(F.data == "admin_managers_list")
async def managers_list(callback: CallbackQuery):
    """📋 Список всех менеджеров"""
    await callback.answer()

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        managers = await repo.get_all()

    logger.info(f"🔐 Managers list: found {len(managers)} managers")
    for m in managers:
        logger.info(f"  - @{m.username} (ID: {m.id}, active: {m.is_active})")

    if not managers:
        text = (
            "👥 <b>Менеджеры</b>\n\n"
            "Список менеджеров пуст.\n\n"
            "Нажмите «➕ Добавить менеджера» чтобы создать первого."
        )
    else:
        active_count = sum(1 for m in managers if m.is_active)
        text = (
            "👥 <b>Менеджеры</b>\n\n"
            f"Всего: {len(managers)} | Активных: {active_count}\n\n"
            "Нажмите на менеджера для просмотра деталей:"
        )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_managers_list_keyboard(managers),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_managers_list_keyboard(managers),
            parse_mode="HTML",
        )


# ===== ДОБАВЛЕНИЕ МЕНЕДЖЕРА =====

@router.callback_query(F.data == "manager_add")
async def manager_add_start(callback: CallbackQuery, state: FSMContext):
    """➕ Начало добавления менеджера"""
    await callback.answer()
    await state.clear()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="admin_managers_list")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            "➕ <b>Добавление менеджера</b>\n\n"
            "Отправьте username менеджера в Telegram:\n"
            "• Можно с @ или без (например: <code>username</code> или <code>@username</code>)\n"
            "• Username должен существовать\n"
            "• Проверьте правильность написания",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "➕ <b>Добавление менеджера</b>\n\n"
            "Отправьте username менеджера в Telegram:\n"
            "• Можно с @ или без (например: username или @username)\n"
            "• Username должен существовать\n"
            "• Проверьте правильность написания",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )

    await state.set_state(ManagerStates.waiting_for_username)


@router.message(ManagerStates.waiting_for_username)
async def manager_add_validate(message: Message, state: FSMContext):
    """Проверка и добавление менеджера"""
    username = message.text.strip().lstrip('@')

    # Валидация формата
    if not username or len(username) < 3 or len(username) > 32:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Username должен быть от 3 до 32 символов.\n\n"
            "Попробуйте ещё раз:"
        )
        return

    if not username.replace('_', '').replace('-', '').isalnum():
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Username может содержать только буквы, цифры, _ и -\n\n"
            "Попробуйте ещё раз:"
        )
        return

    # Проверяем существующего менеджера
    async with database.get_session() as session:
        repo = ManagerRepository(session)
        existing = await repo.get_by_username(username)

        if existing:
            if existing.is_active:
                await message.answer(
                    "⚠️ <b>Менеджер уже существует</b>\n\n"
                    f"Username: @{existing.username}\n"
                    f"Статус: ✅ Активен\n\n"
                    "Выберите действие:",
                    reply_markup=get_manager_detail_keyboard(existing.id),
                    parse_mode="HTML",
                )
                await state.clear()
                return
            else:
                # Активируем неактивного
                await repo.update(existing.id, {"is_active": True})
                await message.answer(
                    "✅ <b>Менеджер активирован!</b>\n\n"
                    f"Username: @{existing.username}\n\n"
                    "Теперь он может получать уведомления.",
                    parse_mode="HTML",
                )
                await state.clear()
                return

    # Предлагаем подтвердить добавление
    await message.answer(
        "✅ <b>Проверка пройдена</b>\n\n"
        f"Менеджер: @{username}\n\n"
        "Нажмите «Подтвердить» для добавления:",
        reply_markup=get_confirm_add_manager_keyboard(username),
        parse_mode="HTML",
    )
    await state.set_state(ManagerStates.waiting_for_confirm)


@router.callback_query(F.data.startswith("manager_confirm_add:"))
async def manager_add_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение добавления менеджера"""
    username = callback.data.split(":")[1]

    logger.info(f"🔐 Adding manager: @{username}")

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        # Создаём с заглушкой для telegram_id (будет обновлён при первом запросе)
        manager = await repo.create(
            telegram_id=f"temp_{username}",  # Временный ID
            username=username
        )

        logger.info(f"✅ Manager created in DB: ID={manager.id}, username={manager.username}, telegram_id={manager.telegram_id}")

    await callback.answer(f"✅ Менеджер @{username} добавлен!")
    logger.info(f"Manager added: @{username} (ID: {manager.id})")

    # 🔐 ПОКАЗЫВАЕМ ОБНОВЛЁННЫЙ СПИСОК МЕНЕДЖЕРОВ
    await managers_list(callback)
    await state.clear()


# ===== ПРОСМОТР МЕНЕДЖЕРА =====

@router.callback_query(F.data.startswith("manager_view:"))
async def manager_view(callback: CallbackQuery):
    """📋 Просмотр информации о менеджере"""
    manager_id = int(callback.data.split(":")[1])
    await callback.answer()

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        manager = await repo.get_by_id(manager_id)

    if not manager:
        await callback.answer("❌ Менеджер не найден", show_alert=True)
        return

    status_text = "✅ Активен" if manager.is_active else "❌ Не активен"
    main_text = "👑 Главный" if manager.is_main else "Обычный"

    text = (
        f"👤 <b>Менеджер</b>\n\n"
        f"Username: @{manager.username}\n"
        f"ID Telegram: <code>{manager.telegram_id}</code>\n"
        f"Имя: {manager.first_name or '—'}\n"
        f"Фамилия: {manager.last_name or '—'}\n\n"
        f"Статус: {status_text}\n"
        f"Роль: {main_text}\n\n"
        f"📊 Статистика:\n"
        f"• Запросов: {manager.total_queries}\n"
        f"• Заказов: {manager.total_orders}\n\n"
        f"Создан: {manager.created_at.strftime('%d.%m.%Y %H:%M') if manager.created_at else '—'}\n"
        f"Обновлён: {manager.updated_at.strftime('%d.%m.%Y %H:%M') if manager.updated_at else '—'}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_manager_detail_keyboard(manager.id, manager.is_active),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_manager_detail_keyboard(manager.id, manager.is_active),
            parse_mode="HTML",
        )


# ===== ДЕАКТИВАЦИЯ / АКТИВАЦИЯ =====

@router.callback_query(F.data.startswith("manager_deactivate:"))
async def manager_deactivate(callback: CallbackQuery):
    """❌ Деактивация менеджера"""
    manager_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        await repo.deactivate(manager_id)
        manager = await repo.get_by_id(manager_id)

    await callback.answer(f"❌ Менеджер @{manager.username} деактивирован")

    await managers_list(callback)
    logger.info(f"Manager deactivated: ID {manager_id}")


@router.callback_query(F.data.startswith("manager_activate:"))
async def manager_activate(callback: CallbackQuery):
    """✅ Активация менеджера"""
    manager_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        await repo.update(manager_id, {"is_active": True})
        manager = await repo.get_by_id(manager_id)

    await callback.answer(f"✅ Менеджер @{manager.username} активирован")

    await manager_view(callback)
    logger.info(f"Manager activated: ID {manager_id}")


# ===== УДАЛЕНИЕ МЕНЕДЖЕРА =====

@router.callback_query(F.data.startswith("manager_delete:"))
async def manager_delete_start(callback: CallbackQuery):
    """🗑 Начало удаления менеджера"""
    manager_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        manager = await repo.get_by_id(manager_id)

    if not manager:
        await callback.answer("❌ Менеджер не найден", show_alert=True)
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🗑 Удалить", callback_data=f"manager_delete_confirm:{manager_id}")
    keyboard.button(text="❌ Отмена", callback_data=f"manager_view:{manager_id}")
    keyboard.adjust(2)

    try:
        await callback.message.edit_text(
            "⚠️ <b>Удаление менеджера</b>\n\n"
            f"Вы уверены что хотите удалить менеджера @{manager.username}?\n\n"
            "Это действие нельзя отменить!",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "⚠️ <b>Удаление менеджера</b>\n\n"
            f"Вы уверены что хотите удалить менеджера @{manager.username}?\n\n"
            "Это действие нельзя отменить!",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("manager_delete_confirm:"))
async def manager_delete_confirm(callback: CallbackQuery):
    """Подтверждение удаления менеджера"""
    manager_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        manager = await repo.get_by_id(manager_id)
        username = manager.username if manager else "Unknown"
        await repo.delete(manager_id)

    await callback.answer(f"🗑 Менеджер @{username} удалён")

    await managers_list(callback)
    logger.info(f"Manager deleted: ID {manager_id}")


# ===== СТАТИСТИКА МЕНЕДЖЕРА =====

@router.callback_query(F.data.startswith("manager_stats:"))
async def manager_stats(callback: CallbackQuery):
    """📊 Статистика менеджера"""
    manager_id = int(callback.data.split(":")[1])

    async with database.get_session() as session:
        repo = ManagerRepository(session)
        manager = await repo.get_by_id(manager_id)

    if not manager:
        await callback.answer("❌ Менеджер не найден", show_alert=True)
        return

    text = (
        f"📊 <b>Статистика менеджера</b>\n\n"
        f"@{manager.username}\n\n"
        f"📬 Запросов от клиентов: {manager.total_queries}\n"
        f"📦 Оформлено заказов: {manager.total_orders}\n\n"
        f"Последняя активность: {manager.last_active_at.strftime('%d.%m.%Y %H:%M') if manager.last_active_at else '—'}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_manager_detail_keyboard(manager.id),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_manager_detail_keyboard(manager.id),
            parse_mode="HTML",
        )


# ===== ОТМЕНА =====

@router.callback_query(F.data == "manager_cancel")
async def manager_cancel(callback: CallbackQuery, state: FSMContext):
    """❌ Отмена действия"""
    await state.clear()
    await callback.answer("❌ Действие отменено")
    await managers_list(callback)
