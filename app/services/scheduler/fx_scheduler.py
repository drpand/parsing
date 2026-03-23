# app/services/scheduler/fx_scheduler.py
"""
FX Scheduler для автообновления курса валют.
Взято из старого парсера + адаптировано для v1.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
import aiohttp
from sqlalchemy import select, update

from app.db.database import database
from app.db.models import Setting
from app.core.config import settings

logger = logging.getLogger(__name__)


class FXScheduler:
    """Планировщик обновления курса валют"""

    def __init__(self, update_interval_hours: int = 12):
        self.update_interval = update_interval_hours
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Запуск планировщика"""
        logger.info(f"✅ FX scheduler started (interval: {self.update_interval}h)")
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Остановка планировщика"""
        logger.info("FX scheduler stopping...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("FX scheduler stopped")

    async def _run_loop(self):
        """Основной цикл обновления"""
        while self._running:
            try:
                await self._update_fx_rates()
                await asyncio.sleep(self.update_interval * 3600)  # Часы в секунды
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"FX scheduler error: {e}")
                await asyncio.sleep(3600)  # Пауза 1 час при ошибке

    async def _update_fx_rates(self):
        """Обновление курсов валют"""
        logger.info("Updating FX rates...")

        try:
            # 🔐 Получаем курсы с ЦБ РФ (или другого источника)
            async with aiohttp.ClientSession() as session:
                async with session.get(settings.cbr_url) as resp:
                    if resp.status == 200:
                        xml_data = await resp.text()
                        usd_rate = self._parse_usd_rate(xml_data)

                        if usd_rate:
                            # Обновляем в БД
                            async with database.get_session() as db_session:
                                await db_session.execute(
                                    update(Setting)
                                    .where(Setting.key == "usd_rub")
                                    .values(value=str(usd_rate))
                                )
                                await db_session.commit()

                            logger.info(f"FX rate updated: USD={usd_rate}")
                        else:
                            logger.warning("Failed to parse USD rate from CB")
                    else:
                        logger.warning(f"CB API error: {resp.status}")

        except Exception as e:
            logger.error(f"FX update error: {e}")

    def _parse_usd_rate(self, xml_data: str) -> Optional[float]:
        """Парсинг XML от ЦБ РФ"""
        # 🔐 Простой парсинг XML (можно заменить на lxml)
        try:
            for line in xml_data.split('\n'):
                if 'USD' in line and 'Rate=' in line:
                    # <Valute ID="R0123A"><...><Value>90.5000</Value></Valute>
                    start = line.find('<Value>') + len('<Value>')
                    end = line.find('</Value>')
                    if start > -1 and end > -1:
                        rate_str = line[start:end].replace(',', '.')
                        return float(rate_str) / 10000  # ЦБ даёт в десятитысячных
        except Exception as e:
            logger.error(f"XML parse error: {e}")

        return None


# Глобальный экземпляр
fx_scheduler = FXScheduler(update_interval_hours=12)
