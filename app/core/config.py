"""
Configuration IndiaShop Bot v2.0
"""

import os
# 🔐 ПРИНУДИТЕЛЬНАЯ ЗАГРУЗКА .env ПЕРЕД всем остальным
from dotenv import load_dotenv
load_dotenv('.env', override=True)

from pydantic import SecretStr
from pydantic_settings import BaseSettings
from typing import List


class BotSettings(BaseSettings):
    """Настройки бота"""

    # Telegram
    bot_token: SecretStr
    bot_username: str = "tatastu_bot"  # 🔐 Добавляем username бота
    admin_telegram_ids: str = "5935993156"

    # OpenRouter
    openrouter_api_key: SecretStr
    openrouter_model: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout: int = 30
    openrouter_fallback_models: str
    openrouter_max_retries: int = 3

    # Database
    database_url: str = "sqlite+aiosqlite:///./bot.db"

    # Pricing (актуальные значения)
    usd_inr: float = 91.0
    usd_rub: float = 80.0
    margin_percent: float = 25.0
    delivery_fixed: float = 500
    delivery_percent: float = 5.0

    # Manager (как в бекапе v0.8.8)
    manager_username: str = "tatastu"  # Username менеджера для связи (одиночный)
    manager_usernames: str = "tatastu"  # Список менеджеров через запятую для балансировки

    # Posting (как в бекапе v0.8.8)
    post_interval_minutes: int = 60  # Интервал авто-постинга в минутах

    # ScrapeGraph (не используется)
    scrapegraph_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорировать лишние поля

    @property
    def admin_ids(self) -> List[int]:
        """Список ID админов"""
        return [int(x.strip()) for x in self.admin_telegram_ids.split(",")]

    @property
    def manager_list(self) -> List[str]:
        """Список менеджеров для балансировки нагрузки"""
        return [m.strip().lstrip('@') for m in self.manager_usernames.split(",") if m.strip()]


# Глобальный экземпляр
settings = BotSettings()
