# 📊 INDIA SHOP BOT — СТРУКТУРА УРОВНЕЙ ДОСТУПА

**Версия:** 1.1 FIXED  
**Дата:** 2026-03-17  
**Статус:** ✅ Актуально

---

## 🏗️ АРХИТЕКТУРА УРОВНЕЙ ДОСТУПА

```
┌─────────────────────────────────────────────────┐
│                 УРОВЕНЬ 1: АДМИН                │
│  • Полный доступ ко всем функциям               │
│  • Настройки бота, менеджеры, БД, кэш           │
│  • Парсинг, публикация, редактирование          │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│                УРОВЕНЬ 2: МЕНЕДЖЕР              │
│  • Просмотр товаров, карточка товара            │
│  • Публикация, редактирование                   │
│  • Обработка запросов клиентов                  │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│                УРОВЕНЬ 3: КЛИЕНТ                │
│  • (В РАЗРАБОТКЕ) Просмотр каталога             │
│  • (В РАЗРАБОТКЕ) Корзина, заказы               │
│  • (В РАЗРАБОТКЕ) Связь с менеджером            │
└─────────────────────────────────────────────────┘
```

---

## 👑 УРОВЕНЬ 1: АДМИН

### Кто имеет доступ

```python
# app/core/config.py
admin_ids: List[int] = [5935993156]  # Telegram ID админов

# Проверка в коде:
if message.from_user.id not in settings.admin_ids:
    return  # Доступ запрещён
```

### Доступные функции

| Функция | Описание | Файл |
|---------|----------|------|
| **📦 Парсинг товара** | Парсинг одиночного URL | `admin_parse.py` |
| **📊 Парсинг категории** | Массовый парсинг (DOM + AI) | `admin_parse.py` |
| **📦 Товары** | Просмотр, редактирование, удаление | `admin_products.py` |
| **📢 Автопостинг** | Настройка расписания | `admin_posting.py` |
| **⚙️ Настройки** | Курс, маржа, доставка | `admin_settings.py` |
| **👥 Менеджеры** | Добавление, удаление | `admin_managers.py` |
| **💾 Кэш** | Очистка, просмотр | `admin_cache.py` |
| **🗑 Очистка БД** | Полная очистка базы | `admin_db.py` |

### Команды админа

```
/start — Главное меню
/admin — Админ-панель
/find <ID> — Найти товар по ID
/cache — Управление кэшем
/version — Версия бота
/cancel — Отмена
```

### Пример проверки доступа

```python
# app/bots/handlers/admin_products.py
@router.message(F.text == "📦 Товары")
async def admin_products_text(message: Message, state: FSMContext):
    """📦 Обработка кнопки 'Товары' — Админы и Менеджеры"""
    await state.clear()

    user_id = message.from_user.id
    is_admin = user_id in settings.admin_ids
    
    # Проверка на менеджера (если не админ)
    is_manager = False
    if not is_admin:
        async with database.get_session() as session:
            from app.db.repositories import ManagerRepository
            repo = ManagerRepository(session)
            managers = await repo.get_all_active()
            is_manager = any(m.telegram_id == str(user_id) for m in managers)

    if not is_admin and not is_manager:
        return  # Доступ запрещён

    logger.info(f"{'Manager' if is_manager else 'Admin'} {user_id} clicked 'Товары'")
    # ... логика
```

---

## 👔 УРОВЕНЬ 2: МЕНЕДЖЕР

### Кто имеет доступ

```python
# app/db/models.py
class Manager(Base):
    __tablename__ = "managers"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)  # Telegram ID
    username = Column(String)  # @username
    is_active = Column(Boolean, default=True)
```

### Как добавить менеджера

1. Админ нажимает: `👥 Менеджеры` → `➕ Добавить`
2. Отправляет username менеджера (например, `@manager_bot`)
3. Менеджер сохраняется в БД

### Доступные функции

| Функция | Описание | Файл |
|---------|----------|------|
| **📦 Товары** | Просмотр списка товаров | `admin_products.py` |
| **👁️ Карточка товара** | Просмотр + кнопки | `admin_products.py` |
| **📤 Опубликовать** | Публикация в канал | `admin_products.py` |
| **✏️ Редактировать** | Название, цена, описание | `admin_products.py` |
| **🔍 Поиск по ID** | Найти товар | `start.py` |
| **📞 Помощь** | Связь с поддержкой | `start.py` |

