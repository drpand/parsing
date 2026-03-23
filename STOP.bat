@echo off
REM ============================================================================
REM IndiaShop Bot v1.2.0 — Stop Script
REM Остановка бота
REM © 2026 IndiaShop. All Rights Reserved.
REM ============================================================================

chcp 65001 >nul
cls

echo ============================================
echo IndiaShop Bot v1.2.0 — Остановка
echo ============================================
echo.

REM Поиск процесса Python с main.py
echo Поиск запущенного бота...
echo.

for /f "tokens=2 delims=," %%i in ('wmic process where "name='python.exe'" get ProcessId^,CommandLine /format:csv ^| find "main.py"') do (
    set PID=%%i
    goto :found
)

REM Альтернативный метод поиска
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *main.py*" /FO CSV ^| find "python"') do (
    set PID=%%i
    goto :found
)

:found
if defined PID (
    REM Удалить кавычки из PID
    set PID=%PID:"=%
    
    echo [OK] Найден процесс бота (PID: %PID%)
    echo.
    echo Остановка бота...
    taskkill /F /PID %PID% >nul 2>&1
    
    if errorlevel 1 (
        echo [WARN] Не удалось остановить процесс
        echo Попробуйте закрыть окно бота вручную
    ) else (
        echo [OK] Бот успешно остановлен
    )
) else (
    echo [INFO] Бот не запущен
    echo.
    echo Если бот работает в другом окне,
    echo закройте его вручную.
)

echo.
echo ============================================
echo.

REM Очистка PID файла если есть
if exist bot.pid (
    del bot.pid >nul 2>&1
    echo [OK] Файл bot.pid удалён
)

echo.
pause
