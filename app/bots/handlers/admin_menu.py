"""
Admin Menu Handler v0.7.0 — Плавная навигация с edit_text
Все переходы изменяют текущее сообщение, а не отправляют новые
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.core.config import settings
from app.utils.logger import logger
from app.bots.keyboards.main import get_admin_keyboard, remove_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="admin_menu")


class AdminStates(StatesGroup):
    """Общие состояния для всех админ-хендлеров"""
    waiting_for_url = State()
    waiting_for_product_url = State()
    waiting_for_category_url = State()
    waiting_for_category_offset = State()
    waiting_for_order_status = State()
    waiting_for_db_confirm = State()


class ParseState(StatesGroup):
    """Состояние для сохранения контекста парсинга категории"""
    parsing_category = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """
    🔐 Главное меню администратора
    ✅ УДАЛЯЕТ Reply клавиатуру и показывает Inline
    """
    if message.from_user.id not in settings.admin_ids:
        await message.answer("🚫 <b>Доступ запрещён</b>", parse_mode="HTML")
        return

    logger.info(f"Admin {message.from_user.id} opened admin panel")

    # 🔐 УДАЛЯЕМ старую Reply клавиатуру
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """
    🔙 Возврат в главное меню админки
    ✅ Возвращает Reply клавиатуру (как в v0.6.1)
    """
    await callback.answer()

    # 🔐 ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ С Reply клавиатурой
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_keyboard(),  # ReplyKeyboardMarkup
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_products")
async def admin_products_menu(callback: CallbackQuery):
    """
    📦 Меню товаров — перенаправление на новый список
    ✅ ИЗМЕНЕНО: Прямой переход к products_router
    """
    # 🔐 ПЕРЕНАПРАВЛЯЕМ НА НОВЫЙ СПИСОК ТОВАРОВ
    from app.bots.handlers.products import show_products_page
    await show_products_page(callback, page=1)


@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu(callback: CallbackQuery, state: FSMContext):
    """
    ⚙️ Меню настроек
    ✅ ИЗМЕНЕНО: edit_text + кнопка Назад
    """
    await state.clear()  # 🔐 СБРОС СОСТОЯНИЯ
    await callback.answer()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⚙️ Настройки бота", callback_data="settings_main")
    keyboard.button(text="🔙 Назад", callback_data="admin_back")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            "Выберите раздел:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "⚙️ <b>Настройки</b>\n\n"
            "Выберите раздел:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin_parse")
async def admin_parse_menu(callback: CallbackQuery):
    """
    🔍 Меню парсинга
    ✅ ИЗМЕНЕНО: edit_text + кнопка Назад
    """
    await callback.answer()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔍 Парсинг товара", callback_data="parse_product")
    keyboard.button(text="📂 Парсинг категории", callback_data="parse_category")
    keyboard.button(text="🔙 Назад", callback_data="admin_back")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            "🔍 <b>Парсинг</b>\n\n"
            "Выберите тип:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "🔍 <b>Парсинг</b>\n\n"
            "Выберите тип:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin_orders")
async def admin_orders_menu(callback: CallbackQuery):
    """
    📋 Меню заказов
    ✅ ИЗМЕНЕНО: edit_text + кнопка Назад
    """
    await callback.answer()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📋 Просмотр заказов", callback_data="orders_view")
    keyboard.button(text="🔙 Назад", callback_data="admin_back")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            "📋 <b>Заказы</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "📋 <b>Заказы</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin_db")
async def admin_db_menu(callback: CallbackQuery):
    """
    🗄 Меню базы данных
    ✅ ИЗМЕНЕНО: edit_text + кнопка Назад
    """
    await callback.answer()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🗄 Управление БД", callback_data="db_manage")
    keyboard.button(text="🔙 Назад", callback_data="admin_back")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            "🗄 <b>База данных</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "🗄 <b>База данных</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_menu(callback: CallbackQuery):
    """
    📢 Меню рассылки
    ✅ ИЗМЕНЕНО: edit_text + кнопка Назад
    """
    await callback.answer()

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📢 Рассылка", callback_data="broadcast_send")
    keyboard.button(text="🔙 Назад", callback_data="admin_back")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            "📢 <b>Рассылка</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "📢 <b>Рассылка</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin_managers")
async def admin_managers_menu(callback: CallbackQuery):
    """
    👥 Меню менеджеров — перенаправление на новый список
    ✅ ИЗМЕНЕНО: Прямой переход к managers_router
    """
    from app.bots.handlers.admin_managers import managers_list
    await managers_list(callback)


# ===== 🔐 ОБРАБОТКА РЕПЛИ-КНОПОК =====

@router.message(F.text == "👥 Менеджеры")
async def managers_menu_text(message: Message, state: FSMContext):
    """
    🔐 Меню менеджеров (текстовая команда)
    ✅ Вызывается при нажатии кнопки "👥 Менеджеры"
    """
    await state.clear()  # 🔐 СБРОС СОСТОЯНИЯ

    from app.bots.handlers.admin_managers import managers_list

    # Создаём фейковый callback для совместимости
    class FakeCallback:
        def __init__(self, msg):
            self.message = msg
            self.from_user = msg.from_user

        async def answer(self):
            pass

    fake_callback = FakeCallback(message)
    await managers_list(fake_callback)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "❌ <b>Действие отменено</b>\n\n"
        "Выберите команду или используйте меню.",
        parse_mode="HTML",
    )
    logger.info(f"Admin {message.from_user.id} cancelled action")