### НЕдоступные функции

| Функция | Почему |
|---------|--------|
| **📊 Парсинг категории** | Только админ |
| **⚙️ Настройки** | Только админ |
| **👥 Менеджеры** | Только админ |
| **💾 Кэш** | Только админ |
| **🗑 Очистка БД** | Только админ |

### Главное меню менеджера

```python
# app/bots/handlers/start.py
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Главное меню + проверка на менеджера"""
    
    # Проверка на менеджера
    async with database.get_session() as session:
        from app.db.repositories import ManagerRepository
        repo = ManagerRepository(session)
        managers = await repo.get_all_active()
        is_manager = any(m.telegram_id == str(message.from_user.id) for m in managers)

    if is_manager:
        await message.answer(
            "🏠 <b>Меню менеджера</b>\n\n"
            "Выберите раздел:",
            reply_markup=get_manager_keyboard(),
            parse_mode="HTML",
        )
    else:
        # Обычное меню для клиентов
        await message.answer(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите раздел:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
```

### Клавиатура менеджера

```python
# app/bots/keyboards/main.py
def get_manager_keyboard() -> ReplyKeyboardMarkup:
    """🔐 Меню менеджера"""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📦 Товары"),
        KeyboardButton(text="🔍 Поиск по ID"),
    )
    builder.row(
        KeyboardButton(text="📞 Помощь"),
    )

    return builder.as_markup(resize_keyboard=True)
```

### Карточка товара для менеджера

```python
# app/bots/handlers/manager.py
async def send_product_card(message: Message, product_id: int):
    """Отправляет карточку товара менеджеру"""
    
    # ... получение товара из БД
    
    # 🔐 КНОПКИ ССЫЛОК (фото и оригинал)
    link_buttons = []
    if product.images:
        images = json.loads(product.images) if isinstance(product.images, str) else product.images
        if images and images[0].startswith('http'):
            link_buttons.append(InlineKeyboardButton(text="🖼 Фото товара", url=images[0]))
    
    if product.source_url:
        link_buttons.append(InlineKeyboardButton(text="🔗 Оригинал", url=product.source_url))
    
    if link_buttons:
        keyboard.row(*link_buttons)

    keyboard.row(
        InlineKeyboardButton(text="📤 Опубликовать", callback_data=f"product_publish:{product.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"product_edit:{product.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 В админку", callback_data="admin_back")
    )
```

---

## 🛒 УРОВЕНЬ 3: КЛИЕНТ

### Статус: В РАЗРАБОТКЕ ⏳

### Планируемые функции

| Функция | Описание | Статус |
|---------|----------|--------|
| **🛍 Каталог** | Просмотр товаров | ⏳ В разработке |
| **🔍 Поиск** | Поиск по названию/ID | ⏳ В разработке |
| **🛒 Корзина** | Добавление товаров | ⏳ В разработке |
| **📦 Заказ** | Оформление заказа | ⏳ В разработке |
| **📞 Менеджер** | Связь с менеджером | ✅ Готово (кнопка) |

### Текущий функционал

```python
# app/bots/handlers/start.py
@router.message(F.text == "👋 Привет")
async def say_hello(message: Message):
    """Приветствие для клиентов"""
    version = get_full_version()
    await message.answer(
        f"👋 <b>Привет!</b>\n\n"
        f"Я бот IndiaShop <b>{version}</b>.\n"
        f"Сейчас я нахожусь в разработке, но скоро смогу помочь вам с покупками!",
        parse_mode="HTML",
    )
```

### Клавиатура клиента

```python
# app/bots/keyboards/main.py
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню пользователя (клиента)"""
    builder = ReplyKeyboardBuilder()

    # ⚠️ Пользовательские кнопки скрыты до реализации
    builder.row(
        KeyboardButton(text="👋 Привет"),
        KeyboardButton(text="📞 Помощь"),
    )

    return builder.as_markup(resize_keyboard=True)
```

