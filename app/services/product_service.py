"""
Product Service — Сервис для работы с товарами
"""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.database import database
from app.db.models import Product
from app.utils.logger import logger


class ProductService:
    """Сервис для работы с товарами"""

    async def get_product(self, product_id: int) -> Optional[Product]:
        """Получить товар по ID"""
        async with database.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            return result.scalar()

    async def get_products_list(
        self,
        page: int = 1,
        limit: int = 10,
        visible_only: bool = True
    ) -> tuple[List[Product], int]:
        """
        Получить список товаров с пагинацией
        
        Args:
            page: Номер страницы (1-based)
            limit: Количество товаров на странице
            visible_only: Показывать только видимые (is_active=True)
            
        Returns:
            (products, total_count)
        """
        async with database.get_session() as session:
            # Базовый запрос
            query = select(Product)
            
            # Фильтр по видимости
            if visible_only:
                query = query.where(Product.is_active == True)
            
            # Считаем общее количество
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            # Пагинация
            offset = (page - 1) * limit
            query = query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            products = result.scalars().all()
            
            return list(products), total_count

    async def update_product(self, product_id: int, **kwargs) -> bool:
        """
        Обновить товар
        
        Args:
            product_id: ID товара
            **kwargs: Поля для обновления
            
        Returns:
            True если успешно
        """
        async with database.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar()
            
            if not product:
                return False
            
            # Обновляем поля
            for key, value in kwargs.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            
            await session.commit()
            logger.info(f"Product {product_id} updated: {kwargs}")
            return True

    async def delete_product(self, product_id: int, hard: bool = False) -> bool:
        """
        Удалить товар
        
        Args:
            product_id: ID товара
            hard: Если True — полное удаление (DELETE), иначе мягкое (is_active=False)
            
        Returns:
            True если успешно
        """
        async with database.get_session() as session:
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar()
            
            if not product:
                return False
            
            if hard:
                # Полное удаление
                await session.delete(product)
                logger.info(f"Product {product_id} hard deleted")
            else:
                # Мягкое удаление
                product.is_active = False
                logger.info(f"Product {product_id} soft deleted (is_active=False)")
            
            await session.commit()
            return True

    async def restore_product(self, product_id: int) -> bool:
        """
        Восстановить товар (после мягкого удаления)
        
        Args:
            product_id: ID товара
            
        Returns:
            True если успешно
        """
        return await self.update_product(product_id, is_active=True)

    async def get_product_count(self, visible_only: bool = True) -> int:
        """Получить количество товаров"""
        async with database.get_session() as session:
            query = select(func.count(Product.id))
            
            if visible_only:
                query = query.where(Product.is_active == True)
            
            result = await session.execute(query)
            return result.scalar()

    async def search_products(
        self,
        query: str,
        limit: int = 20
    ) -> List[Product]:
        """
        Поиск товаров по названию
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список товаров
        """
        async with database.get_session() as session:
            result = await session.execute(
                select(Product)
                .where(Product.is_active == True)
                .where(Product.title.ilike(f"%{query}%"))
                .order_by(Product.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())


# Глобальный экземпляр
product_service = ProductService()
