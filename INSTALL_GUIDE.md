# 📖 IndiaShop Bot v1.2.0 — Инструкция по получению API ключей

**Последнее обновление:** 2026-03-23  
**Время настройки:** 10-15 минут

---

## 🔑 ЧТО НУЖНО ПОЛУЧИТЬ

| Ключ | Где получить | Время | Обязательно |
|------|--------------|-------|-------------|
| **BOT_TOKEN** | Telegram @BotFather | 3 мин | ✅ Да |
| **OPENROUTER_API_KEY** | https://openrouter.ai | 5 мин | ✅ Да |
| **ADMIN_TELEGRAM_IDS** | Telegram @userinfobot | 1 мин | ✅ Да |
| **GITHUB_TOKEN** | GitHub Settings | 3 мин | ❌ Нет |

---

## 1️⃣ TELEGRAM BOT TOKEN

### Шаг 1: Откройте @BotFather

1. В Telegram найдите **@BotFather** (официальный бот для создания ботов)
2. Нажмите **Start** или напишите `/start`

### Шаг 2: Создайте нового бота

1. Напишите команду `/newbot`
2. BotFather попросит придумать **имя бота** (отображается в списке чатов)
   - Пример: `IndiaShop Reseller`
3. Теперь придумайте **username бота** (уникальный, заканчивается на `bot`)
   - Пример: `MyIndiaShop_bot`
   - ⚠️ Если username занят, попробуйте другой

### Шаг 3: Скопируйте токен

BotFather создаст бота и покажет токен:

```
Done! Congratulations on your new bot!
You can find it at t.me/MyIndiaShop_bot

Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Скопируйте токен** (строка после `Token:`) и вставьте в `.env`:

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### ⚙️ Настройки бота (опционально)

В @BotFather:
- `/setuserpic` — установить аватарку
- `/setdescription` — описание бота
- `/setabouttext` — текст "О боте"

---

## 2️⃣ OPENROUTER API KEY

### Шаг 1: Зарегистрируйтесь

1. Перейдите на https://openrouter.ai/keys
2. Нажмите **Sign In**
3. Войдите через **Google** или **GitHub** (рекомендуется)

### Шаг 2: Создайте API ключ

1. Нажмите кнопку **"Create Key"**
2. Введите название ключа (любое)
   - Пример: `IndiaShop Bot`
3. Нажмите **"Create"**

### Шаг 3: Скопируйте ключ

Откроется окно с ключом:

```
sk-or-v1-abcdef1234567890abcdef1234567890abcdef1234567890
```

**⚠️ ВАЖНО:** Скопируйте ключ сразу! Он показывается только один раз.

Вставьте ключ в `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-abcdef1234567890abcdef1234567890abcdef1234567890
```

### 💰 Тарифы OpenRouter

- **Бесплатно:** $0.50 кредитов при регистрации
- **Пополнение:** от $5 через карту/crypto
- **Расходы:** ~$0.01-0.05 на 100 товаров (парсинг + AI)

**Рекомендуемая модель:** `google/gemini-3.1-flash-lite-preview`
- Быстрая и дешёвая
- Хорошо распознаёт товары с Zara, Myntra, Ajio

---

## 3️⃣ TELEGRAM ID (ADMIN_TELEGRAM_IDS)

### Способ 1: Через @userinfobot (рекомендуется)

1. В Telegram найдите **@userinfobot**
2. Нажмите **Start**
3. Бот покажет ваш ID:

```
Your Telegram ID: 123456789
```

Скопируйте ID и вставьте в `.env`:

```env
ADMIN_TELEGRAM_IDS=123456789
```

### Способ 2: Через @BotFather

1. Напишите @BotFather
2. Отправьте любое сообщение боту
3. Посмотрите URL сообщения: `https://t.me/BotFather/123`
4. Ваш ID — это число перед `/123`

### Для нескольких админов

Разделяйте запятыми (без пробелов):

```env
ADMIN_TELEGRAM_IDS=123456789,987654321
```

---

## 4️⃣ GITHUB TOKEN (опционально)

Нужен только если планируете интеграцию с GitHub.

### Шаг 1: Откройте настройки

1. Перейдите на https://github.com/settings/tokens
2. Войдите в свой аккаунт GitHub

### Шаг 2: Создайте токен

1. Нажмите **"Generate new token (classic)"**
2. Введите **Note:** `IndiaShop Bot`
3. Выберите **Scope:** ✅ `repo` (полный доступ к репозиториям)
4. Нажмите **"Generate token"**

### Шаг 3: Скопируйте токен

```
ghp_abcdefghijklmnopqrstuvwxyz123456
```

Вставьте в `.env`:

```env
GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz123456
```

---

## ✅ ПРОВЕРКА НАСТРОЕК

После заполнения `.env`:

1. Откройте файл `.env`
2. Проверьте что заполнены:
   ```env
   BOT_TOKEN=123456789:ABCdef...
   OPENROUTER_API_KEY=sk-or-v1-...
   ADMIN_TELEGRAM_IDS=123456789
   ```
3. Сохраните файл
4. Запустите `START.bat`

---

## 🐛 ЧАСТЫЕ ПРОБЛЕМЫ

### ❌ "BOT_TOKEN не найден"

**Решение:**
- Откройте `.env`
- Убедитесь что нет пробелов вокруг `=`
- Проверьте что токен начинается с цифр

### ❌ "OPENROUTER_API_KEY недействителен"

**Решение:**
- Проверьте что ключ начинается с `sk-or-v1-`
- Убедитесь что нет лишних пробелов
- Проверьте баланс на https://openrouter.ai/keys

### ❌ "Доступ запрещён"

**Решение:**
- Проверьте `ADMIN_TELEGRAM_IDS`
- Убедитесь что указали свой ID
- Перезапустите бота (`STOP.bat` → `START.bat`)

---

## 📞 ПОДДЕРЖКА

Если возникли проблемы:

1. Проверьте логи: `bot.log`
2. Напишите в поддержку: **@tatastu** (Telegram)

---

**Готово!** Теперь запустите `START.bat` для запуска бота.
