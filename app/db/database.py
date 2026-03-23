"""
Database connection IndiaShop Bot v2.0
"""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from app.core.config import settings
from app.utils.logger import logger
from typing import Optional, AsyncGenerator


class Database:
    """Управление БД"""

    def __init__(self):
        self.engine: Optional[create_async_engine] = None
        self.session_maker: Optional[async_sessionmaker] = None

    async def connect(self):
        """Подключение к БД"""
        logger.info(f"Connecting to {settings.database_url}...")

        self.engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
        )

        self.session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Создаём таблицы
        from app.db.models import Base, Setting
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
            # 🔐 СОЗДАЁМ НАСТРОЙКИ ПО УМОЛЧАНИЮ (если их нет)
            async with self.session_maker() as session:
                result = await session.execute(select(Setting))
                existing_settings = result.scalars().all()
                
                if not existing_settings:
                    logger.info("🔧 Creating default settings...")
                    
                    default_settings = [
                        Setting(key="parse_limit", value="10"),
                        Setting(key="parse_interval", value="2"),
                        Setting(key="post_interval", value="60"),  # Интервал автопостинга (минуты)
                        Setting(key="manager_username", value="tatastu"),  # Менеджер по умолчанию
                        Setting(key="margin_percent", value="25.0"),
                        Setting(key="usd_inr", value="91.0"),  # Актуальный курс
                        Setting(key="usd_rub", value="80.0"),  # Актуальный курс
                        Setting(key="delivery_fixed", value="500"),
                        Setting(key="delivery_percent", value="5.0"),
                    ]
                    
                    for setting in default_settings:
                        session.add(setting)
                    
                    await session.commit()
                    logger.info(f"✅ Created {len(default_settings)} default settings")
                else:
                    logger.info(f"✅ Found {len(existing_settings)} existing settings")

        logger.info("Database connected")

    async def disconnect(self):
        """Отключение от БД"""
        if self.engine:
            await self.engine.dispose()
        logger.info("Database disconnected")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Получить сессию (async context manager)"""
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def get_session_sync(self) -> AsyncSession:
        """Получить сессию (синхронно, без commit)"""
        return self.session_maker()


# Глобальный экземпляр
database = Database()
