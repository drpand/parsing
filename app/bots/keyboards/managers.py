"""
Клавиатуры для управления менеджерами
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional

from app.db.models import Manager


def get_managers_list_keyboard(managers: List[Manager]) -> InlineKeyboardMarkup:
    """Список менеджеров с кнопками управления"""
    builder = InlineKeyboardBuilder()

    for manager in managers:
        status_icon = "✅" if manager.is_active else "❌"
        main_icon = "👑" if manager.is_main else ""
        text = f"{status_icon} {manager.username} {main_icon}".strip()
        builder.button(
            text=text,
            callback_data=f"manager_view:{manager.id}"
        )

    builder.adjust(1)

    # Кнопки управления
    builder.row(
        InlineKeyboardButton(text="➕ Добавить менеджера", callback_data="manager_add"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"),
    )

    return builder.as_markup()


def get_manager_detail_keyboard(manager_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """Детальная информация о менеджере"""
    builder = InlineKeyboardBuilder()

    # Кнопки управления
    if is_active:
        builder.row(
            InlineKeyboardButton(text="📊 Статистика", callback_data=f"manager_stats:{manager_id}"),
        )
        builder.row(
            InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"manager_deactivate:{manager_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"manager_delete:{manager_id}"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Активировать", callback_data=f"manager_activate:{manager_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"manager_delete:{manager_id}"),
        )

    builder.row(
        InlineKeyboardButton(text="🔙 К списку", callback_data="admin_managers_list"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"),
    )

    return builder.as_markup()


def get_add_manager_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для добавления менеджера"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_managers_list"),
    )

    return builder.as_markup()


def get_confirm_add_manager_keyboard(manager_username: str) -> InlineKeyboardMarkup:
    """Подтверждение добавления менеджера"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"manager_confirm_add:{manager_username}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_managers_list"),
    )

    return builder.as_markup()


def get_managers_selection_keyboard(managers: List[Manager], callback_prefix: str = "manager_select") -> InlineKeyboardMarkup:
    """Выбор менеджера из списка (для назначения на заказ)"""
    builder = InlineKeyboardBuilder()

    for manager in managers:
        if manager.is_active:
            main_icon = "👑" if manager.is_main else ""
            builder.button(
                text=f"{manager.username} {main_icon}".strip(),
                callback_data=f"{callback_prefix}:{manager.id}"
            )

    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    )

    return builder.as_markup()
