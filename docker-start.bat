@echo off
REM Docker Start Script for IndiaShop Bot v1.2.0
REM Windows Batch File

echo ============================================
echo IndiaShop Bot v1.2.0 - Docker Start
echo ============================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Build and start
echo Building Docker image...
docker-compose build

echo.
echo Starting container...
docker-compose up -d

echo.
echo ============================================
echo Container started!
echo ============================================
echo.
echo View logs: docker-compose logs -f
echo Stop: docker-compose down
echo Restart: docker-compose restart
echo.

docker-compose ps
pause
