"""
Admin Settings Handler v0.7.0 — Курс валют + плавная навигация
💰 Наценка % | 💱 Курс USD→INR | 💱 Курс USD→RUB | 📦 Лимит парсинга | ⏱ Интервал автопостинга | 🚚 Доставка
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select
from app.db.database import database
from app.db.models import Setting
from app.core.config import settings
from app.utils.logger import logger

router = Router(name="admin_settings")


class SettingsStates(StatesGroup):
    """Состояния для настроек"""
    waiting_for_margin = State()
    waiting_for_usd_inr = State()
    waiting_for_usd_rub = State()
    waiting_for_limit = State()
    waiting_for_interval = State()
    waiting_for_post_interval = State()  # 🔐 Интервал автопостинга
    waiting_for_manager = State()  # 🔐 Менеджер
    waiting_for_delivery_fixed = State()
    waiting_for_delivery_percent = State()


async def get_setting_value(key: str, default: float) -> float:
    """Получить значение настройки из БД"""
    async with database.get_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar()

        if setting:
            try:
                return float(setting.value)
            except (ValueError, TypeError):
                return default
        return default


async def save_setting_value(key: str, value: float) -> bool:
    """Сохранить значение настройки в БД"""
    try:
        async with database.get_session() as session:
            result = await session.execute(select(Setting).where(Setting.key == key))
            setting = result.scalar()

            if setting:
                setting.value = str(value)
            else:
                setting = Setting(key=key, value=str(value))
                session.add(setting)

            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to save setting {key}: {e}")
        return False


# ===== ГЛАВНОЕ МЕНЮ НАСТРОЕК =====

@router.message(F.text == "⚙️ Настройки")
async def admin_settings_menu_text(message: Message, state: FSMContext):
    """
    🔐 Меню настроек (текстовая команда)
    ✅ Вызывается при нажатии кнопки "⚙️ Настройки"
    """
    await state.clear()  # 🔐 СБРОС СОСТОЯНИЯ
    await admin_settings_menu_callback(message, state)


@router.callback_query(F.data == "settings_main")
async def admin_settings_menu_callback(callback: CallbackQuery | Message, state: FSMContext):
    """
    🔐 Меню настроек с курсом валют
    ✅ ИЗМЕНЕНО: edit_text + кнопка Назад + курс INR→RUB
    """
    # Отвечаем на callback если это CallbackQuery
    if isinstance(callback, CallbackQuery):
        await callback.answer()

    await state.clear()

    # Получаем текущие значения из БД (актуальные значения)
    margin = await get_setting_value("margin_percent", 25.0)
    usd_inr = await get_setting_value("usd_inr", 91.0)
    usd_rub = await get_setting_value("usd_rub", 80.0)
    limit = await get_setting_value("parse_limit", 10)
    interval = await get_setting_value("parse_interval", 2)
    post_interval = await get_setting_value("post_interval", 60)  # 🔐 Интервал автопостинга
    delivery_fixed = await get_setting_value("delivery_fixed", 500)
    delivery_percent = await get_setting_value("delivery_percent", 5.0)

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="💰 Наценка %", callback_data="settings_margin"),
    )
    builder.row(
        InlineKeyboardButton(text="💱 Курс USD→INR", callback_data="settings_usd_inr"),
        InlineKeyboardButton(text="💱 Курс USD→RUB", callback_data="settings_usd_rub"),
    )
    builder.row(
        InlineKeyboardButton(text="📦 Лимит парсинга", callback_data="settings_limit"),
    )
    builder.row(
        InlineKeyboardButton(text="📬 Интервал автопостинга", callback_data="settings_post_interval"),
    )
    builder.row(
        InlineKeyboardButton(text="🚚 Доставка", callback_data="settings_delivery"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"),
    )

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"💰 <b>Наценка:</b> {margin}%\n"
        f"💱 <b>Курс USD→INR:</b> {usd_inr}\n"
        f"💱 <b>Курс USD→RUB:</b> {usd_rub}\n"
        f"📦 <b>Лимит парсинга:</b> {int(limit)} товаров\n"
        f"📬 <b>Интервал автопостинга:</b> {int(post_interval)} мин\n"
        f"🚚 <b>Доставка:</b> {delivery_fixed}₽ + {delivery_percent}%\n\n"
        "💡 <i>Управление менеджерами в разделе «👥 Менеджеры»</i>\n\n"
        "Выберите настройку:"
    )

    # Отправляем сообщение
    if isinstance(callback, CallbackQuery):
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await callback.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ===== НАЦЕНКА =====

@router.callback_query(F.data == "settings_margin")
async def settings_margin_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование наценки"""
    await callback.answer()

    current = await get_setting_value("margin_percent", settings.margin_percent)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="settings_main")
    keyboard.adjust(1)

    try:
        await callback.message.edit_text(
            f"💰 <b>Наценка</b>\n\n"
            f"Текущая наценка: <b>{int(current)}%</b>\n\n"
            "Отправьте процент наценки (1-100):\n"
            "Например: <code>30</code>",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            f"💰 <b>Наценка</b>\n\n"
            f"Текущая наценка: <b>{int(current)}%</b>\n\n"
            "Отправьте процент наценки (1-100):\n"
            "Например: <code>30</code>",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )

    await state.set_state( SettingsStates.waiting_for_margin)


