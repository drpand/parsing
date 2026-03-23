# preview_product.py - Предпросмотр товара перед добавлением

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.config import settings
from app.utils.logger import logger

router = Router()


async def show_product_preview(
    callback: CallbackQuery,
    state: FSMContext,
    page: int,
    product_idx: int
):
    """Показывает превью товара с фото и кнопками Добавить/Пропустить + Навигация"""
    
    if callback.from_user.id not in settings.admin_ids:
        return
    
    data = await state.get_data()
    products = data.get("products", [])
    
    if product_idx >= len(products):
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    product = products[product_idx]
    images = product.get('images', [])
    
    # Формируем описание
    discount_text = ""
    if product.get('discount_percent', 0) > 0:
        discount_text = f"🔥 Скидка: {int(product.get('discount_percent', 0))}%\n"
    
    caption = (
        f"🛍 <b>Товар #{product_idx + 1} из {len(products)}</b>\n\n"
        f"<b>{product.get('title', 'Unknown')[:100]}</b>\n\n"
        f"💰 <b>₹{product.get('price_inr', 0):,.0f}</b>\n"
        f"{discount_text}"
        f"🎨 Цвет: {product.get('color', 'N/A')}\n"
        f"📦 Категория: {product.get('category', 'other')}\n"
        f"{'✅ В наличии' if product.get('in_stock', True) else '❌ Нет в наличии'}\n\n"
        f"🔗 <code>{product.get('product_url', '')[:60]}...</code>\n\n"
        f"<b>Добавить в каталог?</b>"
    )
    
    # Создаём клавиатуру с навигацией
    keyboard = InlineKeyboardBuilder()
    
    # Кнопки действия
    keyboard.row(
        InlineKeyboardButton(text="✅ Добавить", callback_data=f"parse_confirm_add:{page}:{product_idx}"),
        InlineKeyboardButton(text="❌ Пропустить", callback_data=f"parse_skip:{page}:{product_idx}"),
    )
    
    # Кнопки навигации
    nav_buttons = []
    
    # Предыдущий товар
    if product_idx > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"parse_preview:{page}:{product_idx - 1}")
        )
    
    # Номер товара
    nav_buttons.append(
        InlineKeyboardButton(text=f"{product_idx + 1}/{len(products)}", callback_data="parse_current")
    )
    
    # Следующий товар
    if product_idx < len(products) - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"parse_preview:{page}:{product_idx + 1}")
        )
    
    keyboard.row(*nav_buttons)
    
    # Кнопка "К результатам"
    keyboard.row(
        InlineKeyboardButton(text="🔙 К списку", callback_data=f"parse_nav:{page}"),
    )
    
    # Отправляем фото или текст
    if images and len(images) > 0:
        try:
            # Пытаемся скачать изображение через requests
            import requests
            from aiogram.types import BufferedInputFile
            image_url = images[0]

            # 🔐 HEADERS для обхода CDN защиты (Akamai/Cloudflare)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Referer': 'https://www.zara.com/',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }

            # Скачиваем изображение с headers
            response = requests.get(image_url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Отправляем как байты через BufferedInputFile
                photo = BufferedInputFile(
                    response.content,
                    filename=f"product_{product_idx}.jpg"
                )
                await callback.message.answer_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="HTML",
                )
            else:
                # URL недоступен - отправляем текст
                logger.warning(f"Image URL returned {response.status_code}: {image_url}")
                await callback.message.answer(caption, reply_markup=keyboard.as_markup(), parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            await callback.message.answer(caption, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await callback.message.answer(caption, reply_markup=keyboard.as_markup(), parse_mode="HTML")


async def confirm_add_product(
    callback: CallbackQuery,
    state: FSMContext,
    page: int,
    product_idx: int
):
    """Добавляет товар в базу"""
    from app.db.database import database
    from app.db.repositories import ProductRepository
    from app.utils.helpers import calculate_price_rub
    
    data = await state.get_data()
    products = data.get("products", [])
    category_url = data.get("category_url", "")

    if product_idx >= len(products):
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    product = products[product_idx]
    product_url = product.get("product_url") or f"{category_url}#product-{product_idx}"

    async with database.get_session() as session:
        product_repo = ProductRepository(session)

        # Проверяем дубликат
        existing = await product_repo.get_by_url(product_url)
        if existing:
            await callback.message.answer(
                f"⚠️ <b>Уже существует!</b>\n\n"
                f"🛍 {existing.title[:50]}...\n"
                f"💰 {existing.price_rub:,.0f} ₽\n"
                f"🆔 ID: {existing.id}",
                parse_mode="HTML",
            )
            return

        # Рассчитываем цену
        price_rub = calculate_price_rub(
            price_inr=product.get('price_inr', 0),
            usd_inr=settings.usd_inr,
            usd_rub=settings.usd_rub,
            margin_percent=settings.margin_percent,
            delivery_fixed=settings.delivery_fixed,
            delivery_percent=settings.delivery_percent,
        )

        description = f"Цвет: {product.get('color', 'N/A')}" if product.get('color') else "Импорт из Индии"

        # Сохраняем
        import json
        db_product = await product_repo.create({
            "source_url": product_url,
            "title": product.get('title', 'Unknown'),
            "description": description,
            "category": product.get('category', 'other'),
            "gender": "F" if "women" in product.get('category', '').lower() else "M" if "men" in product.get('category', '').lower() else "U",
            "sizes": json.dumps([]),
            "images": json.dumps(product.get('images', [])),
            "price_inr": product.get('price_inr', 0),
            "original_price_inr": product.get('original_price_inr'),
            "discount_percent": product.get('discount_percent', 0),
            "price_rub": price_rub,
            "in_stock": product.get('in_stock', True),
            "is_on_sale": product.get('discount_percent', 0) > 0,
            "is_hot_deal": product.get('discount_percent', 0) >= 70,
        })

        logger.info(f"Product added: ID={db_product.id}, title={db_product.title}")

    # Показываем следующий товар или возвращаемся к списку
    if product_idx < len(products) - 1:
        # Есть следующий товар — показываем его
        await show_product_preview(callback, state, page, product_idx + 1)
    else:
        # Последний товар — возвращаемся к списку
        await callback.message.answer(
            f"✅ <b>Добавлен!</b>\n\n"
            f"🛍 {product.get('title', 'Unknown')[:50]}...\n"
            f"💰 {price_rub:,.0f} ₽ (₹{product.get('price_inr', 0):,.0f})\n"
            f"🆔 ID: {db_product.id}\n\n"
            f"🔙 <i>Это был последний товар. Вернитесь к списку.</i>",
            parse_mode="HTML",
        )


async def skip_product(
    callback: CallbackQuery,
    state: FSMContext,
    page: int,
    product_idx: int
):
    """Пропускает товар и показывает следующий"""
    data = await state.get_data()
    products = data.get("products", [])
    
    # Показываем следующий товар
    if product_idx < len(products) - 1:
        await show_product_preview(callback, state, page, product_idx + 1)
    else:
        await callback.message.answer(
            f"❌ <b>Пропущен</b>\n\n"
            f"Товар #{product_idx + 1} не добавлен.\n\n"
            f"🔙 <i>Это был последний товар. Вернитесь к списку.</i>",
            parse_mode="HTML",
        )
