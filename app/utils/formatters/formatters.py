# app/utils/formatters/formatters.py
"""
Форматтеры для цен, текста, дат.
Взято из старого парсера + адаптировано для v1.0
"""

from typing import Optional, List, Dict, Any


def fmt_inr(value: Optional[float], with_symbol: bool = True) -> str:
    """
    Форматирование цены в INR.
    
    Args:
        value: Цена в рупиях
        with_symbol: Добавить символ ₹
        
    Returns:
        str: Форматированная цена (например: "₹3 550")
    """
    if value is None:
        return "—"
    
    try:
        v = int(round(float(value)))
    except Exception:
        return "—"
    
    # Пробелы как разделители тысяч: 3 550
    s = f"{v:,}".replace(",", " ")
    
    if with_symbol:
        return f"₹{s}"
    return s


def fmt_rub(value: Optional[float], with_symbol: bool = True) -> str:
    """
    Форматирование цены в RUB.
    
    Args:
        value: Цена в рублях
        with_symbol: Добавить символ ₽
        
    Returns:
        str: Форматированная цена (например: "4 000 ₽")
    """
    if value is None:
        return "—"
    
    try:
        v = int(round(float(value)))
    except Exception:
        return "—"
    
    s = f"{v:,}".replace(",", " ")
    
    if with_symbol:
        return f"{s} ₽"
    return s


def fmt_product_title(title: Optional[str], max_length: int = 50) -> str:
    """
    Форматирование названия товара.
    
    Args:
        title: Название товара
        max_length: Максимальная длина
        
    Returns:
        str: Обрезанное название с троеточием
    """
    if not title:
        return "Товар"
    
    title = title.strip()
    
    if len(title) <= max_length:
        return title
    
    return title[:max_length - 3] + "..."


def fmt_sizes(sizes: Optional[List[str]], separator: str = " · ") -> str:
    """
    Форматирование размеров.
    
    Args:
        sizes: Список размеров
        separator: Разделитель
        
    Returns:
        str: Форматированные размеры
    """
    if not sizes:
        return "—"
    
    return separator.join(sizes)


def fmt_discount(percent: Optional[float], original: Optional[float], current: Optional[float]) -> str:
    """
    Форматирование скидки.
    
    Args:
        percent: Процент скидки
        original: Оригинальная цена
        current: Текущая цена
        
    Returns:
        str: Форматированная скидка
    """
    if percent and percent > 0:
        return f"{int(percent)}% OFF"
    
    if original and current and original > current:
        calc_percent = ((original - current) / original) * 100
        return f"{int(calc_percent)}% OFF"
    
    return "—"


def fmt_product_card(product: Dict[str, Any]) -> str:
    """
    Форматирование карточки товара для отображения.
    
    Args:
        product: Данные товара
        
    Returns:
        str: Форматированная карточка
    """
    title = fmt_product_title(product.get('title', 'Товар'))
    brand = product.get('brand', '')
    price_inr = fmt_inr(product.get('price_inr'))
    price_rub = fmt_rub(product.get('price_rub'))
    discount = fmt_discount(
        product.get('discount_percent'),
        product.get('original_price_inr'),
        product.get('price_inr')
    )
    
    lines = [
        f"🛍 {title}",
    ]
    
    if brand:
        lines.append(f"🏷 Бренд: {brand}")
    
    lines.append(f"💰 Цена: {price_inr} ({price_rub})")
    
    if discount != "—":
        lines.append(f"🔻 Скидка: {discount}")
    
    return "\n".join(lines)
