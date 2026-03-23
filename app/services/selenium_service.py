"""
Selenium Stealth Service с Vision AI
© 2026 All Rights Reserved.

Proprietary and Confidential.

- Selenium + stealth плагины
- Эмуляция человека
- Vision AI для извлечения данных
- ✅ Smart Merge по SKU для точного соответствия
- ✅ Explicit Waits для React SPA
- ✅ Viewport scrolling вместо scrollHeight
"""

import asyncio
import re
from typing import Optional, Tuple, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import random
import time
from app.core.config import settings
from app.utils.logger import logger
from app.utils.validator import validate_product_data, batch_validate_products, extract_sku_from_url
from app.services.openrouter_service import OpenRouterService


class SeleniumStealthService:
    """Selenium Stealth + Vision AI для парсинга товаров"""

    def __init__(self):
        self.driver = None
        self.openrouter = OpenRouterService()

    def _extract_sku(self, text: str) -> str:
        """
        Извлекает SKU из любого текста/URL для сопоставления.
        Поддерживает Zara и Myntra.
        """
        if not text:
            return ""

        # Паттерн Zara: -p01234567.html
        zara_match = re.search(r'-p(\d{7,})', text)
        if zara_match:
            return f"p{zara_match.group(1)}"

        # Паттерн Myntra: /1234567/buy или /1234567.html
        myntra_match = re.search(r'/(\d{7,})(?:\.html|/buy)?', text)
        if myntra_match:
            return myntra_match.group(1)

        return ""

    def _smart_merge(self, dom_pairs: List[dict], ai_products: List[dict]) -> List[dict]:
        """
        🔐 ГИБРИДНОЕ слияние: SKU (100% точность) + Keywords (fallback)
        Гарантирует, что товар "Jacket" получит ссылку, в которой есть слово "jacket".
        """
        import re

        merged_products = []

        # Делаем копию, чтобы удалять найденные связки и не присвоить одну ссылку двум товарам
        available_doms = dom_pairs.copy()

        for ai_item in ai_products:
            title = ai_item.get("title", "")
            if not title:
                continue

            # 🔐 ШАГ 1: Пробуем найти по SKU (100% точность)
            dom_sku = None
            ai_text_combined = f"{title} {ai_item.get('image_url', '')}".lower()

            best_match = None
            best_score = 0

            # Ищем наиболее подходящий URL из DOM
            for dom_item in available_doms:
                # Извлекаем SKU из DOM URL
                dom_sku = self._extract_sku(dom_item['url'])

                # 🔐 ПРОВЕРКА ПО SKU (если AI вернул SKU в названии или image_url)
                if dom_sku and dom_sku in ai_text_combined:
                    # БИНГО! 100% совпадение по артикулу
                    best_match = dom_item
                    best_score = 999  # Максимальный приоритет
                    logger.info(f"🎯 SKU match: [{title[:40]}] <---> [{dom_sku}]")
                    break

                # Фоллбек: используем алгоритм подсчета score по ключевым словам
                url_lower = dom_item['url'].lower()

                # Разбиваем название на слова (длиной > 3 символов), переводим в нижний регистр
                title_words = [w.lower() for w in re.findall(r'\b\w+\b', title) if len(w) > 3]

                # Улучшенный подсчет очков
                score = 0
                for word in title_words:
                    if word in url_lower:
                        # Цвет или материал дают х2 очков уверенности
                        if word in ['black', 'white', 'red', 'blue', 'green', 'leather', 'cotton', 'denim', 'linen', 'silk', 'wool', 'polyester']:
                            score += 2
                        else:
                            score += 1

                if score > best_score:
                    best_score = score
                    best_match = dom_item

            # Если нашли по SKU (score=999) или по keywords (score>=1)
            if best_match and best_score >= 1:
                # 🎯 Успешное сопоставление! Название соответствует ссылке.
                merged_product = ai_item.copy()
                merged_product["source_url"] = best_match["url"]
                merged_product["product_url"] = best_match["url"]
                merged_product["images"] = best_match["images"]
                merged_product["image_url"] = best_match["images"][0] if best_match["images"] else None

                merged_products.append(merged_product)
                available_doms.remove(best_match)  # Убираем из пула, чтобы не использовать дважды

                match_type = "SKU" if best_score == 999 else "Keywords"
                logger.info(f"🔗 Склеено ({match_type}): [{title[:40]}] <---> [{best_match['url'][-50:]}] (score: {best_score})")
            else:
                logger.warning(f"⚠️ Отбраковано: Не найдена подходящая ссылка для [{title[:40]}]")

        return merged_products

    def start(self, force_windowed: bool = False, use_undetected: bool = False):
        """Запуск Selenium браузера

        Args:
            force_windowed: Если True — открывать окно (не headless)
            use_undetected: Если True — использовать undetected-chromedriver (для Nykaa)
        """
        logger.info("Starting Selenium stealth browser...")

        # 🔐 ЛОГИРОВАНИЕ МОДЕЛИ ИЗ КОНФИГА
        logger.info(f"🔑 DEBUG: Settings model is: {settings.openrouter_model}")
        logger.info(f"🔑 OpenRouter Fallback: {settings.openrouter_fallback_models}")

        # 🔐 UNDETECTED CHROMEDRIVER ДЛЯ NYKAA
        if use_undetected:
            try:
                import undetected_chromedriver as uc
                logger.info("🔐 Using undetected-chromedriver for Nykaa")

                chrome_options = Options()
                if not force_windowed:
                    chrome_options.add_argument("--headless=new")
                else:
                    logger.info("🔐 WINDOWED MODE")

                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")

                # 🔐 ФИКСИРУЕМ ВЕРСИЮ (чтобы не было рассинхрона)
                # UC сам подберёт правильную версию ChromeDriver
                self.driver = uc.Chrome(
                    options=chrome_options,
                    use_subprocess=True,  # Исправляет баги на Windows
                    auto_version_detection=True,  # Авто-подбор версии
                    version_main=145  # 🔐 Явно указываем версию Chrome
                )
                logger.info("✅ Undetected chromedriver started")
                return

            except ImportError:
                logger.error("❌ undetected-chromedriver not installed")
                raise  # 🔐 НЕ fallback — ошибка!
            except Exception as e:
                logger.error(f"❌ Undetected chromedriver error: {e}")
                raise  # 🔐 НЕ fallback — ошибка!

        # 🔐 ОБЫЧНЫЙ CHROME (для Zara/Myntra)
        chrome_options = Options()

        # 🔐 HEADLESS РЕЖИМ: Можно отключить для защищённых сайтов
        if not force_windowed:
            chrome_options.add_argument("--headless=new")  # Новый движок (Chrome 109+)
        else:
            logger.info("🔐 WINDOWED MODE: Открываем окно для обхода защиты")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # 🔐 ФОРСИРОВАНИЕ РЕНДЕРИНГА КАРТИНОК (КРИТИЧНО ДЛЯ MYNTRA)
        chrome_options.add_argument("--blink-settings=imagesEnabled=true")
        chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--hide-scrollbars")

        # 🔐 НОРМАЛЬНАЯ ЗАГРУЗКА СТРАНИЦЫ (КРИТИЧНО ДЛЯ АССЕТОВ)
        # Eager обрывает загрузку медиа - нам нужно "normal"
        chrome_options.page_load_strategy = "normal"

        # 🔐 ОПТИМИЗАЦИЯ ПАМЯТИ: отключаем лишние функции
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        # ❌ УДАЛЕНО: chrome_options.add_argument("--disable-images")  # Блокирует Vision AI!

        # 🔐 ЖЁСТКИЙ USER-AGENT: Без слова "Headless", иначе Myntra заблокирует
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

        # Запуск с webdriver-manager (используем системный драйвер если есть)
        try:
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.warning(f"System ChromeDriver not found, downloading: {e}")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Применяем stealth
        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        logger.info("Selenium stealth browser started (optimized)")

    def restart_browser(self):
        """
        🔐 АВТО-ВОСКРЕШЕНИЕ: Перезапуск браузера для очистки памяти.
        Используется при глубокой пагинации для предотвращения крашей.
        """
        logger.info("🔄 Перезапуск браузера для очистки памяти...")
        self.stop()
        time.sleep(2)  # Пауза для полного освобождения ресурсов
        self.start()
        logger.info("✅ Браузер перезапущен (память очищена)")

    def stop(self):
        """
        🔐 БЕЗОПАСНАЯ остановка драйвера без спама в логи.
        Использует паттерн Graceful Shutdown с проверкой состояния сессии.
        """
        if not self.driver:
            logger.info("Browser was not started.")
            return

        try:
            # 🔐 ПРОВЕРКА: жив ли ещё драйвер перед очисткой
            # Если драйвер уже "отвалился", это вызовет исключение
            _ = self.driver.window_handles

            # ОЧИСТКА ПАМЯТИ: удаляем cookies и закрываем вкладки
            self.driver.delete_all_cookies()

            # Закрываем все вкладки кроме первой
            if len(self.driver.window_handles) > 1:
                for window in self.driver.window_handles[1:]:
                    self.driver.switch_to.window(window)
                    self.driver.close()

            # Возвращаемся на первую вкладку
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])

            # Полное закрытие браузера
            self.driver.quit()
            logger.info("Selenium browser stopped successfully.")

        except Exception as e:
            # 🔐 Если соединение уже разорвано — просто логируем факт
            logger.warning(f"Driver already unreachable (graceful shutdown): {type(e).__name__}: {e}")
        finally:
            self.driver = None
            logger.info("Selenium stealth browser stopped (memory cleaned)")

    def load_page(self, url: str, timeout: int = 60, retry_count: int = 0) -> Tuple[str, bytes]:
        """
        Загружает страницу и возвращает текст + скриншот.
        ✅ ИСПРАВЛЕНО: Explicit Waits для React SPA + Viewport scrolling
        ✅ АВТО-ВОСКРЕШЕНИЕ: Рестарт браузера при краше вкладки
        """
        if not self.driver:
            self.start()

        try:
            logger.info(f"Selenium loading page: {url[:60]}...")

            # Случайная задержка перед запросом
            time.sleep(random.uniform(0.5, 1.5))  # 🔐 УМЕНЬШЕНО с 1-3 до 0.5-1.5

            # 🔐 АВТО-ВОСКРЕШЕНИЕ: Загружаем страницу с обработкой крашей
            try:
                self.driver.get(url)
            except Exception as e:
                # Ловим WebDriverException (tab crashed, session not created, etc.)
                logger.warning(f"⚠️ Ошибка загрузки страницы: {type(e).__name__}: {e}")
                if retry_count < 1:  # Пробуем только 1 раз
                    logger.info("🔄 Попытка перезапуска браузера...")
                    self.restart_browser()
                    return self.load_page(url, timeout, retry_count + 1)
                else:
                    logger.error("❌ Не удалось загрузить страницу после перезапуска")
                    raise

            self.driver.set_page_load_timeout(timeout)

            # 🛑 1. ЯВНОЕ ОЖИДАНИЕ (Критичный фикс для React SPA)
            # Ждем, пока React отрисует хотя бы пару картинок или ссылок
            try:
                WebDriverWait(self.driver, 5).until(  # 🔐 СОКРАЩЕНО с 15 до 5 секунд
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "img")) > 5 or \
                              len(d.find_elements(By.CSS_SELECTOR, "a[href]")) > 10
                )
                logger.info("✅ DOM elements rendered successfully.")
            except Exception:
                logger.warning("⚠️ Таймаут ожидания элементов. Возможно, страница пустая или капча.")

            # 🔐 ПРОВЕРКА ЗАГОЛОВКА (для обнаружения блокировок)
            page_title = self.driver.title
            logger.info(f"Page title: {page_title}")

            if page_title in ["Just a moment...", "Access Denied", "Attention Required!"]:
                logger.error(f"⚠️ Possible block detected! Title: {page_title}")
                logger.warning("Headless mode may be blocked. Consider using windowed mode or rotating user-agents.")

            # Небольшая пауза для прогрузки CSS/картинок
            time.sleep(random.uniform(1, 2))  # 🔐 УМЕНЬШЕНО с 2-4 до 1-2

            logger.info("Page fully loaded (React rendered)")

            # Проверяем на Access Denied
            page_source = self.driver.page_source
            if "Access Denied" in page_source or "Akamai" in page_source or "Reference #" in page_source:
                logger.error("Akamai Access Denied detected")
                raise Exception("Akamai Access Denied - page blocked")

            # Извлекаем текст
            visible_text = self.driver.find_element("tag name", "body").text

            # Делаем скриншот с качеством 60% (JPEG вместо PNG для уменьшения размера)
            from PIL import Image
            import io

            # Делаем PNG скриншот
            png_screenshot = self.driver.get_screenshot_as_png()

            # Конвертируем в JPEG с качеством 60%
            img = Image.open(io.BytesIO(png_screenshot))
            img = img.convert('RGB')  # Удаляем alpha канал
            buffer = io.BytesIO()
            img.save(buffer, 'JPEG', quality=60, optimize=True)
            screenshot = buffer.getvalue()

            logger.info(f"Screenshot (JPEG 60%): {len(screenshot)} bytes ({len(screenshot) / 1024:.1f} KB)")

            return visible_text, screenshot

        except Exception as e:
            logger.error(f"Selenium error loading {url}: {type(e).__name__}: {e}")
            raise

    def parse_product(self, url: str) -> Optional[dict]:
        """
        Парсит товар через Selenium + Vision AI.
        🔐 ГИБРИД: DOM (изображения) + AI (данные)

        Args:
            url: URL страницы товара

        Returns:
            dict: Данные товара или None
        """
        try:
            # Загружаем страницу и делаем скриншот
            page_text, screenshot = self.load_page(url)

            # 🔐 DOM извлекает URL изображений (надёжно!)
            dom_images = self._extract_images_from_dom(url)

            # AI извлекает данные (название, цена, описание)
            product_data = self.openrouter.extract_product_sync(
                url=url,
                page_text=page_text,
                screenshot=screenshot,
            )

            logger.info(f"Parsed product: {product_data.title[:40]} | ₹{product_data.price_inr}")

            # 🔐 БЕРЁМ ИЗОБРАЖЕНИЯ ОТ DOM (URL), данные от AI
            images = dom_images[:10] if dom_images else (product_data.images if product_data.images else [])

            # Если AI вернул image_url но нет images - используем его
            if not images and product_data.image_url:
                images = [product_data.image_url]

            return {
                "source_url": url,
                "title": product_data.title,
                "price_inr": product_data.price_inr,
                "original_price_inr": product_data.original_price_inr,
                "discount_percent": product_data.discount_percent,
                "category": product_data.category,
                "color": product_data.color,
                "in_stock": product_data.in_stock,
                "product_url": url,
                "images": images,
            }

        except Exception as e:
            logger.error(f"Product parse error: {type(e).__name__}: {e}")
            return None

    async def get_raw_content(self, url: str) -> Optional[dict]:
        """
        🔐 УНИВЕРСАЛЬНЫЙ СБОРЩИК КОНТЕНТА ДЛЯ AI
        Собирает весь текст и изображения для передачи AI.
        Работает для ЛЮБЫХ сайтов (Nykaa, Ajio, Amazon, etc.)
        """
        logger.info(f"🔐 Universal collector: {url[:60]}...")

        try:
            # 1. Загружаем страницу
            page_text, screenshot = self.load_page(url)

            # 2. Собираем все изображения
            all_images = self._collect_all_image_urls()

            logger.info(f"✅ Collected: {len(page_text)} chars, {len(all_images)} images")

            return {
                'text': page_text,
                'images': all_images,
                'url': url
            }

        except Exception as e:
            logger.error(f"Universal collector error: {e}")
            return None

    def _collect_all_image_urls(self) -> List[str]:
        """Собирает ВСЕ img src/srcset/data-src со страницы"""
        images = []
        seen = set()

        try:
            img_elements = self.driver.find_elements("css selector", "img")

            for img in img_elements:
                for attr in ['src', 'data-src', 'data-original']:
                    src = img.get_attribute(attr)
                    if src and len(src) > 20 and src not in seen:
                        clean_src = src.split('?')[0]
                        if self._is_valid_product_image(clean_src):
                            images.append(clean_src)
                            seen.add(clean_src)

                # Srcset для webp
                srcset = img.get_attribute("srcset")
                if srcset:
                    first = srcset.split(',')[0].split(' ')[0]
                    if first and len(first) > 20 and first not in seen:
                        clean_src = first.split('?')[0]
                        if self._is_valid_product_image(clean_src):
                            images.append(clean_src)
                            seen.add(clean_src)

            # Сортируем по качеству
            images.sort(key=lambda x: any(r in x for r in ['1920', '2000', '1000']), reverse=True)
            return images[:10]

        except Exception as e:
            logger.error(f"Image collection error: {e}")
            return []

    def _is_valid_product_image(self, url: str) -> bool:
        """Фильтр — только товарные фото Zara"""
        url_lower = url.lower()

        # ✅ Для Zara: проверяем zara.net и блокируем плейсхолдеры
        if 'zara.net' in url_lower:
            # ❌ Блокируем явные плейсхолдеры
            if any(kw in url_lower for kw in [
                'transparent-background', 'placeholder', 'icon', 'logo',
                'spinner', 'loading', 'empty', 'null', 'stdstatic'
            ]):
                return False
            # ✅ Разрешаем всё с zara.net
            return True

        # ❌ Мусор для других доменов
        if any(kw in url_lower for kw in [
            'icon', 'logo', 'banner', 'ad', 'tracking', 'placeholder',
            'spinner', 'loading', 'transparent-background', 'empty', 'null'
        ]):
            return False

        # ✅ Домены маркетплейсов
        valid = ['zara.net', 'myntassets.com', 'nykaafashion.com', 'nykaa.com', 'ajio.com', 'amazon', 'flipkart']
        return any(d in url_lower for d in valid)

    def _extract_images_from_dom(self, base_url: str) -> List[str]:
        """
        Извлекает URL изображений товара из DOM.
        ✅ v0.8.8 STYLE: Поддержка data-src для lazy load
        ✅ Поддержка CSS background-image
        ✅ Поддержка <picture><source srcset>
        ✅ Поддержка JSON-LD (структурированные данные)
        ✅ Фильтр: только zara.net

        Args:
            base_url: Базовый URL

        Returns:
            List[str]: Список URL изображений
        """
        images = []

        try:
            # 🔐 ШАГ 1: JSON-LD (самый надёжный источник)
            json_ld_scripts = self.driver.find_elements("css selector", 'script[type="application/ld+json"]')
            for script in json_ld_scripts:
                try:
                    json_text = script.get_attribute("innerHTML") or script.get_attribute("textContent")
                    if json_text:
                        import json
                        data = json.loads(json_text)
                        # Ищем изображения в JSON-LD
                        if isinstance(data, dict):
                            json_images = data.get('image', [])
                            if isinstance(json_images, list):
                                for img_url in json_images[:10]:
                                    if img_url and 'zara.net' in img_url:
                                        clean_url = img_url.split('?')[0]
                                        clean_url = re.sub(r'/w/\d+/', '/w/1920/', clean_url)
                                        if clean_url not in images:
                                            images.append(clean_url)
                            elif isinstance(json_images, str) and 'zara.net' in json_images:
                                clean_url = json_images.split('?')[0]
                                clean_url = re.sub(r'/w/\d+/', '/w/1920/', clean_url)
                                if clean_url not in images:
                                    images.append(clean_url)
                except Exception as e:
                    logger.debug(f"JSON-LD parse error: {e}")

            # 🔐 ШАГ 2: <picture><source srcset>
            picture_elements = self.driver.find_elements("css selector", "picture media-image, picture")
            for picture in picture_elements:
                sources = picture.find_elements("css selector", "source")
                for source in sources:
                    srcset = source.get_attribute("srcset")
                    if srcset:
                        # Берём первый URL из srcset (максимальное качество)
                        first_url = srcset.split(',')[0].split(' ')[0]
                        if first_url and 'zara.net' in first_url:
                            clean_url = first_url.split('?')[0]
                            clean_url = re.sub(r'/w/\d+/', '/w/1920/', clean_url)
                            if clean_url not in images:
                                images.append(clean_url)

            # 🔐 ШАГ 3: Обычные <img> теги
            elements = self.driver.find_elements("css selector", "img")
            for elem in elements:
                src = (
                    elem.get_attribute("data-src") or
                    elem.get_attribute("data-original") or
                    elem.get_attribute("src")
                )

                if not src or len(src) <= 20:
                    continue

                clean_url = src.split('?')[0]
                if 'zara.net' in clean_url:
                    clean_url = re.sub(r'/w/\d+/', '/w/1920/', clean_url)

                if self._is_valid_product_image(clean_url):
                    if clean_url not in images:
                        images.append(clean_url)

            # 🔐 ШАГ 4: CSS background-image (fallback)
            if len(images) < 3:
                logger.debug("🔐 Мало изображений, ищем background-image...")
                all_elements = self.driver.find_elements("css selector", "*")
                for el in all_elements[:100]:
                    try:
                        style = el.get_attribute("style")
                        if style and 'background-image' in style:
                            bg_match = re.search(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', style)
                            if bg_match:
                                bg_url = bg_match.group(1)
                                if 'zara.net' in bg_url:
                                    clean_url = bg_url.split('?')[0]
                                    clean_url = re.sub(r'/w/\d+/', '/w/1920/', clean_url)
                                    if self._is_valid_product_image(clean_url) and clean_url not in images:
                                        images.append(clean_url)
                    except:
                        pass

            # Берём первые 10 изображений
            images = images[:10]

            logger.info(f"Extracted {len(images)} product images from DOM")

        except Exception as e:
            logger.error(f"Image extraction error: {e}")

        return images

    async def parse_category(self, url: str, max_products: int = 30, offset: int = 0) -> List[dict]:
        """
        Парсит категорию через DOM + AI Vision (гибридный подход) с прогрессом.
        🔐 OFFSET: Прокручивает страницу мимо offset товаров перед сбором данных
        🔐 АВТО-ВОСКРЕШЕНИЕ: Превентивный рестарт браузера при глубокой пагинации
        🔐 WINDOWED MODE: Для Nykaa открываем окно (не headless)

        Args:
            url: URL категории
            max_products: Максимальное количество товаров для сбора
            offset: Количество товаров для пропуска (смещение)
        """
        logger.info("=" * 60)
        logger.info("🚀 Selenium + DOM + AI Vision: Category parsing")
        logger.info(f"📍 Offset: {offset} | Max products: {max_products}")
        logger.info("=" * 60)

        # 🔐 ПРОВЕРКА: Если Nykaa — используем undetected-chromedriver
        is_nykaa = 'nykaafashion.com' in url or 'nykaa.com' in url
        if is_nykaa:
            # 🔐 ПЕРЕЗАПУСКАЕМ БРАУЗЕР С UNDETECTED
            if self.driver:
                logger.info("🔐 Nykaa detected: Restarting with undetected-chromedriver")
                self.stop()
                time.sleep(2)
            self.start(force_windowed=False, use_undetected=True)
        elif not self.driver:
            self.start()

        # 🔐 АВТО-ВОСКРЕШЕНИЕ: Превентивный рестарт при глубокой пагинации
        # Каждые 30 товаров (offset кратен 30) перезапускаем браузер для очистки памяти
        if offset > 0 and offset % 30 == 0:
            logger.info(f"🔐 Deep pagination detected (offset={offset}). Preventive browser restart...")
            self.restart_browser()
            logger.info("✅ Browser restarted. Continuing with clean memory.")

        # 1. Загружаем страницу категории и делаем скриншот
        logger.info("📸 Loading category page...")
        page_text, screenshot = self.load_page(url)

        logger.info(f"Page loaded: {len(page_text)} chars, Screenshot: {len(screenshot) / 1024:.1f} KB")

        # 2. 🔐 УМНЫЙ СКРОЛЛИНГ С OFFSET: Крутим пока не пропустим offset и не загрузится max_products
        logger.info(f"📸 Smart scrolling: offset={offset}, target={max_products} products...")
        await self._smart_scroll_to_load_products(max_products, offset)

        # 3. ТОЛЬКО ТЕПЕРЬ извлекаем DOM pairs (после скролла на нужную позицию!)
        logger.info("🔗 Extracting DOM product pairs...")
        dom_pairs = self._extract_dom_product_pairs()
        logger.info(f"🔗 DOM extracted {len(dom_pairs)} perfect URL+Image pairs")

        # 🔐 Если DOM не нашёл пары — пробуем AI Vision как fallback
        if len(dom_pairs) < 5:
            logger.warning("⚠️ DOM found less than 5 products, trying AI Vision fallback...")
            # Делаем скриншоты для AI (после скроллинга!)
            logger.info("📸 Taking screenshots for AI analysis...")
            screenshots = await self._take_multiple_screenshots()
            logger.info(f"✅ Taken {len(screenshots)} screenshots")

            # Объединяем скриншоты
            all_screenshots = [screenshot] + screenshots
            logger.info(f"📊 Total screenshots for AI: {len(all_screenshots)} (1 initial + {len(screenshots)} scroll)")

            # AI Vision анализирует ВСЕ скриншоты
            logger.info("🤖 AI Vision: Analyzing category screenshots...")
            all_category_products = []

            for i, scr in enumerate(all_screenshots, 1):
                logger.info(f"📊 Analyzing screenshot {i}/{len(all_screenshots)}...")
                category_products = await self._parse_category_via_ai_vision(url, page_text, scr, [], max_products)
                if category_products:
                    all_category_products.extend(category_products)
                    logger.info(f"✅ Screenshot {i}: {len(category_products)} products")

            # Удаляем дубликаты из AI
            seen_titles = set()
            category_products = []
            for product in all_category_products:
                title = product.get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    category_products.append(product)

            logger.info(f"✅ AI Vision parsed {len(category_products)} unique products (from {len(all_category_products)} total)")

            # ВАЛИДАЦИЯ ДАННЫХ ТОВАРОВ
            logger.info("🔍 Validating product data...")
            validated_products = batch_validate_products(category_products[:max_products])
            return validated_products

        # 🔐 DOM нашёл достаточно товаров — используем быстрый режим
        # 🔐 ОПТИМИЗАЦИЯ: Парсим только max_products товаров (быстрее)
        logger.info(f"✅ DOM mode: {len(dom_pairs)} products found, extracting details (offset: {offset}, limit: {max_products})...")

        # 🔐 ИСПРАВЛЕНО: Правильный срез с учётом offset
        # Было: dom_pairs[:max_products] — игнорировало offset!
        # Стало: dom_pairs[offset : offset + max_products] — корректное смещение

        # 🔐 ПРОВЕРКА: Если offset слишком большой, уменьшаем до 0
        if offset >= len(dom_pairs):
            logger.warning(f"⚠️ Offset {offset} >= {len(dom_pairs)} products available. Resetting offset to 0.")
            offset = 0

        target_pairs = dom_pairs[offset : offset + max_products]

        # Проверка на пустой результат (если offset больше количества ссылок)
        if not target_pairs:
            logger.warning(f"⚠️ Offset {offset} больше количества найденных товаров ({len(dom_pairs)})")
            logger.info("=" * 60)
            return []

        logger.info(f"📦 Selected products {offset+1} to {offset+len(target_pairs)} (total available: {len(dom_pairs)})")

        products = []
        for i, dom_pair in enumerate(target_pairs, 1):
            logger.info(f"🔍 Parsing product {i}/{len(target_pairs)}: {dom_pair['url'][-50:]}")

            # Переходим на страницу товара для извлечения данных
            try:
                product_data = await self._parse_product_from_dom_pair(dom_pair)
                if product_data:
                    products.append(product_data)
                    logger.info(f"✅ Parsed: {product_data['title'][:50]} - ₹{product_data['price_inr']}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse {dom_pair['url']}: {e}")
                continue

        logger.info(f"✅ Total: {len(products)} products parsed from DOM")
        logger.info("=" * 60)

        return products

    async def _parse_product_from_dom_pair(self, dom_pair: dict) -> Optional[dict]:
        """
        🔐 Быстрый парсинг товара из DOM пары (URL + Images).
        Переходит на страницу товара и извлекает данные через AI Vision.
        """
        try:
            url = dom_pair['url']
            dom_images = dom_pair.get('images', [])

            # Загружаем страницу товара
            page_text, screenshot = self.load_page(url)

            # 🔐 ИСПРАВЛЕНО: extract_product_sync - синхронный метод (не требует await)
            product_data = self.openrouter.extract_product_sync(
                url=url,
                page_text=page_text,
                screenshot=screenshot,
            )

            # 🔐 ИСПОЛЬЗУЕМ ИЗОБРАЖЕНИЯ ОТ AI (они правильные)
            ai_images = product_data.images if product_data.images else []
            if not ai_images and product_data.image_url:
                ai_images = [product_data.image_url]

            # 🔐 AI ВЫБОР ЛУЧШИХ ИЗОБРАЖЕНИЙ (фильтрует SVG, выбирает ракурсы)
            all_images = ai_images if ai_images else dom_images
            if all_images and len(all_images) > 3:
                # Если больше 3 фото, AI выберет лучшие
                best_images = await self.openrouter.select_best_images(
                    images=all_images,
                    product_title=product_data.title
                )
                logger.info(f"🤖 AI selected {len(best_images)} best images from {len(all_images)}")
            else:
                best_images = all_images[:5]

            return {
                "source_url": url,
                "title": product_data.title,
                "price_inr": product_data.price_inr,
                "original_price_inr": product_data.original_price_inr,
                "discount_percent": product_data.discount_percent,
                "category": product_data.category,
                "color": product_data.color,
                "in_stock": product_data.in_stock,
                "product_url": url,
                "images": best_images,
                "image_url": best_images[0] if best_images else product_data.image_url,
            }

        except Exception as e:
            logger.error(f"Error parsing product from DOM pair: {e}")
            return None

    async def _take_multiple_screenshots(self) -> List[bytes]:
        """
        Делает несколько скриншотов, плавно скролля по одному экрану вниз.
        🔐 OFFSET-FRIENDLY: Не возвращается наверх, продолжает с текущей позиции
        """
        screenshots = []
        try:
            # Получаем высоту видимого экрана (viewport)
            viewport_height = self.driver.execute_script("return window.innerHeight")

            # Делаем 3 дополнительных скрина (2, 3 и 4 экраны вниз от текущей позиции)
            for i in range(3):
                # Скроллим вниз на один экран от текущей позиции
                self.driver.execute_script(f"window.scrollBy(0, {viewport_height});")
                await asyncio.sleep(2)  # Даем время картинкам появиться (lazy load)

                # Делаем скриншот
                png_screenshot = self.driver.get_screenshot_as_png()
                screenshots.append(png_screenshot)
                logger.info(f"📸 Screenshot {i+2} taken: {len(png_screenshot) / 1024:.1f} KB")

            # 🔐 НЕ возвращаемся наверх! Позиция сохраняется для следующего вызова
            # self.driver.execute_script("window.scrollTo(0, 0)")
            logger.info(f"📸 Taken {len(screenshots)} screenshots, position saved")

        except Exception as e:
            logger.error(f"Screenshot error: {e}")

        return screenshots

    async def _smart_scroll_to_load_products(self, max_products: int = 40, offset: int = 0):
        """
        🔐 ГАРАНТИРОВАННЫЙ СКРОЛЛ: Плавно прокручивает страницу вниз,
        чтобы 100% затриггерить Lazy Load картинок для нужного количества товаров.
        """
        target_total = offset + max_products
        logger.info(f"🔐 Starting GUARANTEED smart scroll (offset: {offset}, target: {max_products})")

        try:
            # На 1 экран высотой 800px обычно помещается около 4 товаров (по 2-4 в ряд)
            # Добавляем +3 скролла "про запас" для уверенности
            scrolls_needed = (target_total // 4) + 3

            for i in range(scrolls_needed):
                # Скроллим плавно по 800 пикселей за раз
                self.driver.execute_script("window.scrollBy(0, 800);")
                await asyncio.sleep(1.5)  # Обязательная пауза для загрузки картинок Myntra

                if (i + 1) % 5 == 0 or i == 0:
                    logger.info(f"  Scroll {i+1}/{scrolls_needed} completed...")

            logger.info(f"✅ Guaranteed scroll completed ({scrolls_needed} scrolls). All lazy images should be loaded.")

        except Exception as e:
            logger.error(f"Scroll error: {e}")

    async def _parse_category_via_ai_vision(self, url: str, page_text: str, screenshot: bytes, dom_pairs: List[dict], max_products: int = 30) -> List[dict]:
        """
        AI Vision анализирует скриншот категории и извлекает все карточки товаров.
        ✅ ИСПРАВЛЕНО: Используем Smart Merge по SKU вместо индексов
        """
        try:
            # 1. Вызываем AI Vision для извлечения названий и цен
            product_data = await self.openrouter.extract_products(
                url=url,
                page_text=page_text,
                screenshot=screenshot,
            )

            # 2. УМНОЕ СОПОСТАВЛЕНИЕ по SKU (вместо индексов!)
            products = self._smart_merge(dom_pairs, product_data)

            logger.info(f"✅ Успешно смерджено {len(products)} товаров (из {len(product_data)} от AI, DOM pairs: {len(dom_pairs)})")
            return products

        except Exception as e:
            logger.error(f"AI Vision category parsing error: {e}")
            return []

    def _extract_dom_product_pairs(self) -> List[dict]:
        """
        ✅ Расширенный поиск: Извлекает URL товара и его фото.
        🔐 УЛУЧШЕНО: Множественные селекторы для Zara + Myntra + логирование прогресса
        """
        pairs = []
        seen_urls = set()

        try:
            # 🔐 ЖДЁМ РЕНДЕРИНГА: Явно ждём появления карточек товаров
            WebDriverWait(self.driver, 10).until(
                lambda d: len(d.find_elements("css selector", "a[href*='-p']")) >= 10 or
                          len(d.find_elements("css selector", "a[href*='/buy']")) >= 10  # Myntra
            )

            # 🔐 ЛОГИРОВАНИЕ: Считаем все потенциальные ссылки
            all_links = self.driver.find_elements("css selector", "a[href]")
            logger.info(f"🔍 Найдено {len(all_links)} потенциальных ссылок на странице")

            # 🔐 РАСШИРЕННЫЙ ПОИСК: Используем несколько стратегий

            # Стратегия 1: Ищем ссылки с паттерном -p01234567 (Zara)
            logger.info("🔍 Стратегия 1: Поиск ссылок с паттерном -p[0-9]{7,} (Zara)")
            elements = self.driver.find_elements("css selector", "a[href*='-p']")
            logger.info(f"   Найдено {len(elements)} ссылок с -p")

            for elem in elements:
                href = elem.get_attribute("href")
                if not href or len(href) < 30:
                    continue

                clean_url = href.split('?')[0]

                # 🔐 ФИЛЬТРЫ: Только товарные страницы
                if any(skip in clean_url.lower() for skip in ['/cat/', '/search', 'category', 'collections']):
                    continue
                # Для Zara: ищем ссылки с -p01234567 (7+ цифр после -p)
                if not re.search(r'-p\d{7,}', clean_url):
                    continue
                if clean_url in seen_urls:
                    continue

                # 🔐 ИЩЕМ КАРТИНКИ: Расширенный поиск с фолбэком
                img_urls = self._extract_images_from_element(elem)
                logger.info(f"🔐 _extract_images_from_element returned {len(img_urls)} images")

                # 🔐 ЕСЛИ НЕ НАШЛИ: Пробуем найти в родительском элементе
                if not img_urls:
                    logger.debug("🔐 No images from _extract_images_from_element, trying _extract_zara_images...")
                    try:
                        parent = elem.find_element("xpath", "./..")
                        img_urls = self._extract_zara_images(elem, parent)
                        logger.info(f"🔐 _extract_zara_images returned {len(img_urls)} images")
                    except Exception as e:
                        logger.debug(f"🔐 _extract_zara_images failed: {e}")
                        pass

                # 🔐 ЕСЛИ ВСЁ ЕЩЁ НЕ НАШЛИ: Ищем img внутри самого elem глубоко
                if not img_urls:
                    try:
                        # Ищем все img внутри элемента (глубокий поиск)
                        all_imgs = elem.find_elements("css selector", "img")
                        for img in all_imgs:
                            raw_src = (
                                img.get_attribute("data-src") or
                                img.get_attribute("src")
                            )
                            if raw_src and 'zara.net' in raw_src:
                                clean_img = raw_src.split('?')[0]
                                clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)
                                if clean_img not in img_urls and not any(skip in clean_img.lower() for skip in ['placeholder', 'icon', 'logo']):
                                    img_urls.append(clean_img)
                                    logger.debug(f"🔐 Нашли img в deep search: {clean_img[:60]}...")
                                    break  # достаточно одного изображения
                    except Exception as e:
                        logger.debug(f"Deep image search failed: {e}")

                # 🔐 ДОБАВЛЯЕМ ТОВАР (даже без изображений — AI извлечёт)
                pairs.append({
                    "url": clean_url,
                    "images": img_urls[:4] if img_urls else []
                })
                seen_urls.add(clean_url)

            # 🔐 Стратегия 1.5: Ищем ссылки Myntra (формат /1234567/buy или /1234567.html)
            logger.info("🔍 Стратегия 1.5: Поиск ссылок Myntra (формат /ID/buy или /ID.html)")
            myntra_elements = self.driver.find_elements("css selector", "a[href*='/buy']")
            logger.info(f"   Найдено {len(myntra_elements)} ссылок с /buy")

            for elem in myntra_elements:
                href = elem.get_attribute("href")
                if not href or len(href) < 20:
                    continue

                clean_url = href.split('?')[0]

                # 🔐 ФИЛЬТРЫ: Только myntra.com
                if 'myntra.com' not in clean_url.lower():
                    continue
                if any(skip in clean_url.lower() for skip in ['/cat/', '/search', 'category', 'collections', '/brand/']):
                    continue

                # Myntra: ссылки имеют формат /name/1234567/buy или /1234567.html
                myntra_match = re.search(r'/(\d{7,})(?:\.html|/buy)?', clean_url)
                if not myntra_match:
                    continue
                if clean_url in seen_urls:
                    continue

                # 🔐 ИЩЕМ КАРТИНКИ: Специализированный метод для Myntra
                img_urls = self._extract_myntra_images(elem, elem)
                logger.info(f"🔐 _extract_myntra_images returned {len(img_urls)} images")

                # 🔐 ЕСЛИ НЕ НАШЛИ: Пробуем общий метод
                if not img_urls:
                    img_urls = self._extract_images_from_element(elem)
                    logger.info(f"🔐 _extract_images_from_element returned {len(img_urls)} images")

                # 🔐 РАЗРЕШАЕМ ПАРСИНГ БЕЗ ИЗОБРАЖЕНИЙ (AI извлечёт из скриншота)
                pairs.append({
                    "url": clean_url,
                    "images": img_urls[:4] if img_urls else []
                })
                seen_urls.add(clean_url)
                logger.info(f"   ✅ Myntra товар: {clean_url[-50:]}")

            # Стратегия 2: Ищем по классам продуктов (если Zara изменит структуру)
            if len(pairs) < 50:
                logger.info(f"🔍 Стратегия 2: Поиск по классам продуктов (найдено только {len(pairs)})")
                product_classes = [
                    "a.product",
                    "a[href*='/product']",
                    ".product-grid-product a[href]",
                    ".product-item a[href]",
                    ".product-card a[href]"
                ]

                for selector in product_classes:
                    try:
                        elements = self.driver.find_elements("css selector", selector)
                        logger.info(f"   Селектор '{selector}': {len(elements)} элементов")

                        for elem in elements:
                            href = elem.get_attribute("href")
                            if not href or len(href) < 30:
                                continue

                            clean_url = href.split('?')[0]

                            if clean_url in seen_urls:
                                continue
                            if any(skip in clean_url.lower() for skip in ['/cat/', '/search', 'category', 'collections']):
                                continue

                            # 🔐 ИСПРАВЛЕНО: Поддержка Zara И Myntra
                            zara_match = re.search(r'-p\d{7,}', clean_url)
                            myntra_match = re.search(r'/(\d{7,})(?:\.html|/buy)?', clean_url) and 'myntra.com' in clean_url

                            if not zara_match and not myntra_match:
                                continue

                            # 🔐 ИЩЕМ КАРТИНКИ: Специализированный метод для Myntra
                            if myntra_match:
                                img_urls = self._extract_myntra_images(elem, elem)
                            else:
                                img_urls = self._extract_images_from_element(elem)

                            if img_urls:
                                pairs.append({
                                    "url": clean_url,
                                    "images": img_urls[:4]
                                })
                                seen_urls.add(clean_url)
                                logger.info(f"   ✅ Добавлен товар: {clean_url[-40:]}")
                    except Exception as e:
                        logger.debug(f"   Селектор {selector} не сработал: {e}")

            # Стратегия 3: Ищем все ссылки и фильтруем по URL
            if len(pairs) < 50:
                logger.info(f"🔍 Стратегия 3: Полный перебор всех ссылок (найдено только {len(pairs)})")
                all_elements = self.driver.find_elements("css selector", "a[href]")

                for elem in all_elements:
                    href = elem.get_attribute("href")
                    if not href or len(href) < 30:
                        continue

                    clean_url = href.split('?')[0]

                    if clean_url in seen_urls:
                        continue
                    if any(skip in clean_url.lower() for skip in ['/cat/', '/search', 'category', 'collections']):
                        continue

                    # 🔐 ИСПРАВЛЕНО: Поддержка Zara И Myntra
                    zara_match = re.search(r'-p\d{7,}', clean_url)
                    myntra_match = re.search(r'/(\d{7,})(?:\.html|/buy)?', clean_url) and 'myntra.com' in clean_url

                    if not zara_match and not myntra_match:
                        continue

                    # 🔐 ИЩЕМ КАРТИНКИ: Специализированный метод для Myntra
                    if myntra_match:
                        img_urls = self._extract_myntra_images(elem, elem)
                    else:
                        img_urls = self._extract_images_from_element(elem)

                    if img_urls:
                        pairs.append({
                            "url": clean_url,
                            "images": img_urls[:4]
                        })
                        seen_urls.add(clean_url)

            logger.info(f"🔗 DOM extracted {len(pairs)} perfect URL+Image pairs")
            return pairs

        except Exception as e:
            logger.error(f"DOM pair extraction error: {e}")
            return []

    def _extract_images_from_element(self, elem) -> List[str]:
        """
        🔐 Пуленепробиваемый извлекатель картинок: v0.8.8 STYLE
        ✅ Ищем в img (data-src, src)
        ✅ Ищем в CSS background-image (для Zara)
        ✅ Ищем в picture > source > srcset
        ✅ Фильтруем ТОЛЬКО товары (не фон/логотипы)
        ✅ Поддержка: Zara, Myntra, Ajio, etc.
        """
        img_urls = []
        debug_urls = []  # 🔐 ОТЛАДКА: собираем все найденные URL

        try:
            # 🔐 ШАГ 1: Ищем все img внутри elem
            all_imgs = elem.find_elements("css selector", "img")

            for img in all_imgs:
                raw_src = (
                    img.get_attribute("data-src") or
                    img.get_attribute("data-original") or
                    img.get_attribute("src")
                )

                if not raw_src:
                    continue

                debug_urls.append(f"img:{raw_src[:60]}")
                clean_img = raw_src.split('?')[0]

                # 🔐 МИНИМАЛЬНЫЙ ФИЛЬТР: только явные плейсхолдеры
                raw_src_lower = raw_src.lower()
                if any(skip in raw_src_lower for skip in ['placeholder', 'icon', 'logo', 'spinner', 'loading', 'transparent-background']):
                    debug_urls.append(f"skip_blocklist:{clean_img[:40]}")
                    continue

                # ✅ ДОБАВЛЯЕМ если это zara.net ИЛИ myntassets.com и ещё не добавлено
                if ('zara.net' in clean_img or 'myntassets.com' in clean_img) and clean_img not in img_urls:
                    img_urls.append(clean_img)
                    logger.debug(f"✅ Нашли фото: {clean_img[:60]}...")

            # 🔐 ШАГ 2: Ищем picture > source > srcset
            if len(img_urls) < 2:
                pictures = elem.find_elements("css selector", "picture")
                for picture in pictures:
                    sources = picture.find_elements("css selector", "source")
                    for source in sources:
                        srcset = source.get_attribute("srcset")
                        if srcset:
                            first_src = srcset.split(',')[0].split(' ')[0]
                            if first_src and ('zara.net' in first_src or 'myntassets.com' in first_src):
                                clean_img = first_src.split('?')[0]
                                clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)
                                if clean_img not in img_urls:
                                    img_urls.append(clean_img)
                                    logger.debug(f"✅ Picture source: {clean_img[:60]}...")

            # 🔐 ШАГ 3: Ищем CSS background-image (для Zara!)
            if len(img_urls) < 2:
                # Ищем элементы с style="background-image: url(...)"
                all_elements = elem.find_elements("css selector", "*")
                for el in all_elements[:50]:  # Ограничиваем 50 элементами
                    try:
                        style = el.get_attribute("style")
                        if style and 'background-image' in style:
                            # Извлекаем URL из background-image: url("...")
                            bg_match = re.search(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', style)
                            if bg_match:
                                bg_url = bg_match.group(1)
                                debug_urls.append(f"bg:{bg_url[:60]}")
                                if 'zara.net' in bg_url or 'myntassets.com' in bg_url:
                                    clean_img = bg_url.split('?')[0]
                                    clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)
                                    if clean_img not in img_urls:
                                        img_urls.append(clean_img)
                                        logger.debug(f"✅ Background: {clean_img[:60]}...")
                    except:
                        pass

        except Exception as e:
            logger.debug(f"Image extraction failed: {e}")

        # 🔐 ОТЛАДКА: логируем если не нашли изображения
        if not img_urls:
            logger.debug(f"🔐 Debug URLs (first 5): {debug_urls[:5]}")

        if not img_urls:
            logger.warning("⚠️ No valid images found (all filtered out)")
        else:
            logger.info(f"✅ Extracted {len(img_urls)} valid images")

        return img_urls


    def _extract_zara_images(self, elem, parent) -> List[str]:
        """
        🔐 ИЗОБРАЖЕНИЯ ZARA: Улучшенная версия v1.1.1
        ✅ Ищем изображения в picture/source/img элементах
        ✅ Поддержка lazy load (data-src, data-srcset)
        ✅ Прокрутка страницы для загрузки lazy images
        ✅ Извлечение из JavaScript (window.__PRELOADED_STATE__)
        """
        img_urls = []

        try:
            # 🔐 ШАГ 1: Прокручиваем страницу для загрузки lazy images
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            import time
            time.sleep(2)  # Ждем загрузки изображений
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            # 🔐 ШАГ 2: Ищем все picture/img в elem и parent
            pictures = parent.find_elements("css selector", "picture") + elem.find_elements("css selector", "picture")
            imgs = parent.find_elements("css selector", "img") + elem.find_elements("css selector", "img")

            # 🔐 Извлекаем из picture > source
            for picture in pictures:
                sources = picture.find_elements("css selector", "source")
                for source in sources:
                    srcset = source.get_attribute("srcset")
                    src = source.get_attribute("src")
                    
                    # 🔐 Пробуем data-srcset для lazy load
                    if not srcset:
                        srcset = source.get_attribute("data-srcset")
                    if not src:
                        src = source.get_attribute("data-src")

                    if srcset:
                        # Берём первый URL из srcset
                        first_src = srcset.split(',')[0].split(' ')[0]
                        if first_src and 'zara.net' in first_src:
                            clean_img = first_src.split('?')[0]
                            clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)
                            if clean_img not in img_urls:
                                img_urls.append(clean_img)

                    if src and 'zara.net' in src:
                        clean_img = src.split('?')[0]
                        clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)
                        if clean_img not in img_urls:
                            img_urls.append(clean_img)

            # 🔐 Извлекаем из img (data-src, data-original, src)
            for img in imgs:
                raw_src = (
                    img.get_attribute("data-src") or
                    img.get_attribute("data-original") or
                    img.get_attribute("src") or
                    img.get_attribute("data-srcset")
                )

                if not raw_src:
                    continue

                # 🔐 Для srcset берем первый URL
                if 'srcset' in raw_src.lower():
                    raw_src = raw_src.split(',')[0].split(' ')[0]

                clean_img = raw_src.split('?')[0]

                # 🔐 ТОЛЬКО zara.net
                if 'zara.net' not in clean_img:
                    continue

                # 🔐 ЧЕРНЫЙ СПИСОК
                raw_src_lower = raw_src.lower()
                if any(skip in raw_src_lower for skip in [
                    'placeholder', 'icon', 'logo', 'bg-', 'background',
                    'transparent', 'empty', 'null', 'loading', 'spinner'
                ]):
                    continue

                # 🔐 ЗАМЕНЯЕМ РАЗРЕШЕНИЕ на 1920
                clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)

                if clean_img not in img_urls:
                    img_urls.append(clean_img)

            # 🔐 ШАГ 3: Если не нашли, пробуем извлечь из JavaScript
            if not img_urls:
                try:
                    script = """
                        var imgs = [];
                        document.querySelectorAll('img').forEach(function(img) {
                            var src = img.src || img.getAttribute('data-src') || img.getAttribute('data-original');
                            if (src && src.indexOf('zara.net') > -1) {
                                imgs.push(src);
                            }
                        });
                        return imgs;
                    """
                    js_images = self.driver.execute_script(script)
                    for js_img in js_images:
                        clean_img = js_img.split('?')[0]
                        clean_img = re.sub(r'/w/\d+/', '/w/1920/', clean_img)
                        if clean_img not in img_urls and 'placeholder' not in clean_img.lower():
                            img_urls.append(clean_img)
                except Exception as e:
                    logger.debug(f"JS extraction failed: {e}")

        except Exception as e:
            logger.debug(f"Zara extraction failed: {e}")

        logger.info(f"✅ Zara: extracted {len(img_urls)} images")
        return img_urls


    def _extract_myntra_images(self, elem, parent) -> List[str]:
        """
        🔐 ИЗОБРАЖЕНИЯ MYNTRA: Извлечение из <source> и img
        ✅ Поддержка webp через srcset
        """
        img_urls = []

        try:
            # Стратегия 1: Обычные <img>
            imgs = parent.find_elements("css selector", "img") + elem.find_elements("css selector", "img")

            for img in imgs:
                raw_src = (
                    img.get_attribute("data-src") or
                    img.get_attribute("data-original") or
                    img.get_attribute("src")
                )

                if not raw_src:
                    continue

                raw_src_lower = raw_src.lower()
                if any(skip in raw_src_lower for skip in ['placeholder', 'icon', 'logo', 'transparent']):
                    continue

                clean_img = raw_src.split('?')[0]

                # 🔐 ТОЛЬКО myntassets.com
                if 'myntassets.com' not in clean_img:
                    continue

                if clean_img not in img_urls:
                    img_urls.append(clean_img)

            # Стратегия 2: <source srcset> для webp
            try:
                sources = parent.find_elements("css selector", "source") + elem.find_elements("css selector", "source")

                for source in sources:
                    srcset = source.get_attribute("srcset")

                    if srcset:
                        # Берем первую ссылку до запятой/пробела
                        raw_src = srcset.split(',')[0].strip().split(' ')[0]

                        if raw_src.startswith("data:image/"):
                            continue

                        clean_img = raw_src.split('?')[0]

                        if 'myntassets.com' in clean_img and clean_img not in img_urls:
                            img_urls.append(clean_img)
                            logger.info(f"✅ Myntra webp added: {clean_img[:80]}...")

            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Myntra extraction failed: {e}")

        return img_urls


# Глобальный экземпляр
selenium_stealth_service = SeleniumStealthService()
