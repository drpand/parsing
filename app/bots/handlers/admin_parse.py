"""
Admin Parse Handler - Парсинг товаров и категорий
"""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.core.config import settings
from app.db.database import database
from app.db.repositories import ProductRepository
from app.utils.logger import logger
from app.utils.helpers import calculate_price_rub, safe_html
from app.bots.handlers.admin_menu import AdminStates, ParseState
from app.db.models import Product

router = Router(name="admin_parse")


@router.message(F.text == "/cancel")
async def cmd_cancel_parse(message: Message, state: FSMContext):
    """Отмена парсинга"""
    current_state = await state.get_state()
    if current_state in [AdminStates.waiting_for_product_url, AdminStates.waiting_for_category_url]:
        await state.clear()
        await message.answer("❌ <b>Отменено</b>\n\nВыберите действие:", parse_mode="HTML")


@router.message(F.text == "📦 Добавить товар")
async def admin_add_product(message: Message, state: FSMContext):
    """Добавление товара по URL"""
    await state.clear()  # 🔐 ПРИНУДИТЕЛЬНЫЙ СБРОС ЛЮБОГО СОСТОЯНИЯ
    await state.set_state(AdminStates.waiting_for_product_url)

    await message.answer(
        "📦 <b>Добавление товара</b>\n\n"
        "Отправьте URL страницы товара:\n"
        "• Zara (zara.com)\n"
        "• Myntra (myntra.com)\n"
        "• Ajio (ajio.com)\n\n"
        "❌ <i>Отмена: /cancel</i>",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_product_url, F.text.startswith("http"))