@router.message(SettingsStates.waiting_for_margin)
async def settings_margin_save(message: Message, state: FSMContext):
    """Сохранение наценки"""
    try:
        new_margin = int(message.text.strip())

        if not 1 <= new_margin <= 100:
            await message.answer("❌ Наценка должна быть от 1 до 100%")
            return

        success = await save_setting_value("margin_percent", new_margin)

        if success:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад в настройки", callback_data="settings_main")

            await message.answer(
                f"✅ <b>Наценка обновлена!</b>\n\n"
                f"Было: {settings.margin_percent}%\n"
                f"Стало: {new_margin}%\n\n"
                "Нажмите кнопку ниже чтобы вернуться:",
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
            )
            logger.info(f"Margin updated: {new_margin}%")
        else:
            await message.answer("❌ Ошибка при сохранении в БД")

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите целое число (например: 30)")


# ===== ИНТЕРВАЛ АВТОПОСТИНГА =====

@router.callback_query(F.data == "settings_post_interval")
async def settings_post_interval_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование интервала автопостинга"""
    await callback.answer()

    current = await get_setting_value("post_interval", 60)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="settings_main")
    keyboard.button(text="🔙 Назад", callback_data="settings_main")
    keyboard.adjust(2)

    await callback.message.edit_text(
        f"📬 <b>Интервал автопостинга</b>\n\n"
        f"Текущий интервал: <b>{int(current)} мин</b>\n\n"
        "Как часто публиковать посты в канал?\n\n"
        "Примеры:\n"
        "• <code>30</code> — каждые 30 минут\n"
        "• <code>60</code> — каждый час\n"
        "• <code>180</code> — каждые 3 часа\n\n"
        "Отправьте число (минут):",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state( SettingsStates.waiting_for_post_interval)


@router.message(SettingsStates.waiting_for_post_interval, F.text.isdigit())
async def settings_post_interval_save(message: Message, state: FSMContext):
    """Сохранение интервала автопостинга"""
    new_interval = int(message.text.strip())

    if new_interval < 5 or new_interval > 1440:
        await message.answer("❌ Интервал должен быть от 5 до 1440 минут (от 5 мин до 24 часов)")
        return

    # 🔐 Получаем старое значение из БД
    old_interval = await get_setting_value("post_interval", 60)

    success = await save_setting_value("post_interval", new_interval)

    if success:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад в настройки", callback_data="settings_main")

        await message.answer(
            f"✅ <b>Интервал автопостинга обновлен!</b>\n\n"
            f"Было: {int(old_interval)} мин\n"
            f"Стало: {new_interval} мин\n\n"
            "<i>Планировщик будет перезапущен автоматически.</i>\n\n"
            "Нажмите кнопку ниже чтобы вернуться:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
        logger.info(f"Post interval updated: {new_interval} min")
    else:
        await message.answer("❌ Ошибка при сохранении в БД")

    await state.clear()


@router.message(SettingsStates.waiting_for_post_interval)
async def settings_post_interval_invalid(message: Message):
    """Неверное значение интервала"""
    await message.answer("❌ Введите число (например: 60)")


# ===== КУРС USD→INR =====

@router.callback_query(F.data == "settings_usd_inr")
async def settings_usd_inr_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование курса USD→INR"""
    await callback.answer()

    current = await get_setting_value("usd_inr", settings.usd_inr)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="settings_main")
    keyboard.button(text="🔙 Назад", callback_data="settings_main")
    keyboard.adjust(2)

    await callback.message.edit_text(
        f"💱 <b>Курс USD→INR</b>\n\n"
        f"Текущий курс: <b>{current}</b>\n\n"
        "Сколько индийских рупий за 1 доллар?\n\n"
        "Отправьте число:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state(SettingsStates.waiting_for_usd_inr)


@router.message(SettingsStates.waiting_for_usd_inr)
async def settings_usd_inr_save(message: Message, state: FSMContext):
    """Сохранение курса USD→INR"""
    try:
        new_rate = float(message.text.strip().replace(',', '.'))

        if new_rate <= 0:
            await message.answer("❌ Курс должен быть больше 0")
            return

        # 🔐 Получаем старое значение из БД (не из .env!)
        old_rate = await get_setting_value("usd_inr", settings.usd_inr)

        success = await save_setting_value("usd_inr", new_rate)

        if success:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад в настройки", callback_data="settings_main")

            # 🔐 ОТПРАВЛЯЕМ СООБЩЕНИЕ С КНОПКОЙ "НАЗАД"
            await message.answer(
                f"✅ <b>Курс USD→INR обновлен!</b>\n\n"
                f"Было: {old_rate}\n"
                f"Стало: {new_rate}\n\n"
                "Нажмите кнопку ниже чтобы вернуться:",
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
            )
            logger.info(f"USD→INR updated: {new_rate}")
        else:
            await message.answer("❌ Ошибка при сохранении в БД")

        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число (например: 83.5)")


# ===== КУРС USD→RUB =====

@router.callback_query(F.data == "settings_usd_rub")
async def settings_usd_rub_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование курса USD→RUB"""
    await callback.answer()

    current = await get_setting_value("usd_rub", settings.usd_rub)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="settings_main")
    keyboard.button(text="🔙 Назад", callback_data="settings_main")
    keyboard.adjust(2)

    await callback.message.edit_text(
        f"💱 <b>Курс USD→RUB</b>\n\n"
        f"Текущий курс: <b>{current}</b>\n\n"
        "Сколько рублей за 1 доллар?\n\n"
        "Отправьте число:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state(SettingsStates.waiting_for_usd_rub)


@router.message(SettingsStates.waiting_for_usd_rub)
async def settings_usd_rub_save(message: Message, state: FSMContext):
    """Сохранение курса USD→RUB"""
    try:
        new_rate = float(message.text.strip().replace(',', '.'))

        if new_rate <= 0:
            await message.answer("❌ Курс должен быть больше 0")
            return

        # 🔐 Получаем старое значение из БД (не из .env!)
        old_rate = await get_setting_value("usd_rub", settings.usd_rub)

        success = await save_setting_value("usd_rub", new_rate)

        if success:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад в настройки", callback_data="settings_main")

            await message.answer(
                f"✅ <b>Курс USD→RUB обновлен!</b>\n\n"
                f"Было: {old_rate}\n"
                f"Стало: {new_rate}\n\n"
                "Нажмите кнопку ниже чтобы вернуться:",
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
            )
            logger.info(f"USD→RUB updated: {new_rate}")
        else:
            await message.answer("❌ Ошибка при сохранении в БД")

        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число (например: 92.0)")


# ===== ЛИМИТ ПАРСИНГА =====

@router.callback_query(F.data == "settings_limit")
async def settings_limit_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование лимита парсинга"""
    await callback.answer()

    current = await get_setting_value("parse_limit", 10)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="settings_main")
    keyboard.button(text="🔙 Назад", callback_data="settings_main")
    keyboard.adjust(2)

    await callback.message.edit_text(
        f"📦 <b>Лимит парсинга</b>\n\n"
        f"Текущий лимит: <b>{int(current)} товаров</b>\n\n"
        "Сколько товаров парсить за один раз?\n\n"
        "Примеры:\n"
        "• <code>10</code> — быстро\n"
        "• <code>30</code> — нормально\n"
        "• <code>50</code> — много\n\n"
        "Отправьте число:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state( SettingsStates.waiting_for_limit)


@router.message(SettingsStates.waiting_for_limit, F.text.isdigit())
async def settings_limit_save(message: Message, state: FSMContext):
    """Сохранение лимита парсинга"""
    new_limit = int(message.text.strip())

    if new_limit < 1 or new_limit > 100:
        await message.answer("❌ Лимит должен быть от 1 до 100 товаров")
        return

    success = await save_setting_value("parse_limit", new_limit)

    if success:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад в настройки", callback_data="settings_main")

        await message.answer(
            f"✅ <b>Лимит парсинга обновлен!</b>\n\n"
            f"Было: 30\n"
            f"Стало: {new_limit}\n\n"
            "Нажмите кнопку ниже чтобы вернуться:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
        )
        logger.info(f"Parse limit updated: {new_limit}")
    else:
        await message.answer("❌ Ошибка при сохранении в БД")

    await state.clear()


@router.message(SettingsStates.waiting_for_limit)
async def settings_limit_invalid(message: Message):
    """Неверное значение лимита"""
    await message.answer("❌ Введите число (например: 10)")


# ===== ДОСТАВКА =====

@router.callback_query(F.data == "settings_delivery")
async def settings_delivery_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование доставки"""
    await callback.answer()

    fixed = await get_setting_value("delivery_fixed", settings.delivery_fixed)
    percent = await get_setting_value("delivery_percent", settings.delivery_percent)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Отмена", callback_data="settings_main")
    keyboard.button(text="🔙 Назад", callback_data="settings_main")
    keyboard.adjust(2)

    await callback.message.edit_text(
        f"🚚 <b>Доставка</b>\n\n"
        f"Текущая доставка:\n"
        f"• Фикс: <b>{int(fixed)}₽</b>\n"
        f"• Процент: <b>{percent}%</b>\n\n"
        "Отправьте фиксированную часть (₽):",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state( SettingsStates.waiting_for_delivery_fixed)


@router.message(SettingsStates.waiting_for_delivery_fixed, F.text.isdigit())
async def settings_delivery_fixed_save(message: Message, state: FSMContext):
    """Сохранение фиксированной доставки"""
    new_fixed = int(message.text.strip())

    if new_fixed < 0:
        await message.answer("❌ Фикс не может быть отрицательным")
        return

    success = await save_setting_value("delivery_fixed", new_fixed)

    if success:
        await message.answer(
            f"✅ <b>Фиксированная доставка обновлена!</b>\n\n"
            f"Стало: {new_fixed}₽\n\n"
            "Теперь отправьте процент (%):",
            parse_mode="HTML",
        )
        logger.info(f"Delivery fixed updated: {new_fixed}")
        await state.set_state(SettingsStates.waiting_for_delivery_percent)
    else:
        await message.answer("❌ Ошибка при сохранении в БД")


@router.message(SettingsStates.waiting_for_delivery_percent, F.text.replace(',', '.').replace('.', '', 1).isdigit())
async def settings_delivery_percent_save(message: Message, state: FSMContext):
    """Сохранение процента доставки"""
    try:
        new_percent = float(message.text.strip().replace(',', '.'))

        if new_percent < 0 or new_percent > 100:
            await message.answer("❌ Процент должен быть от 0 до 100")
            return

        success = await save_setting_value("delivery_percent", new_percent)

        if success:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад в настройки", callback_data="settings_main")

            await message.answer(
                f"✅ <b>Доставка обновлена!</b>\n\n"
                f"Фикс: {int(await get_setting_value('delivery_fixed', 500))}₽\n"
                f"Процент: {new_percent}%\n\n"
                "Нажмите кнопку ниже чтобы вернуться:",
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
            )
            logger.info(f"Delivery percent updated: {new_percent}%")
        else:
            await message.answer("❌ Ошибка при сохранении в БД")

        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число (например: 5.0)")


@router.message(SettingsStates.waiting_for_delivery_fixed)
async def settings_delivery_fixed_invalid(message: Message):
    """Неверное значение фикса"""
    await message.answer("❌ Введите число (например: 500)")


@router.message(SettingsStates.waiting_for_delivery_percent)
async def settings_delivery_percent_invalid(message: Message):
    """Неверное значение процента"""
    await message.answer("❌ Введите число (например: 5.0)")


# ===== МЕНЕДЖЕР =====
# 🔐 УДАЛЕНО: Перенесено в раздел "👥 Менеджеры" (admin_managers.py)
# Теперь управление менеджерами только через отдельный раздел

@router.callback_query(F.data == "settings_manager")
async def settings_manager_edit(callback: CallbackQuery, state: FSMContext):
    """🔐 Перенаправление в раздел Менеджеры"""
    await callback.answer("ℹ️ Управление менеджерами перенесено в раздел «👥 Менеджеры»", show_alert=True)

    # Перенаправляем в раздел менеджеров
    from app.bots.handlers.admin_managers import managers_list
    await managers_list(callback)


# ===== НАЗАД В ГЛАВНОЕ МЕНЮ =====

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """🔙 Возврат в главное меню админки"""
    if callback.from_user.id not in settings.admin_ids:
        return

    # 🔐 ЗАНОВО ЧИТАЕМ ВСЕ ЗНАЧЕНИЯ ИЗ БД (актуальные значения)
    margin = await get_setting_value("margin_percent", 25.0)
    usd_inr = await get_setting_value("usd_inr", 91.0)
    usd_rub = await get_setting_value("usd_rub", 80.0)
    limit = await get_setting_value("parse_limit", 10)
    interval = await get_setting_value("parse_interval", 2)
    post_interval = await get_setting_value("post_interval", 60)
    delivery_fixed = await get_setting_value("delivery_fixed", 500)
    delivery_percent = await get_setting_value("delivery_percent", 5.0)

    from app.bots.keyboards.main import get_admin_keyboard

    await callback.answer()

    try:
        await callback.message.edit_text(
            "🔧 <b>Панель администратора</b>\n\n"
            "📊 <b>Управление:</b>\n"
            "• Добавление товаров через URL\n"
            "• Управление каталогом\n"
            "• Просмотр заказов\n\n"
            "👇 Выберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "🔧 <b>Панель администратора</b>\n\n"
            "📊 <b>Управление:</b>\n"
            "• Добавление товаров через URL\n"
            "• Управление каталогом\n"
            "• Просмотр заказов\n\n"
            "👇 Выберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
