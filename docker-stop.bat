@echo off
REM Docker Stop Script for IndiaShop Bot v1.2.0
REM Windows Batch File

echo ============================================
echo IndiaShop Bot v1.2.0 - Docker Stop
echo ============================================
echo.

REM Stop container
echo Stopping container...
docker-compose down

echo.
echo [OK] Container stopped
echo.

pause
