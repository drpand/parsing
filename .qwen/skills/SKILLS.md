# 🦾 Superpowers для Qwen Code

Коллекция навыков и суперспособностей для эффективной разработки с Qwen Code.

---

## 📚 Каталог навыков

### 🧠 Память (Memory)

| Навык | Описание | Когда использовать |
|-------|----------|-------------------|
| [`memory/task`](.qwen/skills/memory/task/SKILL.md) | Управление задачами | В начале/конце сессии для отслеживания прогресса |
| [`memory/session`](.qwen/skills/memory/session/SKILL.md) | Журнал сессий | Документирование каждой сессии разработки |
| [`memory/patterns`](.qwen/skills/memory/patterns/SKILL.md) | Паттерны и антипаттерны | Сохранение успешных решений и ошибок |

### ⚡ Суперспособности (Superpowers)

| Навык | Описание | Когда использовать |
|-------|----------|-------------------|
| [`superpowers/brainstorming`](.qwen/skills/superpowers/brainstorming/SKILL.md) | Генерация идей | Сложная задача, выбор подхода |
| [`superpowers/planning`](.qwen/skills/superpowers/planning/SKILL.md) | Создание планов | Перед реализацией многошаговой задачи |
| [`superpowers/executing`](.qwen/skills/superpowers/executing/SKILL.md) | Выполнение планов | Систематическая реализация по шагам |
| [`superpowers/debugging`](.qwen/skills/superpowers/debugging/SKILL.md) | Системная отладка | Поиск и исправление ошибок |
| [`superpowers/testing`](.qwen/skills/superpowers/testing/SKILL.md) | TDD подход | Разработка через тестирование |
| [`superpowers/verification`](.qwen/skills/superpowers/verification/SKILL.md) | Проверка перед завершением | Финальная валидация результата |
| [`superpowers/code-review`](.qwen/skills/superpowers/code-review/SKILL.md) | Подготовка к ревью | Самопроверка перед коммитом |
| [`superpowers/refactoring`](.qwen/skills/superpowers/refactoring/SKILL.md) | Улучшение кода | Рефакторинг без изменения логики |

---

## 🚀 Как использовать

### Через команду skill

```
use skill tool to load memory/task
use skill tool to load superpowers/brainstorming
```

### Автоматически

Qwen Code автоматически применяет навыки когда распознаёт контекст:
- **Новая задача** → brainstorming → planning
- **Реализация** → executing → verification
- **Ошибка** → debugging
- **Перед коммитом** → code-review

---

## 📋 Мета-LOOP (Алгоритм работы)

Каждую задачу выполняй по циклу:

```
1. 📖 ЧИТАЙ
   - .qwen/memory/tasks.md — текущая задача
   - .qwen/memory/sessions.md — контекст прошлой сессии

2. 🧠 BRAINSTORMING (если нужно)
   - Исследовать проблему
   - Предложить 3 варианта решения
   - Выбрать лучший

3. 📝 PLANNING
   - Декомпозировать на шаги
   - Оценить риски
   - Получить подтверждение

4. ⚡ EXECUTING
   - Один шаг за раз
   - Тест после каждого шага
   - Ждать подтверждения

5. ✅ VERIFICATION
   - Синтаксис
   - Unit тесты
   - Integration тесты
   - E2E в Telegram

6. 📚 ЗАПИСЬ
   - Обновить tasks.md
   - Записать в sessions.md
   - Сохранить паттерн если новый
```

---

## 🎯 Принципы работы

### Source of Truth
```
❌ Успех: "Код без ошибок"
✅ Успех: "Реальный тест проходит"
```

### Маленькие шаги
```
Один файл за раз.
Одно изменение за раз.
Подтверждение после каждого шага.
```

### Честность
```
Попытка 1 не удалась → Анализ, исправление
Попытка 2 не удалась → СТОП, объяснить проблему
Никогда не пробовать третий раз — это галлюцинация
```

### Безопасность
```
❌ Никогда не коммитить .env
❌ Никогда не хардкодить токены
✅ Запрашивать у пользователя
```

---

## 📁 Структура файлов

```
.qwen/
├── memory/
│   ├── tasks.md       # Задачи (слои)
│   ├── sessions.md    # Журнал сессий
│   └── patterns.md    # Паттерны
├── skills/
│   ├── memory/
│   │   ├── task/SKILL.md
│   │   ├── session/SKILL.md
│   │   └── patterns/SKILL.md
│   └── superpowers/
│       ├── brainstorming/SKILL.md
│       ├── planning/SKILL.md
│       ├── executing/SKILL.md
│       ├── debugging/SKILL.md
│       ├── testing/SKILL.md
│       ├── verification/SKILL.md
│       ├── code-review/SKILL.md
│       └── refactoring/SKILL.md
└── settings.json
```

---

## 🔗 Связанные ресурсы

- [QWEN.md](../QWEN.md) — Глобальные правила агента
- [README.md](../README.md) — Документация проекта
- [PROJECT_BLUEPRINT.md](../PROJECT_BLUEPRINT.md) — Архитектура

---

**Версия:** 1.0  
**Обновлено:** 2026-03-23
