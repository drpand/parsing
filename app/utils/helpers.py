"""
Helper functions IndiaShop Bot v2.0
"""

import html
from typing import List, Optional


def safe_html(text: str) -> str:
    """Экранирование HTML"""
    if not text:
        return ""
    return html.escape(str(text))


def truncate_text(text: str, max_length: int = 50) -> str:
    """Обрезка текста"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def calculate_price_rub(
    price_inr: float,
    usd_inr: float,
    usd_rub: float,
    margin_percent: float,
    delivery_fixed: float,
    delivery_percent: float,
) -> float:
    """
    Расчёт цены в рублях.

    Формула:
    1. Конвертируем INR → USD → RUB
    2. Добавляем наценку %
    3. Добавляем доставку (фикс + %)
    """
    if not price_inr:
        return 0.0

    # Конвертация
    price_usd = price_inr / usd_inr
    price_rub_base = price_usd * usd_rub

    # Наценка
    price_with_margin = price_rub_base * (1 + margin_percent / 100)

    # Доставка
    delivery_total = delivery_fixed + (price_rub_base * delivery_percent / 100)

    # Итого
    total = price_with_margin + delivery_total

    return round(total, 2)


def format_price(price: float, currency: str = "₽") -> str:
    """Форматирование цены"""
    return f"{price:,.0f} {currency}"


def parse_bool(value: str) -> bool:
    """Парсинг булевого значения"""
    return value.lower() in ('true', '1', 'yes', 'да')


def parse_list_str(value: str) -> List[str]:
    """Парсинг строки списка (CSV)"""
    if not value:
        return []
    return [x.strip() for x in value.split(",")]
