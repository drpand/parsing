# IndiaShop Bot — MCP Серверы

## 🔧 Настроенные MCP серверы

### 1. **GitHub MCP**
- **Команда:** `npx -y @modelcontextprotocol/server-github`
- **Назначение:** Работа с GitHub (issues, PR, commits)
- **Требует:** `GITHUB_TOKEN` в .env

### 2. **Ruflo MCP** ⭐
- **Команда:** `npx -y ruflo`
- **Назначение:** 
  - Управление агентами и swarm
  - Память проекта (RuVector Memory)
  - Workflow automation
  - Metrics и analytics
- **Требует:** Нет (автономный)

### 3. **Task Master MCP** ⭐
- **Команда:** `npx -y task-master-ai`
- **Назначение:**
  - AI планирование задач
  - Декомпозиция проектов
  - Трекинг прогресса
- **Требует:** `OPENROUTER_API_KEY` в .env

### 4. **Superpowers MCP**
- **Команда:** `node C:/Users/gruffi/.qwen/mcp-servers/superpowers-mcp/build/index.js`
- **Назначение:**
  - Brainstorming
  - Code review
  - Planning & Execution
- **Требует:** Установленный superpowers-mcp

### 5. **Real Browser MCP**
- **Команда:** `npx -y real-browser-mcp`
- **Назначение:**
  - Веб-автоматизация
  - Тестирование UI
  - Скриншоты
- **Требует:** Playwright

### 6. **Skillsmith MCP**
- **Команда:** `npx -y @skillsmith/mcp-server`
- **Назначение:**
  - AI skill discovery
  - Pattern matching
- **Требует:** Нет

---

## 📁 Структура .qwen/

```
.qwen/
├── settings.json           # Активные настройки (НЕ коммитить!)
├── settings.json.example   # Шаблон для документации
├── .gitignore              # Исключения
├── memory/                 # Память проектов (игнорируется)
│   ├── sessions.md
│   ├── tasks.md
│   └── patterns.md
└── skills/                 # AI навыки (игнорируется)
```

---

## 🚀 Быстрый старт

### 1. Установить Node.js (если нет)
```bash
node --version  # Проверка
```

### 2. Настроить .env
```env
GITHUB_TOKEN=ghp_your_token_here
OPENROUTER_API_KEY=sk-or-v1-your_key_here
```

### 3. Запустить Ruflo
```bash
npx -y ruflo
```

### 4. Проверить статус
```bash
npx -y ruflo system status
```

---

## 🔐 Безопасность

### ❌ НЕ коммитить:
- `.qwen/settings.json` (с реальными токенами)
- `.qwen/memory/`
- `.env`

### ✅ Можно коммитить:
- `.qwen/settings.json.example`
- `.qwen/.gitignore`
- Документацию

---

**Дата обновления:** 2026-03-24  
**Статус:** ✅ Активно
