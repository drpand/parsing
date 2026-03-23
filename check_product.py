import asyncio
import sys
sys.path.insert(0, 'C:\\Users\\gruffi\\Desktop\\bot')

from app.db.database import database
from app.db.models import Product
from sqlalchemy import select

async def check():
    await database.connect()
    async with database.get_session() as session:
        # Проверяем товар ID=8
        result = await session.execute(select(Product).where(Product.id == 8))
        p = result.scalar()
        if p:
            print(f"✅ Product ID=8: {p.title[:50]}...")
            print(f"   Price: ₹{p.price_inr} / ₽{p.price_rub}")
            print(f"   Images: {p.images[:50] if p.images else 'None'}...")
        else:
            print("❌ Product ID=8 NOT FOUND")
        
        # Проверяем все товары
        result = await session.execute(select(Product))
        products = result.scalars().all()
        print(f"\n📦 Всего товаров в БД: {len(products)}")
        for prod in products[:10]:
            print(f"   - ID={prod.id}: {prod.title[:40]}... ({prod.price_rub}₽)")
    
    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
