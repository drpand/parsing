"""
Клавиатуры для товаров (админка)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_products_list_keyboard(
    products: list,
    current_page: int,
    total_pages: int,
    has_next: bool = False,
    has_prev: bool = False
) -> InlineKeyboardMarkup:
    """
    Клавиатура списка товаров (вертикальный список inline кнопок)
    
    Args:
        products: Список товаров для отображения
        current_page: Текущая страница
        total_pages: Всего страниц
        has_next: Есть ли следующая
        has_prev: Есть ли предыдущая
    """
    builder = InlineKeyboardBuilder()
    
    # 🔐 КНОПКИ-ТОВАРЫ (списком, только название)
    for idx, product in enumerate(products, 1):
        # Статус наличия
        stock_icon = "✅" if product.in_stock else "❌"
        
        # Текст кнопки (только название + ID)
        button_text = f"{stock_icon} {product.title[:35]}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"product_view_{product.id}"
            )
        )
    
    # 🔐 ПАГИНАЦИЯ (отдельно после товаров)
    builder.row(
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"products_page_{current_page - 1}" if has_prev else "empty"
        ),
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="empty"
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"products_page_{current_page + 1}" if has_next else "empty"
        )
    )
    
    # Ввести номер страницы
    builder.row(
        InlineKeyboardButton(
            text="🔢 Ввести номер",
            callback_data="products_enter_page"
        )
    )
    
    # В админку
    builder.row(
        InlineKeyboardButton(
            text="🔙 В админку",
            callback_data="admin_menu"
        )
    )
    
    return builder.as_markup()


def get_product_card_keyboard(product_id: int, is_admin: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура карточки товара
    
    Args:
        product_id: ID товара
        is_admin: Если True — показывать кнопки админа
    """
    builder = InlineKeyboardBuilder()
    
    if is_admin:
        # Кнопки админа
        builder.row(
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"product_edit_{product_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📤 В канал",
                callback_data=f"product_post_{product_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"product_delete_{product_id}"
            )
        )
    
    # Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к списку",
            callback_data="admin_products"
        )
    )
    
    return builder.as_markup()


def get_product_edit_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура редактирования товара
    """
    builder = InlineKeyboardBuilder()
    
    # Поля для редактирования
    builder.row(
        InlineKeyboardButton(
            text="📝 Название",
            callback_data=f"product_edit_title_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💵 Цена (INR)",
            callback_data=f"product_edit_price_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Старая цена",
            callback_data=f"product_edit_original_price_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 Наличие",
            callback_data=f"product_edit_stock_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Описание",
            callback_data=f"product_edit_description_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖼 Изображения",
            callback_data=f"product_edit_images_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏷 Категория",
            callback_data=f"product_edit_category_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎨 Цвет",
            callback_data=f"product_edit_color_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📏 Размеры",
            callback_data=f"product_edit_sizes_{product_id}"
        )
    )
    
    # Кнопки навигации
    builder.row(
        InlineKeyboardButton(
            text="💾 Сохранить и выйти",
            callback_data=f"product_view_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"product_view_{product_id}"
        )
    )
    
    return builder.as_markup()


def get_product_delete_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура удаления товара (подтверждение)
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="❗️ Да, удалить",
            callback_data=f"product_delete_confirm_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"product_view_{product_id}"
        )
    )
    
    return builder.as_markup()


def get_product_images_keyboard(product_id: int, images: list) -> InlineKeyboardMarkup:
    """
    Клавиатура управления изображениями
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки для каждого изображения
    for idx, img_url in enumerate(images[:10]):  # Максимум 10
        builder.row(
            InlineKeyboardButton(
                text=f"🖼 Фото {idx + 1}",
                url=img_url
            )
        )
    
    # Кнопки управления
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить URL",
            callback_data=f"product_edit_add_image_{product_id}"
        )
    )
    
    if len(images) > 1:
        builder.row(
            InlineKeyboardButton(
                text="➖ Удалить последнее",
                callback_data=f"product_edit_remove_image_{product_id}"
            )
        )
    
    # Назад
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"product_edit_{product_id}"
        )
    )
    
    return builder.as_markup()
