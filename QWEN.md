# IndiaShop Reseller Bot — Context Guide

**Project:** Telegram bot for parsing Indian marketplaces (Myntra, Zara, Ajio, Nykaa) with AI analysis
**Version:** v1.2 STABLE
**Last Update:** 2026-03-20
**Status:** ✅ Production Ready

---

## 🎯 Project Overview

IndiaShop is a Telegram bot that helps resellers find, parse, and analyze products from Indian e-commerce platforms. It uses:

- **Selenium Stealth** for web scraping (bypasses anti-bot protection)
- **OpenRouter Vision API** (ByteDance Seed 2.0 Mini) for AI-powered product data extraction
- **Aiogram 3.x** for Telegram bot framework
- **SQLAlchemy 2.0 + SQLite** for database (PostgreSQL ready)
- **APScheduler** for auto-posting schedules

**Value Proposition:**
- Saves time monitoring multiple marketplaces manually
- AI-generated product descriptions in Russian
- Automatic price conversion (INR → RUB) with margin calculation
- Auto-posting to Telegram channel on schedule

---

## 🏗️ Architecture

```
app/
├── bots/
│   ├── handlers/          # Command handlers (10 routers)
│   │   ├── start.py       # /start main menu
│   │   ├── admin_menu.py  # Admin panel navigation
│   │   ├── admin_parse.py # Single URL / category parsing
│   │   ├── admin_products.py  # CRUD products
│   │   ├── admin_posting.py   # Auto-posting settings
│   │   ├── admin_settings.py  # Pricing config (USD/RUB, margin)
│   │   ├── admin_cache.py     # Cache management
│   │   ├── admin_db.py        # Database operations
│   │   ├── admin_managers.py  # Manager accounts
│   │   ├── preview_product.py # Product preview
│   │   └── manager.py         # Manager contact handler
│   ├── keyboards/         # Inline keyboards
│   └── dispatcher.py      # Router registration, startup/shutdown
├── core/
│   ├── config.py          # Pydantic settings (.env loader)
│   ├── version.py         # Version info (v1.2.0)
│   └── process_manager.py # PID file management
├── db/
│   ├── models.py          # SQLAlchemy models (User, Product, Order, etc.)
│   ├── database.py        # Async SQLite connection
│   └── repositories/      # Data access layer
├── services/
│   ├── selenium_service.py    # 🚨 CRITICAL: Web scraping + stealth
│   ├── openrouter_service.py  # 🚨 CRITICAL: AI Vision API
│   ├── poster_service.py      # 🚨 CRITICAL: Auto-posting scheduler
│   ├── product_service.py     # Product business logic
│   ├── scheduler/
│   │   └── fx_scheduler.py    # Currency rate updates
│   └── proxy/
│       └── proxy_manager.py   # Proxy rotation (ready)
└── utils/
    ├── logger.py          # Custom logger
    ├── helpers.py         # Utility functions
    ├── validator.py       # URL validation, SKU extraction
    └── formatters/
        └── formatters.py  # Price/text formatters
```

### Critical Modules (⚠️ DO NOT MODIFY WITHOUT TESTS)

| Module | File | Purpose |
|--------|------|---------|
| Selenium Service | `app/services/selenium_service.py` | Scrapes Zara, Myntra, Ajio with stealth |
| OpenRouter Service | `app/services/openrouter_service.py` | AI extracts product data from screenshots |
| Poster Service | `app/services/poster_service.py` | Schedules posts to Telegram channel |
| Dispatcher | `app/bots/dispatcher.py` | Event loop, startup/shutdown hooks |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` (already configured, verify tokens):

```env
# Telegram
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_TELEGRAM_IDS=your_telegram_id_here

# OpenRouter AI
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview
OPENROUTER_FALLBACK_MODELS=qwen/qwen3.5-27b

# Database
DATABASE_URL=sqlite+aiosqlite:///./bot.db

# Pricing
USD_INR=83.5
USD_RUB=92.0
MARGIN_PERCENT=25.0
```

### 3. Run Bot

```bash
python main.py
```

**Windows (with auto-restart):**
```bash
start_bot.bat
```

### 4. Docker (Optional)

```bash
docker build -t indiashop-bot .
docker-compose up -d
```

---

## 📋 Bot Commands

### Public Commands
| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/version` | Bot version info |
| `/help` | Help message |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Admin panel |
| `/find <id>` | Find product by ID |
| `/cache` | Cache management |
| `/cancel` | Cancel current action |

### Admin Panel Features
- 🔍 **Parsing** — Single URL or category batch parse
- 📦 **Products** — View, edit, delete, filter by category
- 📢 **Posting** — Manual post, auto-post schedule
- ⚙️ **Settings** — Currency rates, margin %, intervals
- 💾 **Cache** — Clear AI cache
- 🗄 **Database** — Backup, reset, optimize
- 👥 **Managers** — Add/remove manager accounts

---

## 🛠️ Development

### Running Tests

```bash
pytest tests/
pytest --cov=app tests/
```

### Code Style

- **Type hints:** Required for all functions
- **Docstrings:** Google style for public APIs
- **Logging:** Use `app.utils.logger` with context
- **Error handling:** Catch specific exceptions, log with `exc_info=True`

### Adding New Handlers

1. Create handler in `app/bots/handlers/`
2. Register router in `app/bots/dispatcher.py`
3. Add commands to `setup_bot_commands()`

### Database Migrations

