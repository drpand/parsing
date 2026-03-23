@echo off
REM ============================================================================
REM IndiaShop Bot v1.2.0 — Start Script
REM Запуск бота
REM © 2026 IndiaShop. All Rights Reserved.
REM ============================================================================

chcp 65001 >nul
cls

echo ============================================
echo IndiaShop Bot v1.2.0 — Запуск
echo ============================================
echo.

REM Проверка .env
if not exist .env (
    echo [ERROR] Файл .env не найден!
    echo.
    echo Запустите SETUP.bat сначала.
    echo.
    pause
    exit /b 1
)

REM Проверка BOT_TOKEN
findstr /C:"BOT_TOKEN=" .env >nul 2>&1
if errorlevel 1 (
    echo [ERROR] BOT_TOKEN не найден в .env!
    echo.
    echo Откройте .env и добавьте токен бота.
    echo Получите токен в @BotFather (Telegram)
    echo.
    pause
    exit /b 1
)

REM Проверка OPENROUTER_API_KEY
findstr /C:"OPENROUTER_API_KEY=" .env >nul 2>&1
if errorlevel 1 (
    echo [ERROR] OPENROUTER_API_KEY не найден в .env!
    echo.
    echo Откройте .env и добавьте API ключ.
    echo Получите ключ на https://openrouter.ai/keys
    echo.
    pause
    exit /b 1
)

echo [OK] Проверка конфигурации пройдена
echo.
echo ============================================
echo 🤖 Запуск бота...
echo ============================================
echo.
echo 💡 Для остановки бота:
echo   • Закройте это окно
echo   • Или нажмите CTRL+C
echo.
echo 📊 Логи сохраняются в: bot.log
echo.
echo ============================================
echo.

python main.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo [ERROR] Бот завершил работу с ошибкой
    echo ============================================
    echo.
    echo Проверьте логи в файле bot.log
    echo.
    pause
)