---

## 🔐 МЕХАНИЗМ ПРОВЕРКИ ДОСТУПА

### Схема проверки

```python
# 1. Проверяем админа
is_admin = user_id in settings.admin_ids

if is_admin:
    # Полный доступ
    return

# 2. Проверяем менеджера
is_manager = False
async with database.get_session() as session:
    repo = ManagerRepository(session)
    managers = await repo.get_all_active()
    is_manager = any(m.telegram_id == str(user_id) for m in managers)

if is_manager:
    # Доступ менеджера
    return

# 3. Клиент (нет доступа к админ-функциям)
return  # Доступ запрещён
```

### Логирование

```python
logger.info(f"{'Manager' if is_manager else 'Admin'} {user_id} clicked 'Товары'")
```

---

## 📊 СРАВНЕНИЕ УРОВНЕЙ

| Функция | Админ | Менеджер | Клиент |
|---------|-------|----------|--------|
| **Парсинг товара** | ✅ | ❌ | ❌ |
| **Парсинг категории** | ✅ | ❌ | ❌ |
| **Просмотр товаров** | ✅ | ✅ | ⏳ |
| **Карточка товара** | ✅ | ✅ | ⏳ |
| **Публикация** | ✅ | ✅ | ❌ |
| **Редактирование** | ✅ | ✅ | ❌ |
| **Настройки** | ✅ | ❌ | ❌ |
| **Менеджеры** | ✅ | ❌ | ❌ |
| **Кэш** | ✅ | ❌ | ❌ |
| **БД** | ✅ | ❌ | ❌ |
| **Корзина** | ❌ | ❌ | ⏳ |
| **Заказы** | ❌ | ❌ | ⏳ |

---

## 🎯 ПЛАНЫ РАЗВИТИЯ

### Уровень 1: Админ (готово ✅)

- [x] Парсинг товара/категории
- [x] Управление товарами
- [x] Настройки
- [x] Менеджеры
- [x] Автопостинг

### Уровень 2: Менеджер (готово ✅)

- [x] Просмотр товаров
- [x] Карточка товара с кнопками
- [x] Публикация
- [x] Редактирование
- [x] Поиск по ID

### Уровень 3: Клиент (в разработке ⏳)

- [ ] Каталог товаров
- [ ] Поиск товаров
- [ ] Корзина
- [ ] Оформление заказа
- [ ] История заказов
- [ ] Избранное

---

## 📋 БАЗА ДАННЫХ

### Таблица `managers`

```sql
CREATE TABLE managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT UNIQUE NOT NULL,
    username TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Репозиторий

```python
# app/db/repositories.py
class ManagerRepository:
    async def get_all_active(self) -> List[Manager]:
        """Получить всех активных менеджеров"""
        result = await self.session.execute(
            select(Manager).where(Manager.is_active == True)
        )
        return result.scalars().all()
    
    async def add(self, telegram_id: str, username: str) -> Manager:
        """Добавить менеджера"""
        manager = Manager(telegram_id=telegram_id, username=username)
        self.session.add(manager)
        await self.session.commit()
        return manager
```

---

## 🔧 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Добавление менеджера (админ)

```
1. /admin → 👥 Менеджеры
2. ➕ Добавить
3. Отправить: @manager_username
4. ✅ Менеджер добавлен!
```

### Вход менеджера

```
1. /start
2. Бот проверяет: is_manager = True
3. Показывает: "🏠 Меню менеджера"
4. Кнопки: 📦 Товары, 🔍 Поиск по ID, 📞 Помощь
```

### Обработка запроса клиента (менеджер)

```
1. Клиент пишет менеджеру
2. Менеджер отправляет: /find 123
3. Бот показывает карточку товара #123
4. Менеджер нажимает: 📤 Опубликовать
5. Товар публикуется в канал
```

---

## 📞 КОНТАКТЫ

**Админ:** @tatastu  
**Менеджер:** @tatastu_support  
**Канал:** @tatastutest  
**Бот:** @tatastu_bot

---

**Последнее обновление:** 2026-03-17  
**Версия документа:** 1.1 FIXED
