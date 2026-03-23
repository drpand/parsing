"""
Check managers in database
"""

import asyncio
from app.db.database import database
from app.db.repositories import ManagerRepository


async def check():
    await database.connect()
    
    async with database.get_session() as session:
        repo = ManagerRepository(session)
        managers = await repo.get_all()
        
        print(f"\n{'='*50}")
        print(f"👥 МЕНЕДЖЕРЫ В БАЗЕ ДАННЫХ")
        print(f"{'='*50}")
        print(f"Всего менеджеров: {len(managers)}\n")
        
        if managers:
            for m in managers:
                print(f"  • @{m.username}")
                print(f"    ID: {m.telegram_id}")
                print(f"    Active: {'✅' if m.is_active else '❌'}")
                print(f"    Main: {'👑' if m.is_main else 'Обычный'}")
                print(f"    Запросов: {m.total_queries}")
                print(f"    Заказов: {m.total_orders}")
                print()
        else:
            print("  ❌ Менеджеров нет в базе\n")
        
        print(f"{'='*50}\n")
    
    await database.disconnect()


if __name__ == "__main__":
    asyncio.run(check())
