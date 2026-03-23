# Суперспособность: Refactoring (Рефакторинг)

## Назначение
Улучшение структуры кода без изменения его внешнего поведения.

## Когда использовать
- Код работает но сложно читать
- Дублирование в нескольких местах
- Функция слишком большая (>30 строк)
- Перед добавлением новой фичи
- После получения замечаний с code review

## Принципы рефакторинга

### Правило скаута
```
Оставляй код чище чем нашёл.
Даже одно маленькое улучшение стоит делать.
```

### Red-Green-Refactor
```
1. 🔴 Убедиться что тесты проходят
2. 🟢 Сделать рефакторинг
3. 🟡 Запустить тесты снова
4. Если тесты не прошли → откат
```

### Маленькие шаги
```
Один рефакторинг = одно изменение.
Не делать 5 изменений в одном коммите.
```

## Типы рефакторинга

### 1. Извлечение метода (Extract Method)
**До:**
```python
async def parse_product(self, url: str) -> Product:
    # Загрузка страницы
    await self.page.goto(url)
    await self.page.wait_for_load_state('networkidle')
    
    # Скриншот
    screenshot = await self.page.screenshot()
    
    # AI экстракция
    product_data = await self.openrouter.analyze(screenshot)
    
    # Создание продукта
    product = Product(
        title=product_data['title'],
        price_inr=product_data['price'],
        images=product_data['images'],
        url=url,
        marketplace='zara'
    )
    
    # Сохранение в БД
    await self.db.add(product)
    await self.db.commit()
    
    return product
```

**После:**
```python
async def parse_product(self, url: str) -> Product:
    await self.page.goto(url)
    await self.page.wait_for_load_state('networkidle')
    
    screenshot = await self.page.screenshot()
    product_data = await self.openrouter.analyze(screenshot)
    
    product = self._create_product(product_data, url)
    await self.db.add(product)
    await self.db.commit()
    
    return product

def _create_product(self, data: dict, url: str) -> Product:
    return Product(
        title=data['title'],
        price_inr=data['price'],
        images=data['images'],
        url=url,
        marketplace='zara'
    )
```

### 2. Удаление дублирования (DRY)
**До:**
```python
def extract_price_zara(text: str) -> int:
    text = text.replace("₹", "").replace(",", "")
    return int(float(text))

def extract_price_myntra(text: str) -> int:
    text = text.replace("₹", "").replace(",", "")
    return int(float(text))
```

**После:**
```python
def extract_price(text: str) -> int:
    """Извлекает цену из строки с любым форматом."""
    text = text.replace("₹", "").replace("Rs.", "")
    text = text.replace(",", "").strip()
    return int(float(text))
```

### 3. Замена магических чисел константами
**До:**
```python
async def send_message(chat_id: int, text: str):
    if len(text) > 4096:
        text = text[:4096]
    await bot.send_message(chat_id, text, parse_mode="HTML")
```

**После:**
```python
TELEGRAM_MESSAGE_LIMIT = 4096
PARSE_MODE_HTML = "HTML"

async def send_message(chat_id: int, text: str):
    if len(text) > TELEGRAM_MESSAGE_LIMIT:
        text = text[:TELEGRAM_MESSAGE_LIMIT]
    await bot.send_message(chat_id, text, parse_mode=PARSE_MODE_HTML)
```

### 4. Упрощение условий
**До:**
```python
def get_status(order):
    if order.status == "pending":
        if order.paid:
            return "processing"
        else:
            return "waiting_payment"
    elif order.status == "shipped":
        return "on_the_way"
    elif order.status == "delivered":
        return "completed"
    else:
        return "unknown"
```

**После:**
```python
STATUS_MAP = {
    "pending": {"paid": "processing", "unpaid": "waiting_payment"},
    "shipped": "on_the_way",
    "delivered": "completed",
}

def get_status(order):
    if order.status == "pending":
        key = "paid" if order.paid else "unpaid"
        return STATUS_MAP["pending"][key]
    return STATUS_MAP.get(order.status, "unknown")
```

