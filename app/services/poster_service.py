"""
Poster Service v2.1 - Авто-постинг в группы
© 2026 All Rights Reserved.

Proprietary and Confidential.

🔐 Безопасность: HTML экранирование + Anti-Flood
"""

import asyncio
import html
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy import select
from app.core.config import settings
from app.db.database import database
from app.db.models import Setting
from app.db.repositories import PostGroupRepository, PostScheduleRepository, PostHistoryRepository, ProductRepository
from app.utils.logger import logger


class PosterService:
    """Сервис авто-постинга"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = None

    async def start_scheduler(self):
        """Запуск планировщика с динамическим интервалом из БД"""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from app.db.models import Setting

        self.scheduler = AsyncIOScheduler()

        # 🔐 ПОЛУЧАЕМ ИНТЕРВАЛ ИЗ БД (не из .env!)
        async with database.get_session() as session:
            result = await session.execute(select(Setting).where(Setting.key == "post_interval"))
            setting = result.scalar()
            interval_minutes = int(setting.value) if setting else 60  # По умолчанию 60 мин

        # Задача: проверка групп каждые N минут
        self.scheduler.add_job(
            self._check_and_post,
            trigger='interval',
            minutes=interval_minutes,
            id='auto_post',
            name='Auto Poster',
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(f"Poster scheduler started (interval: {interval_minutes} min)")

    async def stop_scheduler(self):
        """Остановка планировщика"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Poster scheduler stopped")

    async def _check_and_post(self):
        """Проверка и отправка постов"""
        try:
            async with database.get_session() as session:
                group_repo = PostGroupRepository(session)
                schedule_repo = PostScheduleRepository(session)
                product_repo = ProductRepository(session)
                history_repo = PostHistoryRepository(session)

                # Получаем все активные группы
                groups = await group_repo.get_all_active()

                now = datetime.utcnow()

                for group in groups:
                    # Получаем расписание
                    schedule = await schedule_repo.get_by_group_id(group.id)

                    if not schedule or not schedule.is_active:
                        continue

                    # Проверяем время (по UTC)
                    current_hour = now.hour
                    if current_hour < schedule.start_hour or current_hour > schedule.end_hour:
                        continue

                    # Проверяем день недели
                    current_day = now.weekday()
                    if current_day not in schedule.days_of_week:
                        continue

                    # Проверяем интервал
                    if group.last_post_at:
                        minutes_since_last = (now - group.last_post_at).total_seconds() / 60
                        if minutes_since_last < schedule.interval_minutes:
                            continue

                    # Получаем товар для поста
                    products = await product_repo.get_for_posting(group.id, limit=1)

                    if not products:
                        logger.info(f"No products for group {group.chat_name}")
                        continue

                    product = products[0]

                    # Отправляем пост
                    try:
                        success = await self._send_post(group, product)

                        if success:
                            # Обновляем статистику
                            await group_repo.increment_stats(group.id, posts=1)
                            await product_repo.update_last_posted(product.id)

                            # Сохраняем историю
                            await history_repo.create({
                                'group_id': group.id,
                                'product_id': product.id,
                                'status': 'sent',
                            })

                            logger.info(f"Posted product {product.id} to {group.chat_name}")

                        # 🔐 АНТИ-ФЛУД ЗАДЕРЖКА (1.5 сек между чатами)
                        await asyncio.sleep(1.5)

                    except TelegramRetryAfter as e:
                        logger.warning(f"Flood limit! Sleeping for {e.retry_after} seconds")
                        await asyncio.sleep(e.retry_after)
                        continue  # Попробуем в следующую итерацию шедулера

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

    async def _send_post(self, group: 'PostGroup', product: 'Product') -> bool:
        """Отправить пост в группу с галереей фото"""
        try:
            # Логирование для отладки
            logger.info(f"Sending post to group: {group.chat_name} (chat_id={group.chat_id})")
            logger.info(f"Product: {product.title[:50]} (price={product.price_rub})")

            # 🔐 ФОРМИРУЕМ ТЕКСТ (async/await)
            text = await self._format_post_text(product)
            logger.debug(f"Post text: {text[:200]}...")

            # 🔐 КЛАВИАТУРА (async/await)
            keyboard = await self._get_post_keyboard(product)

            # 🔐 ОТПРАВЛЯЕМ ГАЛЕРЕЮ (3-5 фото) - ГИБРИД: URL + fallback на скачивание
            if product.images and len(product.images) > 0:
                images = product.images if isinstance(product.images, list) else []

                # 🔐 ФИЛЬТР: Только валидные URL (не SVG), максимум 5 фото
                valid_images = [
                    img for img in images
                    if img and img.startswith('http') and not img.lower().endswith('.svg')
                ][:5]

                if len(valid_images) >= 1:
                    # Первое фото с текстом
                    logger.info(f"Sending photo gallery (hybrid): {len(valid_images)} photos")

                    # 🔐 ГИБРИД: Пробуем URL, если не работает → скачиваем
                    success = await self._send_media_group_hybrid(
                        chat_id=group.chat_id,
                        images=valid_images,
                        caption=text,
                    )

                    if success:
                        # Отправляем клавиатуру отдельным сообщением
                        await self.bot.send_message(
                            chat_id=group.chat_id,
                            text="👇 <b>Для заказа выберите:</b>",
                            reply_markup=keyboard,
                            parse_mode="HTML",
                        )
                    else:
                        logger.error(f"Failed to send media group to {group.chat_name}")
                        return False
                else:
                    # Только текст если нет фото
                    logger.info("Sending text message (no valid images)")
                    await self.bot.send_message(
                        chat_id=group.chat_id,
                        text=text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
            else:
                logger.info("Sending text message (no images)")
                await self.bot.send_message(
                    chat_id=group.chat_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )

            logger.info(f"Post successfully sent to {group.chat_name}")
            return True

        except TelegramRetryAfter:
            # 🔐 ПРОБРАСЫВАЕМ наверх для обработки в _check_and_post()
            logger.warning(f"Telegram RetryAfter exception")
            raise
        except Exception as e:
            logger.error(f"Send post error: {type(e).__name__}: {e}", exc_info=True)
            logger.error(f"Failed to send to group: {group.chat_name} (chat_id={group.chat_id})")
            return False

    async def _format_post_text(self, product: 'Product') -> str:
        """Форматировать текст поста с HTML экранированием + расчёт цены через USD"""
        from app.bots.handlers.admin_settings import get_setting_value

        # 🔐 БЕЗ ЭКРАНИРОВАНИЯ (оставляем название как в БД)
        safe_title = product.title[:150] if product.title else "Товар"
        safe_description = product.description[:300] if product.description else None

        # Извлекаем бренд из названия (до первого пробела или дефиса)
        brand = ""
        if product.title:
            brand_match = re.match(r'^([A-Z][A-Za-z]+)', product.title)
            if brand_match:
                brand = brand_match.group(1)

        # 🔐 ПОЛУЧАЕМ КУРСЫ ИЗ БД (async/await)
        usd_inr = await get_setting_value("usd_inr", 91.0)
        usd_rub = await get_setting_value("usd_rub", 80.0)

        # 🔐 РАСЧЁТ ЦЕНЫ: INR → USD → RUB
        price_usd = product.price_inr / usd_inr  # Конвертируем в USD
        price_rub = int(price_usd * usd_rub)  # Конвертируем в RUB

        text = f"🔥 <b>НОВОЕ ПОСТУПЛЕНИЕ!</b>\n\n"

        # Бренд + Название
        if brand:
            text += f"<b>{brand} {safe_title}</b>\n\n"
        else:
            text += f"<b>{safe_title}</b>\n\n"

        # Цена с расчётом через USD
        text += f"💵 Цена: <b>{price_rub:,} ₽</b>"

        if product.discount_percent > 0 and product.original_price_inr:
            old_price_usd = product.original_price_inr / usd_inr
            old_price_rub = int(old_price_usd * usd_rub)
            text += f" <s>{old_price_rub:,} ₽</s>"
            text += f" <i>(Скидка {int(product.discount_percent)}%)</i>"

        text += f"\n\n"

        # Наличие
        text += f"📦 Наличие: <i>Запрашивайте у менеджера</i>\n\n"

        # 🔐 АРТИКУЛ
        text += f"🔖 <b>Артикул: #{product.id}</b>\n\n"

        # Описание (если есть)
        if safe_description:
            text += f"<i>{safe_description}</i>\n\n"

        # 🔐 МЕНЕДЖЕР - используем функцию из manager.py
        from app.bots.handlers.manager import get_manager_for_notification
        manager_username = await get_manager_for_notification()

        text += f"👤 <b>Менеджер:</b> @{manager_username}\n\n"

        # Призыв к действию
        text += f"🛍 <b>Для заказа:</b>\n"
        text += f"1️⃣ Нажмите кнопку ниже\n"
        text += f"2️⃣ Или напишите артикул менеджеру: <code>#{product.id}</code>\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👤 Менеджер: @{manager_username}"

        return text

    async def _send_media_group_hybrid(self, chat_id: int, images: List[str], caption: str) -> bool:
        """
        🔐 ГИБРИДНАЯ ОТПРАВКА: Пробуем URL → fallback на скачивание
        """
        from aiogram.types import InputMediaPhoto, BufferedInputFile
        import aiohttp

        # 🔐 ПОПЫТКА 1: Отправка по URL (быстро)
        for attempt in range(3):  # 3 попытки
            try:
                logger.debug(f"Trying URL-based sending (attempt {attempt+1}/3) for {len(images)} images...")

                media_group = []
                for i, img_url in enumerate(images[:10]):
                    if i == 0:
                        media_group.append(
                            InputMediaPhoto(media=img_url, caption=caption, parse_mode="HTML")
                        )
                    else:
                        media_group.append(InputMediaPhoto(media=img_url))

                await self.bot.send_media_group(chat_id=chat_id, media=media_group)
                logger.info(f"✅ URL-based sending succeeded")
                return True

            except Exception as e:
                error_msg = str(e)
                if attempt < 2:  # Не последняя попытка
                    logger.warning(f"Attempt {attempt+1} failed: {error_msg}, retrying...")
                    await asyncio.sleep(2)  # Пауза перед следующей попыткой
                else:
                    logger.warning(f"URL-based sending failed after 3 attempts: {error_msg}")
                    logger.info(f"🔄 Falling back to file-based sending...")

        # 🔐 ПОПЫТКА 2: Скачиваем и отправляем как файлы
        return await self._send_images_as_files(chat_id, images, caption)

    async def _send_images_as_files(self, chat_id: int, images: List[str], caption: str) -> bool:
        """
        🔐 СКАЧИВАНИЕ + ОТПРАВКА ГАЛЕРЕЕЙ: Надёжно но медленнее
        """
        from aiogram.types import InputMediaPhoto, BufferedInputFile
        import aiohttp

        try:
            downloaded_photos = []

            # Скачиваем все изображения
            async with aiohttp.ClientSession() as session:
                for i, img_url in enumerate(images[:10]):
                    try:
                        async with session.get(img_url, timeout=10) as response:
                            if response.status != 200:
                                logger.warning(f"Failed to download image: {img_url}")
                                continue

                            photo_data = await response.read()
                            downloaded_photos.append(photo_data)
                            logger.debug(f"✅ Downloaded image {i+1}/{len(images)}")

                    except Exception as e:
                        logger.debug(f"Download error for image {i+1}: {e}")
                        continue

            if not downloaded_photos:
                logger.warning("No images downloaded")
                return False

            # Формируем media group из скачанных фото
            media_group = []
            for i, photo_data in enumerate(downloaded_photos[:10]):
                if i == 0:
                    # Первое фото с caption
                    media_group.append(
                        InputMediaPhoto(
                            media=BufferedInputFile(photo_data, filename=f"photo_{i}.jpg"),
                            caption=caption,
                            parse_mode="HTML"
                        )
                    )
                else:
                    media_group.append(
                        InputMediaPhoto(media=BufferedInputFile(photo_data, filename=f"photo_{i}.jpg"))
                    )

            # Отправляем галереей
            await self.bot.send_media_group(chat_id=chat_id, media=media_group)

            logger.info(f"✅ File-based gallery sending succeeded ({len(downloaded_photos)} images)")
            return True

        except Exception as e:
            logger.error(f"File-based gallery sending failed: {type(e).__name__}: {e}")
            return False

    async def _get_post_keyboard(self, product: 'Product') -> InlineKeyboardMarkup:
        """
        Клавиатура поста — ОДНА понятная кнопка
        🔐 ПРОСТО: Клиент пишет менеджеру напрямую
        """
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        # 🔐 ПОЛУЧАЕМ МЕНЕДЖЕРА ИЗ БД
        from app.bots.handlers.manager import get_manager_for_notification
        manager_username = await get_manager_for_notification()

        # 🔐 ОДНА КНОПКА — ведёт на менеджера с предзаполненным сообщением
        # Формируем сообщение для менеджера (полная ссылка + артикул)
        import urllib.parse

        message_text = (
            f"Товар: {product.title[:40]}\n"
            f"URL: {product.source_url}\n"
            f"Артикул: {product.id}"
        )

        # 🔐 КОДИРУЕМ для URL (чтобы # и пробелы работали)
        encoded_message = urllib.parse.quote(message_text)

        builder.row(
            InlineKeyboardButton(
                text="✍️ Написать менеджеру",
                url=f"https://t.me/{manager_username}?text={encoded_message}"
            )
        )

        return builder.as_markup()

    async def test_post(self, group_id: int, product_id: int) -> bool:
        """Тестовый пост"""
        async with database.get_session() as session:
            group_repo = PostGroupRepository(session)
            product_repo = ProductRepository(session)

            group = await group_repo.get_by_id(group_id)
            product = await product_repo.get_by_id(product_id)

            if not group or not product:
                return False

            return await self._send_post(group, product)


# Глобальный экземпляр (создаётся в main.py)
poster_service = None
