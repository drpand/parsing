# 🧩 Qwen MCP Templates — Универсальные настройки

**Версия:** 1.0  
**Дата:** 2026-03-24  
**Статус:** ✅ Production Ready

---

## 📦 Что это?

Универсальные шаблоны настроек MCP для всех проектов на базе Qwen Code.

---

## 🚀 Быстрый старт

### 1. Скопируйте шаблон

```bash
# В вашем проекте
cp path/to/settings.json.template .qwen/settings.json
```

### 2. Настройте переменные

Откройте `.qwen/settings.json` и замените:

| Переменная | Описание | Где получить |
|------------|----------|--------------|
| `${GITHUB_TOKEN}` | Токен GitHub | https://github.com/settings/tokens |
| `${OPENROUTER_API_KEY}` | Ключ OpenRouter AI | https://openrouter.ai/keys |
| `${HOME}` | Домашняя директория | Ваша OS |
| `${PROJECT_ROOT}` | Корень проекта | Путь к проекту |

### 3. Проверьте работу

```bash
npx -y ruflo system status
```

---

## 🔧 Доступные MCP серверы

### Ядро (обязательные)

| Сервер | Назначение | Требуется |
|--------|-----------|-----------|
| **ruflo** | Агенты, swarm, память | Нет |
| **github** | Работа с репозиторием | GITHUB_TOKEN |

### AI (рекомендуемые)

| Сервер | Назначение | Требуется |
|--------|-----------|-----------|
| **task-master** | Планирование задач | OPENROUTER_API_KEY |
| **skillsmith** | Skill discovery | Нет |
| **superpowers** | Brainstorming, code review | Установленный superpowers |

### Автоматизация

| Сервер | Назначение | Требуется |
|--------|-----------|-----------|
| **real-browser** | Веб-автоматизация | Playwright |
| **playwright** | Браузерная автоматизация | Playwright |
| **filesystem** | Работа с файлами | Нет |

---

## 📁 Структура шаблона

```
.qwen/
├── settings.json           # Активные настройки (НЕ коммитить!)
├── settings.json.template  # Шаблон (можно коммитить)
├── settings.json.example   # Пример с заглушками
└── .gitignore              # Исключения
```

---

## 🔐 Безопасность

### ❌ НЕ коммитить:

- `.qwen/settings.json` (с реальными токенами)
- `.qwen/memory/`
- `.env`

### ✅ Можно коммитить:

- `.qwen/settings.json.template`
- `.qwen/settings.json.example`
- `.qwen/.gitignore`
- Документацию

---

## 📊 Проверка секретов в GitHub

### Через API:

```bash
# Проверить секреты репозитория
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/USER/REPO/secrets/actions
```

### Через веб-интерфейс:

1. Откройте репозиторий на GitHub
2. Settings → Secrets and variables → Actions
3. Проверьте список секретов

### Рекомендуемые секреты:

| Имя | Описание |
|-----|----------|
| `GITHUB_TOKEN` | Токен для доступа к API |
| `OPENROUTER_API_KEY` | Ключ для AI моделей |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота |
| `DOCKER_USERNAME` | Docker Hub логин |
| `DOCKER_PASSWORD` | Docker Hub пароль |

---

## 🎯 Примеры использования

### IndiaShop Bot

```json
{
  "model": {
    "provider": "openrouter",
    "default": "qwen/qwen3-8b"
  },
  "mcpServers": {
    "github": { "...": "..." },
    "ruflo": { "...": "..." },
    "task-master": { "...": "..." }
  }
}
```

### Telegram Agent

```json
{
  "model": {
    "provider": "openrouter",
    "default": "qwen/qwen3-8b"
  },
  "mcpServers": {
    "github": { "...": "..." },
    "ruflo": { "...": "..." },
    "real-browser": { "...": "..." },
    "superpowers": { "...": "..." }
  }
}
```

---

## 📝 Changelog

### v1.0 (2026-03-24)

- ✅ Ruflo MCP
- ✅ Task Master MCP
- ✅ Skillsmith MCP
- ✅ GitHub MCP
- ✅ Real Browser MCP
- ✅ Playwright MCP
- ✅ Superpowers MCP
- ✅ Filesystem MCP

---

## 📞 Поддержка

**GitHub:** https://github.com/drpand/parsing  
**Telegram:** @tatastu

---

**Лицензия:** MIT (Proprietary for commercial use)  
**© 2026 IndiaShop. All Rights Reserved.**
