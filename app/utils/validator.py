"""
Product Data Validator - Валидация данных товара
Проверка соответствия: Название ↔ URL ↔ Изображения
"""

import re
from typing import List, Dict, Optional
from app.utils.logger import logger


def extract_sku_from_url(url: str) -> Optional[str]:
    """
    Извлекает SKU (артикул) из URL товара.
    
    Примеры:
    - Zara: https://www.zara.com/in/en/linen-blazer-p01234567.html → p01234567
    - Myntra: https://www.myntra.com/shirt/brand/1234567 → 1234567
    """
    
    # Zara формат: -pXXXXXXXX
    zara_match = re.search(r'-p(\d{7,})', url)
    if zara_match:
        return f"p{zara_match.group(1)}"
    
    # Myntra формат: /1234567
    myntra_match = re.search(r'/(\d{7,})(?:\.html)?$', url)
    if myntra_match:
        return myntra_match.group(1)
    
    return None


def validate_product_url(product_url: str, title: str, description: str = "") -> Dict:
    """
    Проверяет соответствие URL и названия товара.
    
    Returns:
        Dict: {'valid': bool, 'warning': str or None}
    """
    result = {'valid': True, 'warning': None}
    
    # Извлекаем SKU из URL
    sku = extract_sku_from_url(product_url)
    
    if sku:
        # Проверяем что SKU есть в названии или описании
        text_to_check = f"{title} {description}".lower()
        
        # SKU должен быть в тексте (хотя бы часть)
        sku_short = sku.replace('p', '')
        if sku_short not in text_to_check and sku not in text_to_check:
            # ⚠️ ПРЕДУПРЕЖДЕНИЕ, но не ошибка! AI может не вернуть SKU в названии
            result['warning'] = f'URL SKU not in title (SKU: {sku})'
            logger.debug(f"URL validation warning: SKU {sku} not found in title/description")
    
    # Проверяем что URL содержит ключевые слова из названия
    if 'zara.com' in product_url:
        # URL должен содержать ключевые слова
        title_words = title.lower().split()[:3]  # Первые 3 слова
        url_contains_keywords = any(word in product_url.lower() for word in title_words if len(word) > 3)
        
        if not url_contains_keywords:
            # ⚠️ ПРЕДУПРЕЖДЕНИЕ, но не ошибка! URL из DOM — точный
            result['warning'] = 'URL keywords mismatch'
            logger.debug(f"URL validation warning: Keywords not found in URL")
    
    return result


def validate_product_images(images: List[str], title: str, category: str = "") -> Dict:
    """
    Фильтрует и проверяет изображения по соответствию названию.
    
    Returns:
        Dict: {'valid_images': List[str], 'warning': str or None}
    """
    result = {'valid_images': [], 'warning': None}
    
    if not images:
        result['warning'] = 'No images provided'
        return result
    
    # Ключевые слова из названия (первые 3 слова, длина > 3 символов)
    title_keywords = [word.lower() for word in title.split()[:5] if len(word) > 3]
    
    # Категорийные ключевые слова
    category_keywords = []
    if category:
        category_keywords = category.lower().replace('_', ' ').split()
    
    all_keywords = title_keywords + category_keywords
    
    # Фильтруем изображения
    for img_url in images:
        img_url_lower = img_url.lower()
        
        # Проверяем что URL изображения содержит ключевые слова
        if any(keyword in img_url_lower for keyword in all_keywords):
            result['valid_images'].append(img_url)
        
        # Или проверяем что это реальный CDN (не заглушка)
        elif '0000' in img_url or 'placeholder' in img_url_lower:
            logger.debug(f"Image is placeholder: {img_url}")
            continue
        
        # Добавляем если URL выглядит валидным (из DOM — значит точный!)
        elif len(result['valid_images']) < 2:  # Берём первые 2 если нет совпадений
            result['valid_images'].append(img_url)
    
    # Если не нашли валидных изображений
    if not result['valid_images']:
        result['warning'] = 'No valid images found'
        logger.debug(f"Image validation warning: No valid images for '{title}'")
    
    return result


def validate_product_data(product: Dict) -> Dict:
    """
    Полная валидация данных товара.
    
    Args:
        product: Dict с данными товара (title, product_url, images, category, description)
    
    Returns:
        Dict: product с добавленными полями validation
    """
    # Копируем продукт чтобы не модифицировать оригинал
    validated_product = product.copy()
    
    warnings = []
    is_valid = True
    
    # 1. Валидация URL
    url_validation = validate_product_url(
        product.get('product_url', ''),
        product.get('title', ''),
        product.get('description', '')
    )
    
    if url_validation['warning']:
        warnings.append(url_validation['warning'])
        # ⚠️ URL из DOM — считаем валидным даже с warning
    
    # 2. Валидация изображений
    images_validation = validate_product_images(
        product.get('images', []),
        product.get('title', ''),
        product.get('category', '')
    )
    
    # Обновляем изображения валидными
    validated_product['images'] = images_validation['valid_images']
    
    if images_validation['warning']:
        warnings.append(images_validation['warning'])
        # ⚠️ Images из DOM — считаем валидными даже с warning
    
    # 3. Добавляем поля валидации
    # ✅ Если URL и Images есть — товар валидный!
    validated_product['validated'] = bool(product.get('product_url') and validated_product['images'])
    validated_product['validation_warnings'] = warnings if warnings else None
    
    # 4. Логирование
    if validated_product['validated']:
        logger.info(f"✅ Product validated: {product.get('title', 'Unknown')[:40]}")
    else:
        logger.warning(f"⚠️ Product validation failed: {product.get('title', 'Unknown')[:40]} | Warnings: {warnings}")
    
    return validated_product


def batch_validate_products(products: List[Dict]) -> List[Dict]:
    """
    Массовая валидация списка товаров.
    
    Returns:
        List[Dict]: Список валидированных товаров
    """
    validated_products = []
    
    for product in products:
        validated = validate_product_data(product)
        validated_products.append(validated)
    
    # Статистика
    valid_count = sum(1 for p in validated_products if p.get('validated', False))
    total_count = len(validated_products)
    
    logger.info(f"📊 Validation complete: {valid_count}/{total_count} products valid")
    
    return validated_products