```bash
# SQLite auto-creates on startup
# For PostgreSQL migration:
alembic upgrade head
```

---

## 🔐 Security Rules

### NEVER
- ❌ Commit `.env` or secrets to git
- ❌ Hardcode API keys, tokens, passwords
- ❌ Expose error details to users
- ❌ Log personal data (PII)

### ALWAYS
- ✅ Use `pydantic.SecretStr` for tokens
- ✅ Validate all user input (URLs, text, files)
- ✅ Set timeouts on API calls
- ✅ Use graceful shutdown (PID cleanup, browser close)

---

## 🧪 Testing Practices

### Unit Tests (70%)
Test pure logic functions:
```python
async def test_price_extraction():
    assert extract_price("₹1,299") == 1299
    assert extract_price("Rs. 999.00") == 999
```

### Integration Tests (20%)
Test module interaction:
```python
async def test_parser_to_database():
    product = await parser.parse_product(url)
    await repository.save(product)
    assert await repository.find_by_url(url) is not None
```

### E2E Tests (10%)
Full user scenarios:
```python
async def test_user_parses_product():
    await bot.send_message("/admin")
    await bot.send_message("Parse URL")
    await bot.send_message("https://zara.com/...")
    assert "Product saved" in last_message
```

---

## 🐛 Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Bot not responding | Event loop blocked | Check for sync calls in async handlers |
| Parse returns empty | Website structure changed | Update CSS selectors in `_extract_*()` |
| Myntra: no images | Domain filter outdated | Add `myntassets.com` to valid domains |
| OpenRouter timeout | Large prompt | Reduce context, add retry logic |
| Database "locked" | SQLite concurrent writes | Enable WAL mode |
| Memory leak | Browsers not closed | Check `async with` in Selenium service |

### Emergency Commands

```bash
# View live logs
Get-Content bot.log -Tail 50 -Wait

# Kill stuck ChromeDriver processes
taskkill /F /IM chromedriver.exe

# Clear cache
python -c "from app.services.cache import clear_all; import asyncio; asyncio.run(clear_all())"

# Restart bot (Process Manager handles PID)
python main.py
```

---

## 📊 Database Schema

### Core Tables
- **users** — Telegram users (telegram_id, username, created_at)
- **products** — Parsed products (title, price_inr, price_rub, images JSON, category)
- **post_groups** — Telegram channels for auto-posting
- **post_schedule** — Posting schedule per group
- **post_history** — Sent posts with stats (views, clicks)
- **orders** — Customer orders (status, total, delivery address)
- **order_items** — Order line items
- **settings** — Bot config (key-value)
- **managers** — Manager accounts for customer support
- **product_cache** — AI response cache (TTL 24h)

---

## 🔄 Data Flow

### Parse Single Product
```
User → /admin → Parse URL → Selenium loads page →
Screenshot → OpenRouter Vision AI → Extract JSON →
Validate → Save to DB → Show preview → User confirms
```

### Auto-Post Cycle
```
Scheduler (every 15 min) → Fetch unpublished products →
Format message + photo → Send to channel →
Log to post_history → Update last_posted_at
```

### Manager Contact
```
User clicks "Contact Manager" →
Bot sends pre-filled message to random active manager →
Manager replies → User receives message
```

---

## 📁 Key Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | Entry point, process manager | ~80 |
| `app/core/config.py` | Pydantic settings loader | ~60 |
| `app/bots/dispatcher.py` | Router registration, hooks | ~150 |
| `app/services/selenium_service.py` | Web scraping logic | ~1400 |
| `app/services/openrouter_service.py` | AI Vision API client | ~1000 |
| `app/db/models.py` | SQLAlchemy models | ~250 |
| `app/bots/handlers/admin_parse.py` | Parse command handler | ~300 |

---

## 🎯 Supported Categories (50+)

### Men (8)
`men_shirts`, `men_tshirts`, `men_jeans`, `men_trousers`, `men_shorts`, `men_jackets`, `men_ethnic`, `men_innerwear`

### Women (10)
`women_dresses`, `women_tops`, `women_tshirts`, `women_jeans`, `women_trousers`, `women_skirts`, `women_sarees`, `women_kurtas`, `women_jackets`, `women_ethnic`

### Shoes (7)
`shoes_sneakers`, `shoes_sandals`, `shoes_boots`, `shoes_formal`, `shoes_heels`, `shoes_flats`, `shoes_sports`

### Bags (5)
`bags_handbags`, `bags_backpacks`, `bags_clutches`, `bags_shoulder`, `bags_wallets`

### Accessories (7)
`accessories_watches`, `accessories_jewelry`, `accessories_belts`, `accessories_sunglasses`, `accessories_scarves`, `accessories_hats`, `accessories_hair`

### Beauty (4)
`beauty_makeup`, `beauty_skincare`, `beauty_haircare`, `beauty_fragrance`

---

## 📚 Related Documentation

- `README.md` — User-facing documentation
- `PROJECT_BLUEPRINT.md` — Architecture decisions (ADR)
- `CHANGELOG.md` — Version history
- `QUICKSTART_v1.2.md` — Category testing guide
- `.env.example` — Environment template

---

## 🆘 Support

| Role | Contact |
|------|---------|
| Bot | @tatastu_bot |
| Channel | @tatastutest |
| Support | @tatastu_support |

---

**Last Reviewed:** 2026-03-23
**Maintainer:** Engineering Team
**License:** MIT (Proprietary for commercial use)