## Шаблон рефакторинга

```markdown
## 🔧 Refactoring: [Название]

### Цель
[Что улучшаем: читаемость, производительность, тестируемость]

### Проблема
**До:**
```python
[старый код]
```

**Проблемы:**
- Проблема 1
- Проблема 2

---

### Решение

**После:**
```python
[новый код]
```

**Улучшения:**
- ✅ Улучшение 1
- ✅ Улучшение 2

---

### Тесты

```bash
pytest tests/ -v
```

**Результат:** ✅ Все тесты прошли

---

### Метрики

| Метрика | До | После |
|---------|-----|-------|
| Строк кода | 100 | 80 |
| Функция (макс) | 45 | 20 |
| Дублирование | 3 места | 0 |

---

**Готов к коммиту?**
```

## Пример рефакторинга

```markdown
## 🔧 Refactoring: Extract parse methods

### Цель
Уменьшить размер parse_product() с 80 до 25 строк

### Проблема

**До:**
```python
async def parse_product(self, url: str) -> Product:
    # 80 строк кода в одной функции
    # Загрузка, скриншот, AI, парсинг цены,
    # парсинг названия, парсинг изображений,
    # создание объекта, сохранение в БД...
```

**Проблемы:**
- Сложно тестировать
- Трудно читать
- Невозможно переиспользовать

---

### Решение

**После:**
```python
async def parse_product(self, url: str) -> Product:
    """Публичный метод парсинга."""
    await self._load_page(url)
    screenshot = await self._take_screenshot()
    data = await self._extract_with_ai(screenshot)
    product = self._create_product(data, url)
    await self._save_product(product)
    return product

async def _load_page(self, url: str):
    """Загружает страницу с ожиданием."""
    await self.page.goto(url)
    await self.page.wait_for_load_state('networkidle')

async def _take_screenshot(self) -> bytes:
    """Делает скриншот страницы."""
    return await self.page.screenshot()

async def _extract_with_ai(self, screenshot: bytes) -> dict:
    """Извлекает данные через OpenRouter AI."""
    return await self.openrouter.analyze(screenshot)

def _create_product(self, data: dict, url: str) -> Product:
    """Создаёт объект Product."""
    return Product(...)

async def _save_product(self, product: Product):
    """Сохраняет продукт в БД."""
    await self.db.add(product)
    await self.db.commit()
```

**Улучшения:**
- ✅ 80 строк → 25 строк в main методе
- ✅ Каждый метод тестируется отдельно
- ✅ Понятная ответственность каждого метода

---

### Тесты

```bash
pytest tests/test_selenium.py -v
```

**Результат:** ✅ 12/12 тестов прошли

**Новые тесты:**
- `test_load_page()`
- `test_take_screenshot()`
- `test_create_product()`

---

### Метрики

| Метрика | До | После |
|---------|-----|-------|
| Строк в parse_product | 80 | 25 |
| Количество методов | 1 | 5 |
| Покрытие тестами | 60% | 85% |

---

**Готов к коммиту?**
```

## Правила рефакторинга

1. **Тесты сначала** — без тестов не рефакторить
2. **Маленькие коммиты** — один рефакторинг = один коммит
3. **Не менять логику** — поведение должно остаться тем же
4. **Измерять улучшение** — метрики до и после
5. **Не ломать API** — публичные методы не менять

## Код-запахи (когда нужен рефакторинг)

| Запах | Решение |
|-------|---------|
| Длинный метод | Extract Method |
| Дублирование | DRY, Extract Utility |
| Магические числа | Extract Constant |
| Сложные условия | Replace Conditional |
| Большой класс | Extract Class |
| Зависть к функциям | Move Method |
| Ленивый класс | Inline Class |

## Связанные навыки
- `superpowers/code-review` — проверка перед рефакторингом
- `superpowers/testing` — тесты защищают от регрессии
- `memory/patterns` — сохранить успешный паттерн рефакторинга
