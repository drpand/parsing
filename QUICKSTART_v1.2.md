# 🚀 Быстрый старт — IndiaShop Bot v1.2

## ✅ Что нового в v1.2

- **50+ категорий товаров** — обувь, одежда, сумки, аксессуары, красота
- **Фильтры в каталоге** — выбор категории с подсчётом товаров
- **Subcategories** — автоматическая группировка внутри категорий
- **Supabase опционален** — бот работает на SQLite без дополнительных настроек

---

## 📋 Быстрый запуск

### 1. Проверка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка .env

Файл `.env` уже настроен! Проверьте только:

```env
BOT_TOKEN=ваш_токен
ADMIN_TELEGRAM_IDS=ваш_id
OPENROUTER_API_KEY=ваш_ключ
```

**Supabase не нужен** — оставьте поля пустыми:
```env
SUPABASE_URL=
SUPABASE_KEY=
```

### 3. Запуск бота

```bash
python main.py
```

Или через .bat (Windows, с автоперезапуском):
```bash
start_bot.bat
```

---

## 🧪 Тестирование категорий

### 1. Откройте каталог

В боте нажмите: **🛍 Каталог**

### 2. Выберите категорию

Вы увидите кнопки:
```
📂 ——— КАТЕГОРИИ ———
✅ 🛍️ Все товары (125) | 👔 Мужское (30)
👗 Женское (55)        | 👟 Обувь (20)
👜 Сумки (12)          | 💍 Аксессуары (8)
```

### 3. Проверьте подкатегории

При выборе категории показываются подкатегории:
```
👟 Обувь
📊 Найдено: 20 товаров

📂 Подкатегории:
  • Sneakers (8)
  • Sandals (5)
  • Boots (4)
  • Formal (3)
```

---

## 🤖 Парсинг с новыми категориями

### 1. Откройте админ-панель

```
/admin → Парсинг → Категория
```

### 2. Введите URL категории

Примеры:
- Myntra Men Clothing: `https://www.myntra.com/men-clothing`
- Zara Women Dresses: `https://www.zara.com/in/en/woman-dresses-l1056.html`
- Ajio Shoes: `https://www.ajio.com/men-shoes/c/6677`

### 3. Проверьте результат

AI автоматически определит:
- **Тип товара** (shoes_sneakers, women_dresses, men_shirts, etc.)
- **Название** и описание
- **Цену** и скидку
- **Изображения**

---

## 📊 Категории (50+ вариантов)

### 👔 Мужские (8)
- `men_shirts`, `men_tshirts`, `men_jeans`, `men_trousers`
- `men_shorts`, `men_jackets`, `men_ethnic`, `men_innerwear`

### 👗 Женские (10)
- `women_dresses`, `women_tops`, `women_tshirts`, `women_jeans`
- `women_trousers`, `women_skirts`, `women_sarees`, `women_kurtas`
- `women_jackets`, `women_ethnic`

### 👟 Обувь (7)
- `shoes_sneakers`, `shoes_sandals`, `shoes_boots`, `shoes_formal`
- `shoes_heels`, `shoes_flats`, `shoes_sports`

### 👜 Сумки (5)
- `bags_handbags`, `bags_backpacks`, `bags_clutches`, `bags_shoulder`, `bags_wallets`

### 💍 Аксессуары (7)
- `accessories_watches`, `accessories_jewelry`, `accessories_belts`
- `accessories_sunglasses`, `accessories_scarves`, `accessories_hats`, `accessories_hair`

### 🧴 Красота (4)
- `beauty_makeup`, `beauty_skincare`, `beauty_haircare`, `beauty_fragrance`

---

## 🔧 Troubleshooting

### Ошибка: "Supabase not configured"

**Это не ошибка!** Бот работает на SQLite. Supabase — опционально для кеширования.

### В каталоге 0 товаров

1. Проверьте что товары активны:
   ```
   /admin → Товары → Активные
   ```
2. Запарсите новую категорию

### AI возвращает старые категории

Проверьте лог бота — должен быть длинный промпт (~3000 символов):
```
Prompt length: 3245 chars
```

---

## 📞 Контакты

- **Бот:** @tatastu_bot
- **Канал:** @tatastutest
- **Поддержка:** @tatastu_support

---

**Версия:** v1.2.0  
**Дата:** 2026-03-20
