"""
Модели базы данных IndiaShop Bot v2.0
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Пользователи (клиенты)"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    language_code = Column(String, default='ru')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    orders = relationship('Order', back_populates='user', lazy='select')

    def __repr__(self):
        return f'<User {self.telegram_id} ({self.username})>'


class Product(Base):
    """Товары"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    source_url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, default='other')
    gender = Column(String, default='U')  # M/F/U

    # Цены
    price_inr = Column(Float, default=0.0)
    original_price_inr = Column(Float)
    price_rub = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)

    # Изображения и размеры (JSON)
    images = Column(JSON, default=list)
    sizes = Column(JSON, default=list)

    # Статусы
    in_stock = Column(Boolean, default=True)
    is_on_sale = Column(Boolean, default=False)  # Есть ли скидка
    is_hot_deal = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_posted_at = Column(DateTime)  # Когда последний раз постили

    # Связи
    order_items = relationship('OrderItem', back_populates='product', lazy='select')
    post_history = relationship('PostHistory', back_populates='product', lazy='select')

    def __repr__(self):
        return f'<Product {self.id}: {self.title[:30]}>'


class PostGroup(Base):
    """Группы для авто-постинга"""
    __tablename__ = 'post_groups'

    id = Column(Integer, primary_key=True)
    chat_id = Column(String, unique=True, nullable=False)
    chat_name = Column(String)
    chat_username = Column(String)  # @username
    chat_type = Column(String, default='supergroup')  # group/supergroup/channel

    # Статус
    is_active = Column(Boolean, default=True)
    bot_is_admin = Column(Boolean, default=False)

    # Статистика
    posts_count = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    last_post_at = Column(DateTime)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    schedule = relationship('PostSchedule', back_populates='group', lazy='select', uselist=False)
    post_history = relationship('PostHistory', back_populates='group', lazy='select')

    def __repr__(self):
        return f'<PostGroup {self.chat_name} ({self.chat_id})>'


class PostSchedule(Base):
    """Расписание постинга для группы"""
    __tablename__ = 'post_schedule'

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('post_groups.id'), nullable=False, unique=True)

    # Настройки
    posts_per_hour = Column(Integer, default=5)  # Сколько постов в час
    interval_minutes = Column(Integer, default=12)  # Интервал между постами (60/5=12)
    start_hour = Column(Integer, default=9)  # Начало (9:00)
    end_hour = Column(Integer, default=23)  # Конец (23:00)
    days_of_week = Column(JSON, default=[0, 1, 2, 3, 4, 5, 6])  # Пн-Вс

    # Фильтры товаров
    min_discount = Column(Integer, default=0)  # Мин. скидка %
    only_hot_deals = Column(Boolean, default=False)  # Только горячие

    # Статус
    is_active = Column(Boolean, default=True)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    group = relationship('PostGroup', back_populates='schedule')

    def __repr__(self):
        return f'<PostSchedule group_id={self.group_id}>'


class PostHistory(Base):
    """История отправленных постов"""
    __tablename__ = 'post_history'

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('post_groups.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)

    # Сообщение в Telegram
    message_id = Column(Integer)

    # Статистика
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)

    # Статус
    status = Column(String, default='sent')  # sent/failed/error
    error_message = Column(Text)

    # Дата
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Связи
    group = relationship('PostGroup', back_populates='post_history')
    product = relationship('Product', back_populates='post_history')

    def __repr__(self):
        return f'<PostHistory group={self.group_id} product={self.product_id}>'


class Order(Base):
    """Заказы от клиентов"""
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Статус заказа
    status = Column(String, default='pending')  # pending/confirmed/paid/shipped/delivered/cancelled

    # Данные клиента
    customer_name = Column(String)
    contact_phone = Column(String)
    delivery_address = Column(Text)
    comment = Column(Text)

    # Суммы
    total_inr = Column(Float, default=0.0)
    total_rub = Column(Float, default=0.0)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime)

    # Связи
    user = relationship('User', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', lazy='select', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.id} user={self.user_id} status={self.status}>'


class OrderItem(Base):
    """Позиции заказа"""
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)

    # Количество и цена
    quantity = Column(Integer, default=1)
    price_inr = Column(Float, default=0.0)
    price_rub = Column(Float, default=0.0)
    size = Column(String)  # Выбранный размер

    # Связи
    order = relationship('Order', back_populates='items')
    product = relationship('Product', back_populates='order_items')

    def __repr__(self):
        return f'<OrderItem order={self.order_id} product={self.product_id}>'


class Setting(Base):
    """Настройки бота"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'


class Manager(Base):
    """Менеджеры для связи с клиентами"""
    __tablename__ = 'managers'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)

    # Статус
    is_active = Column(Boolean, default=True)
    is_main = Column(Boolean, default=False)  # Главный менеджер

    # Статистика
    total_orders = Column(Integer, default=0)
    total_queries = Column(Integer, default=0)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime)

    def __repr__(self):
        return f'<Manager {self.username} (ID: {self.telegram_id})>'
