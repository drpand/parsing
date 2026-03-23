@echo off
REM ============================================================================
REM IndiaShop Bot v1.2.0 — Setup Script
REM Автоматическая настройка для клиента
REM © 2026 IndiaShop. All Rights Reserved.
REM ============================================================================

chcp 65001 >nul
cls

echo ============================================
echo IndiaShop Bot v1.2.0 — Настройка
echo ============================================
echo.

REM 1. Проверка Python
echo [1/6] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден!
    echo.
    echo Установите Python 3.11+ с https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo [OK] Python найден
python --version
echo.

REM 2. Проверка pip
echo [2/6] Проверка pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip не найден!
    echo.
    echo Переустановите Python с опцией "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo [OK] pip найден
echo.

REM 3. Создание .env из шаблона
echo [3/6] Создание файла конфигурации...
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [OK] Файл .env создан из шаблона
    ) else (
        echo [WARN] .env.example не найден, создаю пустой .env
        type nul > .env
    )
    echo.
    echo ╔══════════════════════════════════════════════════════════╗
    echo ║  ⚠️  ВАЖНО: Настройте файл .env                          ║
    echo ╚══════════════════════════════════════════════════════════╝
    echo.
    echo Откройте файл .env и заполните:
    echo   1. BOT_TOKEN — токен от @BotFather
    echo   2. OPENROUTER_API_KEY — ключ от openrouter.ai
    echo   3. ADMIN_TELEGRAM_IDS — ваш Telegram ID
    echo.
    echo 📖 Подробная инструкция: INSTALL_GUIDE.md
    echo.
    pause
) else (
    echo [OK] .env уже существует
)
echo.

REM 4. Установка зависимостей
echo [4/6] Установка зависимостей...
echo Это может занять несколько минут...
echo.
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo [ERROR] Ошибка установки зависимостей!
    echo.
    echo Попробуйте установить вручную:
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo [OK] Зависимости установлены
echo.

REM 5. Создание рабочих папок
echo [5/6] Создание рабочих папок...
if not exist data (
    mkdir data
    echo   [OK] data/
)
if not exist logs (
    mkdir logs
    echo   [OK] logs/
)
echo.

REM 6. Проверка конфигурации
echo [6/6] Проверка конфигурации...
echo.

REM Проверка BOT_TOKEN
findstr /C:"BOT_TOKEN=your_token_here" .env >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  BOT_TOKEN не настроен!
    echo    Откройте .env и вставьте ваш токен бота.
    echo.
) else (
    echo [OK] BOT_TOKEN настроен
)

REM Проверка OPENROUTER_API_KEY
findstr /C:"OPENROUTER_API_KEY=your_api_key_here" .env >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  OPENROUTER_API_KEY не настроен!
    echo    Откройте .env и вставьте ваш API ключ.
    echo.
) else (
    echo [OK] OPENROUTER_API_KEY настроен
)

echo.
echo ============================================
echo ✅ НАСТРОЙКА ЗАВЕРШЕНА!
echo ============================================
echo.
echo 📁 Структура проекта:
echo   ├─ data/        — данные бота (БД, кэш)
echo   ├─ logs/        — логи работы
echo   ├─ app/         — код бота
echo   ├─ .env         — конфигурация
echo   └─ main.py      — точка запуска
echo.
echo 🚀 Следующие шаги:
echo   1. Откройте .env и заполните API ключи
echo   2. Запустите START.bat для запуска бота
echo.
echo 📖 Документация:
echo   • README_CLIENT.md — полная инструкция
echo   • QUICKSTART.md — быстрый старт (5 мин)
echo   • INSTALL_GUIDE.md — как получить API ключи
echo.
echo 💡 Поддержка: напишите @tatastu в Telegram
echo.
pause
