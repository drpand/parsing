# 🇮🇳 IndiaShop Reseller Bot v1.1

Telegram-бот для парсинга товаров с индийских маркетплейсов (Myntra, Ajio, Zara) с AI-анализом через OpenRouter API.

**Статус:** ✅ ГОТОВО К ПРОДАКШЕНУ

**Последнее обновление:** 2026-03-16

---

## 🆕 Что нового в v1.1

- ✅ **Исправлен парсинг Myntra** — изображения теперь корректно извлекаются
- ✅ **Поддержка myntassets.com** — обновлены фильтры изображений
- ✅ **Очистка проекта** — удалены старые файлы и бэкапы
- ✅ **Обновлена документация** — README, CHANGELOG, BACKUP

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка

Отредактируйте файл `.env`:

```env
# Telegram
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_TELEGRAM_IDS=your_telegram_id_here

# OpenRouter AI
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=bytedance-seed/seed-2.0-mini
```

### 3. Запуск

```bash
python main.py
```

**🔐 Process Manager:** Бот автоматически завершит предыдущий экземпляр при запуске.

### 4. Остановка

Нажмите `Ctrl+C` в терминале — бот корректно закроет сессии и удалит PID файл.

---

## 📋 Команды

### Для администраторов:
| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/admin` | Админ-панель |
| `/find` | Найти товар по ID |
| `/cache` | Управление кэшем |
| `/version` | Версия бота |

### Функции админ-панели:
- 🔍 **Парсинг** — одиночный URL или категория
- 📦 **Товары** — просмотр, редактирование, удаление
- 📢 **Постинг** — публикация в канал, автопостинг
- ⚙️ **Настройки** — курс валют, маржа, интервалы
- 💾 **Кэш** — очистка кэша
- 🗄 **БД** — управление базой данных

---

## 🏗️ Архитектура

```
app/
├── bots/
│   ├── handlers/          # Обработчики команд
│   │   ├── start.py
│   │   ├── admin_menu.py
│   │   ├── admin_parse.py
│   │   ├── admin_products.py
│   │   ├── admin_posting.py
│   │   ├── admin_settings.py
│   │   ├── admin_cache.py
│   │   ├── admin_db.py
│   │   ├── preview_product.py
│   │   └── manager.py
│   ├── keyboards/         # Inline клавиатуры
│   └── dispatcher.py      # Диспетчер
├── core/
│   ├── config.py          # Настройки (pydantic)
│   ├── version.py         # Версия бота
│   └── process_manager.py # PID менеджер
├── db/
│   ├── models.py          # SQLAlchemy модели
│   ├── database.py        # Подключение к БД
│   └── repositories.py    # Репозитории
├── services/
│   ├── selenium_service.py    # Парсинг (Selenium stealth)
│   ├── openrouter_service.py  # AI анализ (Vision API)
│   ├── poster_service.py      # Автопостинг
│   ├── product_service.py     # Логика товаров
│   ├── scheduler/
│   │   └── fx_scheduler.py    # FX курсы (готов)
│   └── proxy/
│       └── proxy_manager.py   # Прокси (готов)
└── utils/
    ├── logger.py          # Логирование
    ├── helpers.py         # Хелперы
    ├── validator.py       # Валидация URL
    └── formatters/
        └── formatters.py  # Форматтеры (готов)
```

---

## 🔧 Технологии

| Компонент | Технология |
|-----------|------------|
| **Язык** | Python 3.11+ |
| **Bot API** | Aiogram 3.x |
| **ORM** | SQLAlchemy 2.0 (async) |
| **БД** | SQLite (aiosqlite) |
| **Парсинг** | Selenium + stealth |
| **AI** | OpenRouter API (ByteDance Seed 2.0 Mini) |
| **Планировщик** | APScheduler |
| **Валидация** | Pydantic Settings |

---

## 📊 Функционал v1.0

| Функция | Статус | Описание |
|---------|--------|----------|
| **Парсинг товара** | ✅ | Одиночный URL через AI Vision |
| **Парсинг категории** | ✅ | Массовый парсинг (DOM + AI) |
| **Просмотр товаров** | ✅ | Список с пагинацией |
| **Карточка товара** | ✅ | Просмотр + навигация |
| **Редактирование** | ✅ | Название, цена, описание, наличие |
| **Удаление** | ✅ | С подтверждением |
| **Публикация в канал** | ✅ | 1 фото + 1 кнопка |
| **Автопостинг** | ✅ | По расписанию (15 мин) |
| **Настройки** | ✅ | Курс, интервал, маржа |
| **Кэширование** | ✅ | 24 часа (экономия API) |
| **Кнопка на менеджера** | ✅ | С предзаполненным сообщением |

---

## 📝 Лицензия

MIT

---

## 📞 Контакты

**Менеджер:** @tatastu  
**Канал:** @tatastutest  
**Бот:** @tatastu_bot

---

## 📋 Changelog

### v1.1 STABLE (2026-03-16)

**🔧 Исправления:**
- ✅ Myntra: изображения корректно извлекаются (`myntassets.com`)
- ✅ Парсинг категорий: изображения для Zara и Myntra
- ✅ Очистка проекта: удалены старые файлы

**📁 Файлы:**
- ✅ `app/services/selenium_service.py` — поддержка Myntra images
- ✅ `app/core/version.py` — версия v1.1.0
- ✅ `README.md`, `CHANGELOG.md` — обновлена документация

### v1.0 FINAL (2026-03-15)

**✨ Новое:**
- ✅ AI парсинг через OpenRouter (Vision API)
- ✅ Автопостинг в Telegram канал
- ✅ Админ-панель для управления товарами
- ✅ Кэширование результатов (24 часа)
- ✅ Кнопка связи с менеджером

**🔧 Исправления:**
- ✅ Постинг: 1 фото + 1 кнопка (без дублей)
- ✅ Артикул передаётся в кнопке (URL encoding)
- ✅ Редактирование работает без ошибок
- ✅ Ссылка на товар полная (не обрезается)

**📦 Зависимости:**
- ✅ Selenium + selenium-stealth + webdriver-manager
- ❌ Playwright удалён

---

**Версия 1.1 STABLE — ГОТОВА К ПРОДАКШЕНУ!** 🚀
