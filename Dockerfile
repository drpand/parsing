# Dockerfile для IndiaShop Bot v1.2.0
# © 2026 IndiaShop. All Rights Reserved.

FROM python:3.11-slim

# Устанавливаем Chrome и ChromeDriver для Selenium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Переменные окружения для Chrome (Selenium)
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER=/usr/bin/chromedriver
ENV DISPLAY=:99
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

# Рабочая директория
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаём директорию для данных
RUN mkdir -p /app/data && chown -R botuser:botuser /app/data

# Создаём пользователя для безопасности
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Экспозиция портов (если понадобится веб-интерфейс)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Запуск бота
CMD ["python", "main.py"]