async def process_add_product(message: Message, state: FSMContext):
    """Обработка URL товара - сначала проверка дублей, потом парсинг"""
    url = message.text.strip()

    # Проверяем не категория ли это
    if any(keyword in url.lower() for keyword in ['/women-', '/men-', '/kids-', '/dresses', '/shirts', '/shoes', '/category', '/c/']):
        await message.answer(
            f"⚠️ <b>Это похоже на категорию!</b>\n\n"
            f"🔗 <code>{url[:60]}...</code>\n\n"
            f"💡 <b>Совет:</b>\n"
            f"Для парсинга КАТЕГОРИИ используйте:\n"
            f"📊 <b>Парсинг категории</b>\n\n"
            f"Это быстрее и добавит сразу много товаров!",
            parse_mode="HTML",
        )
        # Не очищаем состояние - пусть юзер отправит правильный URL товара
        return

    # Сначала проверяем дубликат в БД
    async with database.get_session() as session:
        product_repo = ProductRepository(session)
        existing = await product_repo.get_by_url(url)

        if existing:
            await message.answer(
                f"⚠️ <b>Уже существует в базе!</b>\n\n"
                f"🛍 {existing.title[:50]}...\n"
                f"💰 {existing.price_rub:,.0f} ₽\n"
                f"🆔 ID: {existing.id}\n\n"
                f"<i>Отправьте другой URL или используйте /cancel</i>",
                parse_mode="HTML",
            )
            await state.clear()
            return

    # Дубликата нет - парсим
    await message.answer(
        "⏳ <b>Начинаю парсинг...</b>\n\n"
        f"🔗 <code>{url[:60]}...</code>\n"
        f"<i>Это займёт 20-40 секунд.</i>",
        parse_mode="HTML",
    )

    try:
        from app.services.selenium_service import selenium_stealth_service

        # 1️⃣ ПЫТАЕМСЯ ЧЕРЕЗ DOM (быстро, для Zara/Myntra)
        logger.info(f"Trying DOM parse: {url}")

        # 🔐 parse_product — синхронный метод (НЕ await!)
        product_data = selenium_stealth_service.parse_product(url)

        # 2️⃣ ЕСЛИ DOM НЕ СРАБОТАЛ → AI (для Nykaa/Ajio)
        if not product_data:
            logger.info("⚠️ DOM failed, trying AI parser...")
            await message.answer(
                "🤖 <b>Обычный парсинг не сработал...</b>\n\n"
                "<i>Запускаю AI-агента (30-60 сек).</i>",
                parse_mode="HTML",
            )

            # Собираем контент
            raw = await selenium_stealth_service.get_raw_content(url)

            if not raw:
                await message.answer("❌ Ошибка сбора данных", parse_mode="HTML")
                await state.clear()
                return

            # AI анализирует
            from app.services.openrouter_service import OpenRouterService
            openrouter = OpenRouterService()

            ai_data = await openrouter.extract_universal(
                url=url,
                page_text=raw['text'],
                images=raw['images']
            )

            if not ai_data:
                await message.answer("❌ AI не смог распарсить", parse_mode="HTML")
                await state.clear()
                return

            # Конвертируем в формат product_data
            product_data = {
                "source_url": url,
                "title": ai_data.get('title', 'Unknown')[:200],
                "price_inr": ai_data.get('price_inr', 0),
                "original_price_inr": ai_data.get('original_price_inr'),
                "discount_percent": ai_data.get('discount_percent', 0),
                "category": ai_data.get('category', 'other'),
                "color": ai_data.get('color'),
                "in_stock": ai_data.get('in_stock', True),
                "images": ai_data.get('image_urls', []),
                "description": ai_data.get('description_ru', ''),
            }

            logger.info(f"✅ AI parser success: {product_data['title'][:50]}")

        if not product_data:
            await message.answer("❌ <b>Ошибка парсинга</b>\n\nПопробуйте другой URL.", parse_mode="HTML")
            await state.clear()
            return

        # Рассчитываем цену
        price_rub = calculate_price_rub(
            price_inr=product_data['price_inr'],
            usd_inr=settings.usd_inr,
            usd_rub=settings.usd_rub,
            margin_percent=settings.margin_percent,
            delivery_fixed=settings.delivery_fixed,
            delivery_percent=settings.delivery_percent,
        )

        # Сохраняем
        async with database.get_session() as session:
            product_repo = ProductRepository(session)

            # 🛡️ WHITELISTING: Оставляем ТОЛЬКО поля которые есть в БД
            valid_columns = Product.__table__.columns.keys()
            allowed_keys = set(valid_columns + ['images'])  # images тоже разрешаем

            clean_data = {
                key: value
                for key, value in product_data.items()
                if key in allowed_keys
            }

            # 🔐 ОТЛАДКА: проверяем что в clean_data
            logger.debug(f"clean_data keys: {list(clean_data.keys())}")
            logger.debug(f"valid_columns: {valid_columns}")

            try:
                product = await product_repo.create({
                    **clean_data,
                    'price_rub': price_rub,
                    'is_on_sale': product_data.get('discount_percent', 0) > 0,  # 🔐 БЕРЁМ ИЗ product_data
                })
            except Exception as create_error:
                logger.error(f"Product create error: {create_error}")
                logger.error(f"Data: {clean_data}")
                raise

        await message.answer(
            f"✅ <b>Товар добавлен!</b>\n\n"
            f"🛍 {product_data['title'][:50]}...\n"
            f"💰 {price_rub:,.0f} ₽ (₹{product_data['price_inr']:,.0f})\n"
            f"🆔 ID: {product.id}",
            parse_mode="HTML",
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Add product error: {e}")
        await message.answer(f"❌ <b>Ошибка</b>\n\n<i>{safe_html(str(e)[:200])}</i>", parse_mode="HTML")
        await state.clear()


@router.message(F.text == "📊 Парсинг категории")
async def admin_parse_category(message: Message, state: FSMContext):
    """Парсинг категории"""
    await state.clear()  # 🔐 ПРИНУДИТЕЛЬНЫЙ СБРОС ЛЮБОГО СОСТОЯНИЯ
    await state.set_state(AdminStates.waiting_for_category_url)

    # 🔐 ДОБАВЛЯЕМ КНОПКУ "🔙 НАЗАД"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_back")

    await message.answer(
        "📊 <b>Парсинг категории</b>\n\n"
        "Отправьте URL страницы категории:\n"
        "• https://www.myntra.com/women-dresses\n"
        "• https://www.zara.com/in/en/man-l534.html\n\n"
        "<i>Или нажмите кнопку ниже для отмены</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_category_url, F.text.startswith("http"))
async def process_parse_category(message: Message, state: FSMContext):
    """Обработка парсинга категории с запросом offset"""
    url = message.text.strip()

    # 🔐 СБРОС СОСТОЯНИЯ ПЕРЕД НОВЫМ ПАРСИНГОМ
    await state.set_data({
        "category_url": url,
        "current_offset": 0  # Сбрасываем offset
    })

    # 🔐 ЗАПРОС OFFSET: Спрашиваем сколько товаров пропустить
    # 🔐 ДОБАВЛЯЕМ КНОПКУ "🔙 НАЗАД"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_back")

    await message.answer(
        "📍 <b>Настройка смещения (offset)</b>\n\n"
        "Сколько товаров нужно пропустить перед началом парсинга?\n\n"
        "Примеры:\n"
        "• 0 — парсить с начала (по умолчанию)\n"
        "• 20 — пропустить первые 20 товаров\n"
        "• 40 — пропустить первые 40 товаров\n\n"
        "<i>Отправьте число или нажмите кнопку ниже для отмены</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    # Переходим в состояние ожидания offset
    await state.set_state(AdminStates.waiting_for_category_offset)


@router.message(AdminStates.waiting_for_category_offset, F.text.isdigit())
async def process_category_offset(message: Message, state: FSMContext):
    """Обработка offset и запуск парсинга"""
    offset = int(message.text.strip())
    data = await state.get_data()
    url = data.get('category_url')

    if not url:
        await message.answer("❌ <b>Ошибка</b>\n\nURL категории не найден. Начните заново.")
        await state.clear()
        return

    # 🔐 БЕРЁМ ЛИМИТ ИЗ НАСТРОЕК БД
    from app.db.database import database
    from app.db.repositories import SettingRepository

    async with database.get_session() as session:
        settings_repo = SettingRepository(session)
        parse_limit_setting = await settings_repo.get("parse_limit")
        parse_limit = int(parse_limit_setting) if parse_limit_setting else 10

    # 🔐 СОХРАНЯЕМ СОСТОЯНИЕ ПАРСИНГА
    await state.set_state(ParseState.parsing_category)
    await state.update_data(
        category_url=url,
        current_offset=offset,
        max_products=parse_limit
    )

    await message.answer(
        "⏳ <b>Начинаю парсинг категории...</b>\n\n"
        f"🔗 <code>{url[:60]}...</code>\n"
        f"📍 Offset: {offset} (пропустить первые {offset} товаров)\n"
        f"<i>Это займёт 2-3 минуты (до {parse_limit} товаров).</i>",
        parse_mode="HTML",
    )

    try:
        from app.services.selenium_service import selenium_stealth_service

        # 🔐 ПРОВЕРКА: Если offset слишком большой, начинаем с 0
        logger.info(f"Starting parse with offset={offset}, max_products={parse_limit}")

        # 🔐 ПАРСИМ С OFFSET
        products_data = await selenium_stealth_service.parse_category(
            url=url,
            max_products=parse_limit,
            offset=offset
        )

        # 🔐 ПРОВЕРКА: Если товаров не найдено и offset > 0, пробуем с 0
        if not products_data and offset > 0:
            logger.warning(f"No products found with offset={offset}, retrying with offset=0")
            await message.answer(
                f"⚠️ <b>Offset {offset} слишком большой</b>\n\n"
                f"На странице найдено меньше товаров чем указано в offset.\n"
                f"Начинаю парсинг с начала (offset=0)...",
                parse_mode="HTML",
            )
            products_data = await selenium_stealth_service.parse_category(
                url=url,
                max_products=parse_limit,
                offset=0
            )

        if not products_data:
            await message.answer("❌ <b>Товары не найдены</b>", parse_mode="HTML")
            await state.clear()
            return

        # Сохраняем
        async with database.get_session() as session:
            product_repo = ProductRepository(session)

            added = 0
            skipped = 0

            for product_data in products_data:
                # Проверка дубликата
                existing = await product_repo.get_by_url(product_data.get('source_url') or product_data.get('product_url'))
                if existing:
                    skipped += 1
                    continue

                price_rub = calculate_price_rub(
                    price_inr=product_data['price_inr'],
                    usd_inr=settings.usd_inr,
                    usd_rub=settings.usd_rub,
                    margin_percent=settings.margin_percent,
                    delivery_fixed=settings.delivery_fixed,
                    delivery_percent=settings.delivery_percent,
                )

                # 🛡️ WHITELISTING: Оставляем ТОЛЬКО поля которые есть в БД
                valid_columns = Product.__table__.columns.keys()
                allowed_keys = set(valid_columns + ['images'])

                clean_data = {
                    key: value
                    for key, value in product_data.items()
                    if key in allowed_keys
                }

                await product_repo.create({
                    **clean_data,
                    'price_rub': price_rub,
                    'is_on_sale': clean_data.get('discount_percent', 0) > 0,
                })
                added += 1

            # 🔐 ФОРМИРУЕМ СООБЩЕНИЕ С КНОПКОЙ ПРОДОЛЖЕНИЯ
            new_offset = offset + parse_limit

            builder = InlineKeyboardBuilder()
            builder.button(
                text=f"⏭ Парсить следующие {parse_limit} (offset: {new_offset})",
                callback_data=f"parse_more_{new_offset}"
            )
            builder.button(text="❌ Завершить", callback_data="parse_finish")
            builder.button(text="🔙 Назад", callback_data="admin_back")
            builder.adjust(1, 1)

            await message.answer(
                f"✅ <b>Парсинг завершён!</b>\n\n"
                f"📊 Найдено: {len(products_data)}\n"
                f"✅ Добавлено: {added}\n"
                f"⏭️ Пропущено (дубликаты): {skipped}\n"
                f"📍 Offset: {offset}\n\n"
                f"<i>Нажмите кнопку ниже чтобы продолжить парсинг следующих товаров.</i>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
            )

        # 🔐 ОБНОВЛЯЕМ СОСТОЯНИЕ С НОВЫМ OFFSET
        await state.update_data(current_offset=new_offset)

    except Exception as e:
        logger.error(f"Category parse error: {e}")
        await message.answer(f"❌ <b>Ошибка парсинга</b>\n\n<i>{safe_html(str(e)[:200])}</i>", parse_mode="HTML")
        await state.clear()


@router.message(AdminStates.waiting_for_category_offset)
async def process_category_offset_invalid(message: Message, state: FSMContext):
    """Обработка некорректного offset"""
    await message.answer(
        "⚠️ <b>Некорректное число</b>\n\n"
        "Отправьте число (например: 0, 40, 80) или /cancel для отмены",
        parse_mode="HTML",
    )


# 🔐 ОБРАБОТЧИКИ CALLBACK ДЛЯ ПРОДОЛЖЕНИЯ ПАРСИНГА

@router.callback_query(F.data.startswith("parse_more_"))
async def process_parse_more(callback: CallbackQuery, state: FSMContext):
    """Продолжение парсинга с новым offset"""
    data = await state.get_data()
    url = data.get('category_url')
    max_products = data.get('max_products', 40)

    # Извлекаем новый offset из callback_data
    new_offset = int(callback.data.replace("parse_more_", ""))

    if not url:
        await callback.answer("❌ Ошибка: URL не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"⏳ <b>Продолжаю парсинг...</b>\n\n"
        f"🔗 <code>{url[:60]}...</code>\n"
        f"📍 Offset: {new_offset} (пропустить первые {new_offset} товаров)\n"
        f"<i>Это займёт 2-3 минуты (до {max_products} товаров).</i>",
        parse_mode="HTML",
    )

    try:
        from app.services.selenium_service import selenium_stealth_service

        # 🔐 ПАРСИМ С НОВЫМ OFFSET
        products_data = await selenium_stealth_service.parse_category(
            url=url,
            max_products=max_products,
            offset=new_offset
        )

        if not products_data:
            await callback.message.answer("❌ <b>Товары не найдены</b>", parse_mode="HTML")
            await state.clear()
            return

        # Сохраняем
        async with database.get_session() as session:
            product_repo = ProductRepository(session)

            added = 0
            skipped = 0

            for product_data in products_data:
                # Проверка дубликата
                existing = await product_repo.get_by_url(product_data.get('source_url') or product_data.get('product_url'))
                if existing:
                    skipped += 1
                    continue

                price_rub = calculate_price_rub(
                    price_inr=product_data['price_inr'],
                    usd_inr=settings.usd_inr,
                    usd_rub=settings.usd_rub,
                    margin_percent=settings.margin_percent,
                    delivery_fixed=settings.delivery_fixed,
                    delivery_percent=settings.delivery_percent,
                )

                # 🛡️ WHITELISTING
                valid_columns = Product.__table__.columns.keys()
                allowed_keys = set(valid_columns + ['images'])

                clean_data = {
                    key: value
                    for key, value in product_data.items()
                    if key in allowed_keys
                }

                await product_repo.create({
                    **clean_data,
                    'price_rub': price_rub,
                    'is_on_sale': clean_data.get('discount_percent', 0) > 0,
                })
                added += 1

            # 🔐 ОБНОВЛЯЕМ OFFSET
            next_offset = new_offset + max_products

            builder = InlineKeyboardBuilder()
            builder.button(
                text=f"⏭ Парсить следующие {max_products} (offset: {next_offset})",
                callback_data=f"parse_more_{next_offset}"
            )
            builder.button(text="❌ Завершить", callback_data="parse_finish")
            builder.button(text="🔙 Назад", callback_data="admin_back")
            builder.adjust(1, 1)

            await callback.message.answer(
                f"✅ <b>Парсинг завершён!</b>\n\n"
                f"📊 Найдено: {len(products_data)}\n"
                f"✅ Добавлено: {added}\n"
                f"⏭️ Пропущено (дубликаты): {skipped}\n"
                f"📍 Offset: {new_offset}\n\n"
                f"<i>Нажмите кнопку ниже чтобы продолжить.</i>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
            )

            # Обновляем состояние
            await state.update_data(current_offset=next_offset)

    except Exception as e:
        logger.error(f"Parse more error: {e}")
        await callback.message.answer(f"❌ <b>Ошибка</b>\n\n<i>{safe_html(str(e)[:200])}</i>", parse_mode="HTML")
        await state.clear()


@router.callback_query(F.data == "parse_finish")
async def process_parse_finish(callback: CallbackQuery, state: FSMContext):
    """Завершение парсинга"""
    await state.clear()
    await callback.answer("✅ Парсинг завершён", show_alert=True)
    await callback.message.answer("🏠 <b>Возврат в главное меню</b>", parse_mode="HTML")
