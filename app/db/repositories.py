"""
Репозитории для работы с БД IndiaShop Bot v2.0
"""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List
import json

from app.db.models import Product, PostGroup, PostSchedule, PostHistory, Order, OrderItem, User, Setting, Manager


class ProductRepository:
    """Репозиторий товаров"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Product:
        """Создать товар"""
        # Удаляем поля которых нет в БД
        data_copy = data.copy()
        data_copy.pop('is_on_sale', None)  # Удаляем если есть

        product = Product(**data_copy)
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Получить товар по ID"""
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar()

    async def get_by_url(self, url: str) -> Optional[Product]:
        """Получить товар по URL (проверка дубликатов)"""
        result = await self.session.execute(select(Product).where(Product.source_url == url))
        return result.scalar()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Получить все товары"""
        result = await self.session.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_for_posting(self, group_id: int, limit: int = 10) -> List[Product]:
        """Получить товары для постинга (не постили recently)"""
        # Получаем расписание
        schedule_result = await self.session.execute(
            select(PostSchedule).where(PostSchedule.group_id == group_id)
        )
        schedule = schedule_result.scalar()

        if not schedule:
            return []

        # Фильтры
        query = select(Product).where(
            Product.is_active == True,
            Product.in_stock == True,
        )

        # Только горячие если настроено
        if schedule.only_hot_deals:
            query = query.where(Product.is_hot_deal == True)

        # Мин. скидка
        if schedule.min_discount > 0:
            query = query.where(Product.discount_percent >= schedule.min_discount)

        # Не постили в последние N часов
        hours_since_post = 24 // schedule.posts_per_hour
        last_post_threshold = datetime.utcnow() - timedelta(hours=hours_since_post)
        query = query.where(
            and_(
                Product.last_posted_at.is_(None) |
                (Product.last_posted_at < last_post_threshold)
            )
        )

        # Сортировка по скидке и дате
        query = query.order_by(
            Product.discount_percent.desc(),
            Product.is_hot_deal.desc(),
            Product.created_at.desc()
        )
        query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_last_posted(self, product_id: int):
        """Обновить время последнего поста"""
        product = await self.get_by_id(product_id)
        if product:
            product.last_posted_at = datetime.utcnow()
            await self.session.commit()

    async def update(self, product_id: int, data: dict) -> Optional[Product]:
        """Обновить товар"""
        product = await self.get_by_id(product_id)
        if product:
            for key, value in data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            await self.session.commit()
            await self.session.refresh(product)
        return product

    async def delete(self, product_id: int):
        """Удалить товар (мягкое)"""
        product = await self.get_by_id(product_id)
        if product:
            product.is_active = False
            await self.session.commit()

    async def count(self) -> int:
        """Посчитать количество товаров"""
        result = await self.session.execute(
            select(func.count(Product.id)).where(Product.is_active == True)
        )
        return result.scalar() or 0


class PostGroupRepository:
    """Репозиторий групп для постинга"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> PostGroup:
        """Добавить группу"""
        group = PostGroup(**data)
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)

        # Создаём расписание по умолчанию
        schedule = PostSchedule(group_id=group.id)
        self.session.add(schedule)
        await self.session.commit()

        return group

    async def get_by_id(self, group_id: int) -> Optional[PostGroup]:
        """Получить группу по ID"""
        result = await self.session.execute(select(PostGroup).where(PostGroup.id == group_id))
        return result.scalar()

    async def get_by_chat_id(self, chat_id: str) -> Optional[PostGroup]:
        """Получить группу по chat_id"""
        result = await self.session.execute(select(PostGroup).where(PostGroup.chat_id == chat_id))
        return result.scalar()

    async def get_all_active(self) -> List[PostGroup]:
        """Получить все активные группы"""
        result = await self.session.execute(
            select(PostGroup).where(PostGroup.is_active == True)
        )
        return list(result.scalars().all())

    async def update(self, group_id: int, data: dict) -> Optional[PostGroup]:
        """Обновить группу"""
        group = await self.get_by_id(group_id)
        if group:
            for key, value in data.items():
                if hasattr(group, key):
                    setattr(group, key, value)
            await self.session.commit()
            await self.session.refresh(group)
        return group

    async def increment_stats(self, group_id: int, posts: int = 1, views: int = 0, clicks: int = 0):
        """Обновить статистику"""
        group = await self.get_by_id(group_id)
        if group:
            group.posts_count += posts
            group.total_views += views
            group.total_clicks += clicks
            group.last_post_at = datetime.utcnow()
            await self.session.commit()

    async def delete(self, group_id: int):
        """Удалить группу (мягкое)"""
        group = await self.get_by_id(group_id)
        if group:
            group.is_active = False
            await self.session.commit()

    async def count(self) -> int:
        """Посчитать количество групп"""
        result = await self.session.execute(
            select(func.count(PostGroup.id)).where(PostGroup.is_active == True)
        )
        return result.scalar() or 0


