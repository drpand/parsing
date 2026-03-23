# Суперспособность: Test-Driven Development (TDD)

## Назначение
Разработка через тестирование: сначала тест, потом код который его проходит.

## Когда использовать
- Реализация новой функции
- Исправление бага (сначала тест на баг)
- Рефакторинг (тесты защищают от регрессии)
- Сложная логика с условиями

## Цикл TDD: Red-Green-Refactor

### 🔴 Red: Написать тест
```
1. Понять требование
2. Написать тест который ПРОВАЛИТСЯ
3. Запустить тест → убедиться что падает
4. Запомнить что ожидает тест
```

### 🟢 Green: Написать код
```
1. Написать минимальный код для прохождения теста
2. Не оптимизировать, не улучшать
3. Запустить тест → должен пройти
4. Если не прошёл → исправить
```

### 🟡 Refactor: Улучшить
```
1. Убрать дублирование
2. Улучшить читаемость
3. Оптимизировать если нужно
4. Запустить тесты → должны пройти
```

## Шаблон TDD сессии

```markdown
## 🧪 TDD: [Название функции]

### Требование
[Что должна делать функция]

---

### 🔴 Red: Тест

**Тест:**
```python
async def test_[function]_[scenario]():
    # Arrange
    ...
    
    # Act
    result = await function(...)
    
    # Assert
    assert result == expected
```

**Запуск:** ❌ FAILED (ожидаемо)
```
AssertionError: expected X, got Y
```

---

### 🟢 Green: Реализация

**Код:**
```python
async def [function](...):
    # Минимальная реализация
    ...
```

**Запуск:** ✅ PASSED

---

### 🟡 Refactor: Улучшение

**Изменения:**
- Убрал дублирование
- Вынес константу
- Добавил типизацию

**Запуск:** ✅ PASSED

---

### Следующий тест
[Описание следующего сценария]
```

## Пример TDD

```markdown
## 🧪 TDD: extract_price (парсинг цены)

### Требование
Функция должна извлекать цену из строки:
- "₹1,299" → 1299
- "Rs. 999.00" → 999
- "MRP: ₹2,499.00" → 2499

---

### 🔴 Red: Тест 1 (базовый)

**Тест:**
```python
# tests/test_parsers/test_utils.py
async def test_extract_price_rupee_symbol():
    assert extract_price("₹1,299") == 1299
    assert extract_price("₹2,499.00") == 2499
```

**Запуск:** ❌ FAILED
```
NameError: name 'extract_price' is not defined
```

---

### 🟢 Green: Реализация 1

**Код:**
```python
# app/services/parsers/utils.py
def extract_price(text: str) -> int:
    # Удаляем ₹ и запятые
    text = text.replace("₹", "").replace(",", "")
    return int(float(text))
```

**Запуск:** ✅ PASSED

---

### 🟡 Refactor: Улучшение 1

**Изменения:**
- Добавил обработку "Rs."
- Добавил типизацию

**Код:**
```python
def extract_price(text: str) -> int:
    # Удаляем символы валют
    text = text.replace("₹", "").replace("Rs.", "")
    text = text.replace("MRP:", "").strip()
    # Удаляем запятые в числе
    text = text.replace(",", "")
    return int(float(text))
```

**Запуск:** ✅ PASSED

---

### 🔴 Red: Тест 2 (Rs. формат)

**Тест:**
```python
async def test_extract_price_rs_format():
    assert extract_price("Rs. 999.00") == 999
    assert extract_price("MRP: Rs. 1,599") == 1599
```

**Запуск:** ✅ PASSED (уже работает!)

---

### 🔴 Red: Тест 3 (edge cases)

**Тест:**
```python
async def test_extract_price_edge_cases():
    assert extract_price("₹ 1,299") == 1299  # пробел
    assert extract_price("  ₹1,299  ") == 1299  # пробелы вокруг
```

**Запуск:** ❌ FAILED
```
ValueError: could not convert string to float: ' 1299  '
```

---

### 🟢 Green: Исправление

**Код:**
```python
def extract_price(text: str) -> int:
    text = text.replace("₹", "").replace("Rs.", "")
    text = text.replace("MRP:", "")
    text = text.replace(",", "")
    text = text.strip()  # Удаляем пробелы
    return int(float(text))
```

**Запуск:** ✅ PASSED

---

### ✅ Итог
- 3 теста покрывают основные сценарии
- Функция работает с ₹ и Rs.
- Обработка пробелов и запятых

**Готов к следующему TDD циклу?**
```

## Правила TDD

1. **Тест первый** — никогда не писать код до теста
2. **Минимальный код** — только чтобы тест прошёл
3. **Один сценарий за раз** — не добавлять лишние проверки
4. **Рефакторинг после** — только когда тест зелёный
5. **Имя теста = сценарий** — понятно что тестирует

## Типы тестов для TDD

### Unit тесты (70%)
```python
async def test_extract_price_valid_input():
    # Чистая логика без внешних зависимостей
```

### Integration тесты (20%)
```python
async def test_parser_saves_to_database():
    # Взаимодействие модулей
```

### E2E тесты (10%)
```python
async def test_user_parses_product_via_bot():
    # Полный сценарий пользователя
```

## Связанные навыки
- `superpowers/verification` — проверка тестов
- `superpowers/debugging` — если тест не проходит
- `memory/patterns` — сохранить успешный TDD подход
