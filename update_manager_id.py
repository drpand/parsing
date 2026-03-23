"""
Update manager telegram_id to real value
"""

import asyncio
from app.db.database import database
from app.db.repositories import ManagerRepository


async def update():
    await database.connect()
    
    async with database.get_session() as session:
        from sqlalchemy import select
        from app.db.models import Manager
        
        # Находим менеджера Tatastu35
        result = await session.execute(select(Manager).where(Manager.username == 'Tatastu35'))
        manager = result.scalar()
        
        if manager:
            print(f"До: telegram_id = {manager.telegram_id}")
            # Обновляем на реальный ID
            manager.telegram_id = "6546867630"
            await session.commit()
            print(f"После: telegram_id = {manager.telegram_id}")
        else:
            print("Менеджер не найден!")
    
    await database.disconnect()


if __name__ == "__main__":
    asyncio.run(update())
