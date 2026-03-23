import json
import re
import asyncio
import hashlib
import traceback
from typing import Optional, List
from dataclasses import dataclass
import httpx
from app.core.config import settings
from app.utils.logger import logger
from app.utils.helpers import parse_list_str


class OpenRouterError(Exception):
    """Ошибка при работе с OpenRouter API"""
    pass


@dataclass
class ProductData:
    """Структурированные данные о товаре"""
    url: str  # URL страницы товара
    title: str
    price_inr: float
    original_price_inr: Optional[float]
    discount_percent: float
    currency: str
    category: str
    sizes: list
    in_stock: bool
    description: str
    color: Optional[str]
    material: Optional[str]
    brand: Optional[str]
    image_url: Optional[str] = None  # Главное изображение (опционально)
    images: list = None  # Дополнительные изображения (опционально)
    gender: str = "U"  # M/F/U (по умолчанию Unisex)


class OpenRouterService:
    """Сервис для работы с OpenRouter API"""

    # Промпт для ТЕСТА — описание что видит AI
    PROMPT_DESCRIBE_IMAGE = """
Look at this screenshot carefully and describe what you see.

Describe in detail:
1. Is this a webpage? What website?
2. How many product cards can you see?
3. What text can you read (product names, prices, discounts)?
4. Are there any images of clothing/items?
5. Is the page loaded correctly or blank/error?

Answer in simple text, NO JSON needed.
"""

    # Промпт для парсинга НЕСКОЛЬКИХ товаров со страницы категории/распродажи
    PROMPT_EXTRACT_PRODUCTS = """
You are an API that extracts product data from e-commerce screenshots.
You MUST respond ONLY with a valid JSON array. Do not write any text, markdown, or explanations before or after the JSON.

URL: {url}

TASK: Extract ALL visible product cards from this screenshot. Look carefully at every corner of the image.

OUTPUT FORMAT REQUIREMENTS:
[
  {{"title":"Product Name","price_inr":999,"original_price_inr":2999,"discount_percent":67,"category":"men_clothing"}},
  {{"title":"Another Product","price_inr":599,"original_price_inr":null,"discount_percent":0,"category":"accessories"}}
]

CRITICAL RULES:
1. Return ONLY the JSON array. Start your response with `[` and end with `]`.
2. DO NOT try to extract image URLs or product URLs.
3. Prices MUST be numbers: 999 NOT "999" or "₹999".
4. Extract EVERY product visible on screen - even partially visible ones.
5. If you see a product card with readable title and price - include it.
6. Minimum 10 products expected from category pages.
7. Skip empty placeholders or loading states.
"""

    # Промпт для извлечения данных об ОДНОМ товаре
    # 🔐 УПРОЩЕНО: AI извлекает только данные (не URL!)
    PROMPT_EXTRACT_PRODUCT = """
Ты — AI для парсинга товаров с Zara, Myntra, Ajio.

URL: {url}

ЗАДАЧА: Извлеки данные из скриншота.

ОТВЕТ — ТОЛЬКО JSON (без markdown):

{{
  "title": "Название товара",
  "price_inr": 2950,
  "original_price_inr": null,
  "discount_percent": 0,
  "currency": "INR",
  "category": "shoes",
  "color": "White",
  "in_stock": true,
  "description": "Краткое описание на русском"
}}

ПРАВИЛА:
1. Цена — число (2950, не "₹2,950")
2. description — 1-2 предложения на русском
3. category — один из: shoes, clothing, accessories, bags, jewelry
4. НЕ пиши image_url и images (URL берём из DOM)

Верни JSON:
"""

    # 🔐 УНИВЕРСАЛЬНЫЙ ПРОМПТ ДЛЯ AI-АГЕНТА
    PROMPT_UNIVERSAL = """
Ты — AI-эксперт по парсингу маркетплейсов (Zara, Myntra, Nykaa, Ajio, Amazon, Flipkart).

ЗАДАЧА: Извлечь данные о товаре из текста страницы и списка изображений.

ВХОДНЫЕ ДАННЫЕ:
- URL: {url}
- Текст: {page_text}
- Изображения: {images}

ТРЕБОВАНИЯ:
1. **Бренд и название**: Найди в тексте
2. **Цена в INR**: Только индийские рупии (игнорируй USD, EUR)
3. **Изображения**: Выбери 3-5 лучших URL (высокое разрешение, без логотипов)
4. **Описание**: Переведи на русский (стиль fashion-блогера)
5. **JSON формат**: СТРОГО как ниже

ПРИМЕР:
{{
  "brand": "Nykaa",
  "title": "Cotton Kurti",
  "price_inr": 1299,
  "original_price_inr": 1999,
  "discount_percent": 35,
  "description_ru": "Стильная хлопковая курти с цветочным принтом...",
  "category": "women_clothing",
  "color": "Blue",
  "in_stock": true,
  "image_urls": ["url1", "url2"]
}}

ВАЖНО:
- Если не нашёл данные → {{"error": "not_found"}}
- price_inr — число (не строка!)
- description_ru — на русском
- image_urls — 3-5 URL

Извлеки данные:
"""

    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key.get_secret_value()

        # 🔐 ИСПОЛЬЗУЕМ МОДЕЛЬ ИЗ .ENV (не хардкод!)
        self.model = settings.openrouter_model
        self.fallback_models = parse_list_str(settings.openrouter_fallback_models)

        self.timeout = settings.openrouter_timeout
        self.max_retries = settings.openrouter_max_retries

        # 🔐 ЛОГИРОВАНИЕ МОДЕЛИ ПРИ ИНИЦИАЛИЗАЦИИ
        import logging
        logger = logging.getLogger('bot')
        logger.info(f"🔑 OpenRouterService model from .env: {self.model}")
        logger.info(f"🔑 Fallback models: {self.fallback_models}")

    def _extract_json_from_response(self, text: str) -> Optional[dict]:
        """Извлекает JSON из ответа модели"""
        text = text.strip()

        # 1. Пробуем распарсить как чистый JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Извлекаем из markdown-блока ```json
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Извлекаем из общего markdown-блока ```
        json_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 4. Пробуем найти JSON по скобкам {} или []
        start_curly = text.find('{')
        end_curly = text.rfind('}') + 1
        start_square = text.find('[')
        end_square = text.rfind(']') + 1

        # Пробуем фигурные скобки
        if start_curly != -1 and end_curly != 0:
            try:
                return json.loads(text[start_curly:end_curly])
            except json.JSONDecodeError:
                pass

        # Пробуем квадратные скобки (массив)
        if start_square != -1 and end_square != 0:
            try:
                return json.loads(text[start_square:end_square])
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to extract JSON from response: {text[:200]}...")
        return None

    async def _make_request(
        self,
        messages: list[dict],
        model: str,
        image_data: Optional[bytes] = None,
    ) -> dict:
        """Выполняет запрос к OpenRouter API"""
        logger.info(f"🤖 AI Model: {model}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/indiashop-bot",
            "X-Title": "IndiaShop Bot",
        }

        # Формируем контент-сообщение
        content = [{"type": "text", "text": messages[0]["content"]}]

        # Добавляем изображение если есть
        if image_data:
            import base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": content}
            ],
            "temperature": 0.1,  # Низкая температура для точного извлечения
            "max_tokens": 4000,  # Увеличено для категории (было 2000)
        }

        logger.info(f"📡 POST {self.base_url}/chat/completions")
        logger.info(f"📊 Image size: {len(image_data) if image_data else 0} bytes")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                raise OpenRouterError(
                    f"OpenRouter API error: {response.status_code} - {response.text[:200]}"
                )

            data = response.json()
            return data

    async def _call_with_fallback(
        self,
        messages: list[dict],
        image_data: Optional[bytes] = None,
    ) -> dict:
        """Вызов API с итеративным перебором fallback-моделей"""
        models_to_try = [self.model] + self.fallback_models
        last_error = None

        # Если нет fallback, пробуем только основную модель
        if not self.fallback_models:
            models_to_try = [self.model]

        for i, model in enumerate(models_to_try[:self.max_retries]):
            try:
                logger.info(f"Trying OpenRouter model: {model} (attempt {i+1}/{self.max_retries})")

                response_data = await self._make_request(
                    messages=messages,
                    model=model,
                    image_data=image_data,
                )

                return response_data  # Успех

            except OpenRouterError as e:
                last_error = e
                logger.warning(f"Model {model} failed: {e}")
                continue
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error with {model}: {type(e).__name__}: {e}")
                continue

        logger.error(f"All {self.max_retries} OpenRouter attempts failed: {last_error}")
        raise OpenRouterError(
            f"Failed to get response after {self.max_retries} attempts: {last_error}"
        )

    async def describe_screenshot(self, screenshot: bytes) -> str:
        """Описывает что видно на скриншоте (для отладки)"""
        logger.info("🔍 Describing screenshot...")

        prompt = self.PROMPT_DESCRIBE_IMAGE

        messages = [{"role": "user", "content": prompt}]

        response_data = await self._call_with_fallback(
            messages=messages,
            image_data=screenshot,
        )

        content = response_data["choices"][0]["message"]["content"]
        logger.info(f"AI description: {content[:500]}...")
        return content

    async def extract_products(
        self,
        url: str,
        page_text: str,
        screenshot: bytes,
    ) -> list[dict]:
        """Извлекает НЕСКОЛЬКО товаров со страницы категории"""
        logger.info("=" * 60)
        logger.info("🔍 НАЧАЛО AI-АНАЛИЗА КАТЕГОРИИ")
        logger.info("=" * 60)
        logger.info(f"URL: {url}")
        logger.info(f"Screenshot size: {len(screenshot)} bytes")

        prompt = self.PROMPT_EXTRACT_PRODUCTS.format(
            url=url,
            page_text=page_text[:2000] if page_text else ""
        )

        logger.info(f"Prompt length: {len(prompt)} chars")

        messages = [{"role": "user", "content": prompt}]

        # 🔄 ЦИКЛ ПЕРЕБОРА МОДЕЛЕЙ И ПАРСИНГА
        models_to_try = [self.model] + self.fallback_models
        if not self.fallback_models:
            models_to_try = [self.model]

        last_error = None
        json_data = None
        content = None

        for i, model in enumerate(models_to_try[:self.max_retries]):
            try:
                logger.info(f"Trying OpenRouter model: {model} (attempt {i+1}/{self.max_retries})")

                # 1. Запрос к API
                response_data = await self._make_request(
                    messages=messages,
                    model=model,
                    image_data=screenshot,
                )

                # 2. Извлекаем контент
                content = response_data["choices"][0]["message"]["content"]
                logger.info(f"Response length: {len(content)} chars")

                # 3. Пытаемся распарсить JSON СРАЗУ ЖЕ
                json_data = self._extract_json_from_response(content)

                # 🔐 ИСПРАВЛЕНО: Пустой список [] — это ВАЛИДНЫЙ ответ (товаров нет на скриншоте)
                if json_data is None:
                    raise ValueError(f"Модель {model} не вернула валидный JSON")

                # Если дошли сюда — JSON валидный (может быть пустым []), прерываем цикл!
                logger.info(f"✅ Успешный парсинг с помощью {model} (found {len(json_data) if isinstance(json_data, list) else 'object'} items)")
                break

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Ошибка с моделью {model}: {type(e).__name__}: {e}")
                continue  # Пробуем следующую модель

        # Проверяем итог цикла
        if json_data is None:
            logger.error(f"❌ Все модели не смогли вернуть JSON. Последняя ошибка: {last_error}")
            logger.error(f"Raw content: {content[:1000] if content else 'N/A'}")
            return []

        logger.info("=" * 60)
        logger.info("📋 RAW AI RESPONSE (first 1000 chars):")
        logger.info(content[:1000])
        logger.info("=" * 60)

        # Проверяем, что это массив
        if not isinstance(json_data, list):
            logger.warning(f"⚠️ Ожидался массив, получено: {type(json_data)}")
            logger.warning(f"First 500 chars: {str(json_data)[:500]}")
            json_data = [json_data] if isinstance(json_data, dict) else []

        logger.info(f"✅ Найдено элементов в ответе: {len(json_data)}")

        # Показываем первые элементы для отладки
        if json_data:
            logger.info(f"📦 First item keys: {list(json_data[0].keys()) if isinstance(json_data[0], dict) else 'NOT A DICT'}")
            logger.info(f"📦 First item: {json_data[0]}")

        # Валидация каждого товара
        products = []
        for i, item in enumerate(json_data):  # Обрабатываем ВСЕ товары которые вернул AI
            try:
                # Поддержка разных названий ключей
                title = item.get("title") or item.get("Title") or item.get("name") or item.get("Name")

                # Если title не найден — логируем и пропускаем
                if not title:
                    logger.warning(f"⚠️ Item {i+1}: NO TITLE FOUND!")
                    logger.warning(f"  Item data: {item}")
                    continue

                # Поддержка разных форматов цены
                price_raw = item.get("price_inr") or item.get("price") or item.get("Price") or item.get("current_price") or 0
                price = float(price_raw) if price_raw is not None else 0.0

                original_price_raw = item.get("original_price_inr") or item.get("original_price") or item.get("mrp") or item.get("MRP")
                original_price = float(original_price_raw) if original_price_raw is not None else None

                discount_raw = item.get("discount_percent") or item.get("discount") or item.get("off") or 0
                discount = float(discount_raw) if discount_raw is not None else 0.0

                category = item.get("category") or item.get("Category") or "other"
                color = item.get("color") or item.get("Color") or None
                in_stock = item.get("in_stock") or item.get("inStock") or item.get("available") or True

                # Проверка на блокировки
                if any(phrase in title.lower() for phrase in [
                    "access denied", "blocked", "forbidden", "error"
                ]):
                    logger.warning(f"⚠️ Пропуск заблокированного товара: {title}")
                    continue

                # Извлечение изображений
                image_url = item.get("image_url") or item.get("image") or item.get("imageUrl")
                images = item.get("images") or item.get("Images") or []

                # Если images пустой но есть image_url - добавляем
                if not images and image_url:
                    images = [image_url]

                products.append({
                    "title": str(title)[:200],
                    "price_inr": price,
                    "original_price_inr": original_price,
                    "discount_percent": discount,
                    "category": category,
                    "color": color,
                    "in_stock": in_stock,
                    "image_url": image_url,  # Добавляем URL главного изображения
                    "images": images,  # Добавляем массив изображений
                })

                logger.info(f"  ✓ Товар {i+1}: {title[:40]} | {price} INR | {discount}% | Images: {len(images)}")

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"⚠️ Неверные данные товара {i+1}: {e}")
                logger.warning(f"  Raw item data: {item}")
                continue

        logger.info(f"✅ Валидировано товаров: {len(products)}")
        logger.info("=" * 60)
        return products

    def _get_cache_key(self, url: str, screenshot: Optional[bytes] = None) -> str:
        """Создаёт ключ кэша по URL и хэшу скриншота"""
        screenshot_hash = hashlib.md5(screenshot[:1000]).hexdigest() if screenshot else "no_image"
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"cache_{url_hash}_{screenshot_hash}"

    def _get_from_cache(self, cache_key: str) -> Optional[dict]:
        """Получает данные из SQLite кэша"""
        try:
            import sqlite3
            conn = sqlite3.connect("bot_cache.db")
            cursor = conn.cursor()
            cursor.execute("SELECT data, created_at FROM product_cache WHERE key = ?", (cache_key,))
            row = cursor.fetchone()
            conn.close()

            if row:
                import json
                from datetime import datetime, timedelta
                data = json.loads(row[0])
                created_at = datetime.fromisoformat(row[1])

                # Кэш действителен 24 часа
                if datetime.now() - created_at < timedelta(hours=24):
                    logger.info(f"✅ CACHE HIT: {cache_key[:30]}...")
                    return data
                else:
                    logger.info(f"⏰ Cache expired: {cache_key[:30]}...")
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None

    def _save_to_cache(self, cache_key: str, data: dict):
        """Сохраняет данные в SQLite кэш"""
        try:
            import sqlite3
            from datetime import datetime
            conn = sqlite3.connect("bot_cache.db")
            cursor = conn.cursor()

            # Создаём таблицу если нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Сохраняем данные
            cursor.execute(
                "INSERT OR REPLACE INTO product_cache (key, data, created_at) VALUES (?, ?, ?)",
                (cache_key, json.dumps(data), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            logger.info(f"💾 CACHE SAVED: {cache_key[:30]}...")
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    def extract_product_sync(
        self,
        url: str,
        page_text: str,
        screenshot: Optional[bytes] = None,
    ) -> ProductData:
        """Синхронная версия extract_product для Selenium с кэшированием"""
        import base64
        import requests

        # 🔐 ПРОВЕРКА КЭША
        cache_key = self._get_cache_key(url, screenshot)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.info(f"🔄 Returning cached product data for {url[:50]}...")
            return ProductData(**cached_data, url=url)

        logger.info(f"🔍 Cache miss, calling API for {url[:50]}...")

        # Формируем промпт
        prompt = self.PROMPT_EXTRACT_PRODUCT.format(
            url=url,
            page_text=page_text[:4000] if page_text else ""
        )

        # Кодируем скриншот в base64
        image_base64 = base64.b64encode(screenshot).decode('utf-8') if screenshot else None

        # Формируем контент
        content = [{"type": "text", "text": prompt}]
        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
            })

        # Пытаемся вызвать API с fallback моделями
        models_to_try = [self.model] + self.fallback_models
        last_error = None

        for i, model in enumerate(models_to_try[:self.max_retries]):
            logger.info(f"[SYNC] Trying model: {model} (attempt {i+1}/{self.max_retries})")

            # Синхронный запрос к OpenRouter
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.1,
                "max_tokens": 1000,
            }

            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=45,  # 45 сек на AI запрос
                )

                if response.status_code != 200:
                    logger.warning(f"Model {model} failed: {response.status_code} - {response.text[:100]}")
                    last_error = Exception(f"OpenRouter API error: {response.status_code}")
                    continue

                data = response.json()
                content_result = data["choices"][0]["message"]["content"]

                logger.info(f"[SYNC] ✅ Model {model} succeeded")
                logger.info(f"AI response length: {len(content_result)} chars")

                # Извлекаем JSON
                json_data = self._extract_json_from_response(content_result)

                if not json_data:
                    logger.warning(f"Failed to parse JSON from {model}")
                    last_error = Exception("Failed to parse JSON")
                    continue

                # Валидация
                title = json_data.get("title", "Unknown Product")[:200]
                price_inr_raw = json_data.get("price_inr")

                # Обработка None значений
                if price_inr_raw is None:
                    logger.warning(f"No price_inr in AI response for {title[:50]}")
                    price_inr = 0.0
                elif isinstance(price_inr_raw, str):
                    try:
                        price_inr = float(price_inr_raw.replace(',', '').replace('₹', '').strip())
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid price_inr value: {price_inr_raw}")
                        price_inr = 0.0
                else:
                    price_inr = float(price_inr_raw)

                # Discount percent
                discount_raw = json_data.get("discount_percent")
                if discount_raw is None:
                    discount_percent = 0.0
                elif isinstance(discount_raw, str):
                    try:
                        discount_percent = float(discount_raw.replace('%', '').strip())
                    except (ValueError, AttributeError):
                        discount_percent = 0.0
                else:
                    discount_percent = float(discount_raw)

                # 🔐 СОХРАНЯЕМ В КЭШ ПЕРЕД ВОЗВРАТОМ
                cache_data = {
                    "title": title,
                    "price_inr": price_inr,
                    "original_price_inr": json_data.get("original_price_inr"),
                    "discount_percent": discount_percent,
                    "currency": "INR",
                    "category": json_data.get("category", "other"),
                    "sizes": json_data.get("sizes", []),
                    "in_stock": json_data.get("in_stock", True),
                    "description": json_data.get("description", "")[:500],
                    "color": json_data.get("color"),
                    "material": json_data.get("material"),
                    "brand": json_data.get("brand"),
                    "image_url": json_data.get("image_url"),
                    "images": json_data.get("images", []),
                    "gender": self._determine_gender(json_data.get("category", "")),
                }
                self._save_to_cache(cache_key, cache_data)

                return ProductData(
                    url=url,
                    title=title,
                    price_inr=price_inr,
                    original_price_inr=json_data.get("original_price_inr"),
                    discount_percent=discount_percent,
                    currency="INR",
                    category=json_data.get("category", "other"),
                    sizes=json_data.get("sizes", []),
                    in_stock=json_data.get("in_stock", True),
                    description=json_data.get("description", "")[:500],
                    color=json_data.get("color"),
                    material=json_data.get("material"),
                    brand=json_data.get("brand"),
                    image_url=json_data.get("image_url"),
                    images=json_data.get("images", []),
                    gender=self._determine_gender(json_data.get("category", "")),
                )

            except Exception as e:
                logger.error(f"Model {model} error: {e}")
                last_error = e
                continue

        # Все модели не сработали
        logger.error(f"All {self.max_retries} models failed")
        raise Exception(f"Failed to get response after {self.max_retries} attempts: {last_error}")

    async def extract_product(
        self,
        url: str,
        page_text: str,
        screenshot: Optional[bytes] = None,
    ) -> ProductData:
        """Извлекает данные о товаре из страницы"""

        # Проверяем кэш (по URL + хэш скриншота)
        cache_key = f"product:{hashlib.md5(url.encode() + (screenshot[:1000] if screenshot else b'')).hexdigest()}"

        try:
            import redis.asyncio as redis
            redis_client = await redis.from_url("redis://localhost:6379/0", decode_responses=True)
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {cache_key}")
                import json
                data = json.loads(cached)
                return ProductData(**data, url=url)
        except Exception:
            pass  # Redis недоступен, продолжаем без кэша

        logger.info(f"Starting AI analysis for URL: {url}")
        logger.info(f"Page text length: {len(page_text) if page_text else 0}, Screenshot: {bool(screenshot)}")

        prompt = self.PROMPT_EXTRACT_PRODUCT.format(
            url=url,
            page_text=page_text[:4000] if page_text else ""  # Меньше токенов
        )

        messages = [{"role": "user", "content": prompt}]

        # 🔄 ЦИКЛ ПЕРЕБОРА МОДЕЛЕЙ И ПАРСИНГА (как в extract_products)
        models_to_try = [self.model] + self.fallback_models
        if not self.fallback_models:
            models_to_try = [self.model]

        last_error = None
        json_data = None
        content = None

        for i, model in enumerate(models_to_try[:self.max_retries]):
            try:
                logger.info(f"Trying OpenRouter model: {model} (attempt {i+1}/{self.max_retries})")

                # 1. Запрос к API
                response_data = await self._make_request(
                    messages=messages,
                    model=model,
                    image_data=screenshot,
                )

                # 2. Извлекаем контент
                content = response_data["choices"][0]["message"]["content"]
                logger.info(f"Response length: {len(content)} chars")

                # 3. Пытаемся распарсить JSON СРАЗУ ЖЕ
                json_data = self._extract_json_from_response(content)

                if not json_data:
                    raise ValueError(f"Модель {model} не вернула валидный JSON")

                # Если дошли сюда — JSON валидный, прерываем цикл!
                logger.info(f"✅ Успешный парсинг с помощью {model}")
                break

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Ошибка с моделью {model}: {type(e).__name__}: {e}")
                continue  # Пробуем следующую модель

        # Проверяем итог цикла
        if not json_data:
            logger.error(f"❌ Все модели не смогли вернуть JSON. Последняя ошибка: {last_error}")
            logger.error(f"Raw content: {content[:1000] if content else 'N/A'}")
            raise OpenRouterError(f"Failed to parse JSON after {self.max_retries} attempts: {last_error}")

        logger.info(f"JSON extracted successfully: {list(json_data.keys())}")

        # Проверка на "мусорные" данные
        title = json_data.get("title", "")
        if any(phrase in title.lower() for phrase in [
            "access denied", "blocked", "forbidden", "unauthorized",
            "page not available", "not found", "error"
        ]):
            logger.warning(f"AI detected blocked page: {title}")
            raise OpenRouterError(f"Страница заблокирована или недоступна: {title}")

        # Валидация и создание объекта
        try:
            # Безопасное преобразование цены
            price_inr_raw = json_data.get("price_inr")
            price_inr = float(price_inr_raw) if price_inr_raw is not None else 0.0

            original_price_raw = json_data.get("original_price_inr")
            original_price_inr = float(original_price_raw) if original_price_raw is not None else None

            discount_raw = json_data.get("discount_percent")
            discount_percent = float(discount_raw) if discount_raw is not None else 0.0

            product = ProductData(
                url=url,
                title=json_data.get("title", "Unknown Product")[:200],
                price_inr=price_inr,
                original_price_inr=original_price_inr,
                discount_percent=discount_percent,
                currency=json_data.get("currency", "INR"),
                category=json_data.get("category", "other"),
                sizes=json_data.get("sizes", []),
                in_stock=json_data.get("in_stock", True),
                description=json_data.get("description", "")[:500],
                color=json_data.get("color"),
                material=json_data.get("material"),
                brand=json_data.get("brand"),
                image_url=json_data.get("image_url"),  # Извлекаем картинку
                images=json_data.get("images", []),
                gender=self._determine_gender(json_data.get("category", "")),
            )
            logger.info(f"Product data validated: {product.title}, price: {product.price_inr} INR")

            # Сохраняем в кэш
            try:
                import redis.asyncio as redis
                redis_client = await redis.from_url("redis://localhost:6379/0", decode_responses=True)
                import json
                await redis_client.setex(cache_key, 3600, json.dumps(product.__dict__))
            except Exception:
                pass  # Кэш не критичен

            return product
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid product data structure: {e}")
            raise OpenRouterError(f"Invalid product data structure: {e}")

    async def extract_universal(self, url: str, page_text: str, images: List[str]) -> Optional[dict]:
        """
        🔐 УНИВЕРСАЛЬНЫЙ AI-ПАРСИНГ
        Для любых сайтов: Nykaa, Ajio, Amazon, Flipkart, etc.

        Args:
            url: URL страницы
            page_text: Текст страницы
            images: Список URL изображений

        Returns:
            dict: Данные товара или None
        """
        logger.info("=" * 60)
        logger.info("🤖 AI UNIVERSAL PARSER")
        logger.info("=" * 60)

        # Формируем промпт
        prompt = self.PROMPT_UNIVERSAL.format(
            url=url,
            page_text=page_text[:8000],  # Ограничиваем
            images=", ".join(images[:20])
        )

        messages = [{"role": "user", "content": prompt}]

        # Пытаемся получить ответ
        models_to_try = [self.model] + self.fallback_models
        last_error = None

        for i, model in enumerate(models_to_try[:self.max_retries]):
            try:
                logger.info(f"Trying {model} (attempt {i+1})")

                response_data = await self._make_request(
                    messages=messages,
                    model=model,
                    image_data=None
                )

                content = response_data["choices"][0]["message"]["content"]
                json_data = self._extract_json_from_response(content)

                if json_data:
                    logger.info(f"✅ Success with {model}")

                    # Проверяем на ошибку
                    if isinstance(json_data, dict) and json_data.get("error") == "not_found":
                        logger.warning("AI returned not_found")
                        return None

                    return json_data

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ {model} failed: {e}")
                continue

        logger.error(f"❌ All models failed: {last_error}")
        return None

    def _determine_gender(self, category: str) -> str:
        """Определяет пол по категории"""
        category_lower = category.lower()

        if any(word in category_lower for word in ['women', 'female', 'girl', 'ladies']):
            return 'F'
        elif any(word in category_lower for word in ['men', 'male', 'boy', 'gents']):
            return 'M'
        else:
            return 'U'  # Unisex

    async def select_best_images(self, images: List[str], product_title: str) -> List[str]:
        """
        🔐 AI ВЫБОР ЛУЧШИХ ИЗОБРАЖЕНИЙ
        Фильтрует SVG, логотипы, выбирает лучшие ракурсы

        Args:
            images: Список всех URL изображений
            product_title: Название товара

        Returns:
            List[str]: Лучшие 3-5 изображений
        """
        if not images:
            return []

        # 🔐 ФИЛЬТР 1: Быстрая фильтрация SVG и мусора
        filtered_images = []
        for img_url in images:
            if not img_url or not img_url.startswith('http'):
                continue
            # Пропускаем SVG
            if img_url.lower().endswith('.svg'):
                continue
            # Пропускаем логотипы и иконки
            if any(skip in img_url.lower() for skip in ['logo', 'icon', 'placeholder']):
                continue
            filtered_images.append(img_url)

        if len(filtered_images) <= 3:
            # Если мало фото, возвращаем все
            return filtered_images[:5]

        # 🔐 ФИЛЬТР 2: AI выбирает лучшие
        try:
            prompt = f"""
Ты — эксперт по выбору изображений товаров для маркетплейсов.

ЗАДАЧА: Выбери 3-5 лучших изображений товара из списка.

КРИТЕРИИ:
1. Только товар (не модели, не логотипы)
2. Разные ракурсы (спереди, сбоку, сзади, детали)
3. Высокое качество (больше пикселей = лучше)
4. Без текста и водяных знаков

Товар: {product_title}

Список URL (выбери 3-5 лучших):
{chr(10).join(f"- {img}" for img in filtered_images[:15])}

ОТВЕТ: Верни ТОЛЬКО JSON массив URL (без markdown):
["url1.jpg", "url2.jpg", "url3.jpg"]
"""

            messages = [{"role": "user", "content": prompt}]

            response_data = await self._make_request(
                messages=messages,
                model=self.model,
                image_data=None
            )

            content = response_data["choices"][0]["message"]["content"]
            selected_images = self._extract_json_from_response(content)

            if isinstance(selected_images, list) and len(selected_images) > 0:
                logger.info(f"✅ AI selected {len(selected_images)} best images")
                return selected_images[:5]
            else:
                logger.warning("⚠️ AI didn't return valid images, using fallback")

        except Exception as e:
            logger.warning(f"⚠️ AI image selection failed: {e}, using fallback")

        # Fallback: возвращаем первые 5
        return filtered_images[:5]

        if any(x in category_lower for x in ["men", "male", "boy"]):
            return "M"
        elif any(x in category_lower for x in ["women", "female", "girl", "ladies"]):
            return "F"
        else:
            return "U"