class PostScheduleRepository:
    """Репозиторий расписания постинга"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_group_id(self, group_id: int) -> Optional[PostSchedule]:
        """Получить расписание по группе"""
        result = await self.session.execute(
            select(PostSchedule).where(PostSchedule.group_id == group_id)
        )
        return result.scalar()

    async def update(self, schedule_id: int, data: dict) -> Optional[PostSchedule]:
        """Обновить расписание"""
        result = await self.session.execute(
            select(PostSchedule).where(PostSchedule.id == schedule_id)
        )
        schedule = result.scalar()
        if schedule:
            for key, value in data.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            await self.session.commit()
            await self.session.refresh(schedule)
        return schedule


class PostHistoryRepository:
    """Репозиторий истории постов"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> PostHistory:
        """Создать запись о посте"""
        history = PostHistory(**data)
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def update_stats(self, message_id: int, views: int = None, clicks: int = None):
        """Обновить статистику поста"""
        result = await self.session.execute(
            select(PostHistory).where(PostHistory.message_id == message_id)
        )
        history = result.scalar()
        if history:
            if views is not None:
                history.views = views
            if clicks is not None:
                history.clicks = clicks
            await self.session.commit()


class OrderRepository:
    """Репозиторий заказов"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Order:
        """Создать заказ"""
        order = Order(**data)
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar()

    async def get_all(self, status: str = None, limit: int = 50) -> List[Order]:
        """Получить все заказы (с фильтрацией)"""
        query = select(Order).order_by(Order.created_at.desc()).limit(limit)
        if status:
            query = query.where(Order.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(self, order_id: int, status: str) -> Optional[Order]:
        """Обновить статус заказа"""
        order = await self.get_by_id(order_id)
        if order:
            order.status = status
            if status == 'paid':
                order.paid_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(order)
        return order

    async def add_item(self, order_id: int, product_id: int, quantity: int = 1, size: str = None):
        """Добавить товар в заказ"""
        from app.db.models import Product

        product_result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar()

        if product:
            item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                price_inr=product.price_inr,
                price_rub=product.price_rub,
                size=size
            )
            self.session.add(item)

            # Обновляем сумму заказа
            order = await self.get_by_id(order_id)
            order.total_inr += product.price_inr * quantity
            order.total_rub += product.price_rub * quantity
            await self.session.commit()

    async def count(self) -> int:
        """Посчитать количество заказов"""
        result = await self.session.execute(select(func.count(Order.id)))
        return result.scalar() or 0


class UserRepository:
    """Репозиторий пользователей"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, telegram_id: int, username: str = None, first_name: str = None) -> User:
        """Получить или создать пользователя"""
        result = await self.session.execute(select(User).where(User.telegram_id == str(telegram_id)))
        user = result.scalar()

        if not user:
            user = User(
                telegram_id=str(telegram_id),
                username=username,
                first_name=first_name
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

        return user


class SettingRepository:
    """Репозиторий настроек"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[str]:
        """Получить настройку"""
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar()
        return setting.value if setting else None

    async def set(self, key: str, value: str):
        """Установить настройку"""
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar()

        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            self.session.add(setting)

        await self.session.commit()

    async def get_json(self, key: str) -> Optional[dict]:
        """Получить JSON настройку"""
        value = await self.get(key)
        return json.loads(value) if value else None

    async def set_json(self, key: str, value: dict):
        """Установить JSON настройку"""
        await self.set(key, json.dumps(value))


class ManagerRepository:
    """Репозиторий менеджеров"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, telegram_id: str, username: str, first_name: str = None, last_name: str = None) -> Manager:
        """Создать менеджера"""
        # Проверяем существующего по telegram_id
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            # Активируем если был деактивирован
            existing.is_active = True
            existing.username = username.lstrip('@')
            existing.first_name = first_name
            existing.last_name = last_name
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        # Проверяем по username
        existing_by_username = await self.get_by_username(username)
        if existing_by_username:
            existing_by_username.is_active = True
            existing_by_username.telegram_id = telegram_id
            existing_by_username.first_name = first_name
            existing_by_username.last_name = last_name
            await self.session.commit()
            await self.session.refresh(existing_by_username)
            return existing_by_username

        # Создаём нового
        manager = Manager(
            telegram_id=str(telegram_id),
            username=username.lstrip('@'),
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(manager)
        await self.session.commit()
        await self.session.refresh(manager)
        return manager

    async def get_by_id(self, manager_id: int) -> Optional[Manager]:
        """Получить менеджера по ID"""
        result = await self.session.execute(select(Manager).where(Manager.id == manager_id))
        return result.scalar()

    async def get_by_telegram_id(self, telegram_id: str) -> Optional[Manager]:
        """Получить менеджера по Telegram ID"""
        result = await self.session.execute(select(Manager).where(Manager.telegram_id == str(telegram_id)))
        return result.scalar()

    async def get_by_username(self, username: str) -> Optional[Manager]:
        """Получить менеджера по username"""
        result = await self.session.execute(
            select(Manager).where(Manager.username == username.lstrip('@'))
        )
        return result.scalar()

    async def get_all_active(self) -> List[Manager]:
        """Получить всех активных менеджеров"""
        result = await self.session.execute(
            select(Manager).where(Manager.is_active == True).order_by(Manager.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(self) -> List[Manager]:
        """Получить всех менеджеров (включая неактивных)"""
        result = await self.session.execute(
            select(Manager).order_by(Manager.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, manager_id: int, data: dict) -> Optional[Manager]:
        """Обновить менеджера"""
        manager = await self.get_by_id(manager_id)
        if manager:
            for key, value in data.items():
                if hasattr(manager, key):
                    setattr(manager, key, value)
            await self.session.commit()
            await self.session.refresh(manager)
        return manager

    async def deactivate(self, manager_id: int):
        """Деактивировать менеджера (мягкое удаление)"""
        manager = await self.get_by_id(manager_id)
        if manager:
            manager.is_active = False
            await self.session.commit()

    async def delete(self, manager_id: int):
        """Полное удаление менеджера"""
        manager = await self.get_by_id(manager_id)
        if manager:
            await self.session.delete(manager)
            await self.session.commit()

    async def set_main(self, manager_id: int):
        """Назначить главного менеджера"""
        # Сбрасываем всех главных
        await self.session.execute(
            text("UPDATE managers SET is_main = 0 WHERE is_main = 1")
        )
        # Назначаем нового
        manager = await self.get_by_id(manager_id)
        if manager:
            manager.is_main = True
            await self.session.commit()

    async def increment_queries(self, manager_id: int):
        """Увеличить счётчик запросов"""
        manager = await self.get_by_id(manager_id)
        if manager:
            manager.total_queries += 1
            manager.last_active_at = datetime.utcnow()
            await self.session.commit()

    async def increment_orders(self, manager_id: int):
        """Увеличить счётчик заказов"""
        manager = await self.get_by_id(manager_id)
        if manager:
            manager.total_orders += 1
            await self.session.commit()

    async def count(self) -> int:
        """Посчитать количество активных менеджеров"""
        result = await self.session.execute(
            select(func.count(Manager.id)).where(Manager.is_active == True)
        )
        return result.scalar() or 0
