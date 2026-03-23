from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import Optional, List


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню пользователя (клиента)"""
    builder = ReplyKeyboardBuilder()

    # ✅ Клиентский функционал v1.2.0
    builder.row(
        KeyboardButton(text="🛍 Каталог товаров"),
        KeyboardButton(text="📞 Связаться с менеджером"),
    )
    builder.row(
        KeyboardButton(text="ℹ️ О боте"),
    )

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_manager_keyboard() -> ReplyKeyboardMarkup:
    """
    🔐 Меню менеджера
    ✅ Товары, Поиск, Помощь
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📦 Товары"),
        KeyboardButton(text="🔍 Поиск по ID"),
    )
    builder.row(
        KeyboardButton(text="📞 Помощь"),
    )

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def remove_keyboard():
    """🔐 Удалить клавиатуру (для перехода на Inline)"""
    return ReplyKeyboardRemove()


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    🔐 Админ-панель на Reply-кнопках
    ✅ Возврат к стабильной версии как в v0.6.1
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📦 Добавить товар"),
        KeyboardButton(text="📊 Парсинг категории"),
    )
    builder.row(
        KeyboardButton(text="📢 Авто-постинг"),
        KeyboardButton(text="📦 Товары"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="👥 Менеджеры"),
    )
    builder.row(
        KeyboardButton(text="💾 Кэш"),
        KeyboardButton(text="🗑 Очистить базу"),
    )
    builder.row(
        KeyboardButton(text="🔙 В главное меню"),
    )

    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Кнопки действий с товаром"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🛒 В корзину", callback_data=f"cart_add:{product_id}"),
        InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav_toggle:{product_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Оригинал", url="https://example.com"),  # URL подставится динамически
    )

    return builder.as_markup()


def get_catalog_filters_keyboard(
    current_category: Optional[str] = None,
    current_gender: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Фильтры каталога"""
    builder = InlineKeyboardBuilder()

    # Категории
    categories = [
        ("Все", "all"),
        ("Одежда", "clothing"),
        ("Обувь", "shoes"),
        ("Аксессуары", "accessories"),
    ]

    for name, value in categories:
        prefix = "✅" if current_category == value else "◻️"
        builder.button(
            text=f"{prefix} {name}",
            callback_data=f"catalog_filter:category:{value}"
        )

    builder.adjust(4)

    # Пол
    genders = [
        ("Мужской", "M"),
        ("Женский", "F"),
        ("Унисекс", "U"),
    ]

    for name, value in genders:
        prefix = "✅" if current_gender == value else "◻️"
        builder.button(
            text=f"{prefix} {name}",
            callback_data=f"catalog_filter:gender:{value}"
        )

    builder.adjust(3)

    # Кнопка сброса
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить фильтры", callback_data="catalog_filter:reset"),
    )

    return builder.as_markup()


def get_products_list_keyboard(products: list, page: int = 1) -> InlineKeyboardMarkup:
    """Список товаров с пагинацией"""
    builder = InlineKeyboardBuilder()

    # Кнопки для каждого товара
    for product in products[:10]:
        product_id = product.id if hasattr(product, 'id') else product.get('id')
        title = product.title if hasattr(product, 'title') else product.get('title', 'Товар')
        title_short = title[:30] + "..." if len(title) > 30 else title

        builder.button(
            text=f"🛍 {title_short}",
            callback_data=f"product_view:{product_id}"
        )

    builder.adjust(1)

    # Пагинация
    nav_buttons = []

    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"catalog_page:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"📄 Стр. {page}", callback_data="catalog_page:current")
    )

    nav_buttons.append(
        InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"catalog_page:{page+1}")
    )

    builder.row(*nav_buttons)

    return builder.as_markup()


def get_product_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Кнопки подтверждения для админа (добавление товара)"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_product_confirm:{product_id}"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_product_edit:{product_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_product_cancel"),
    )

    return builder.as_markup()


def get_order_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение заказа"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="order_confirm"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="order_cancel"),
    )

    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back"),
    )
    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str = "page",
) -> InlineKeyboardMarkup:
    """Клавиатура пагинации"""
    builder = InlineKeyboardBuilder()

    buttons = []

    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}:{current_page - 1}")
        )

    buttons.append(
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data=f"{callback_prefix}:current")
    )

    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}:{current_page + 1}")
        )

    builder.row(*buttons)

    return builder.as_markup()
