# app/services/proxy/proxy_manager.py
"""
Proxy Manager для ротации прокси при парсинге.
Взято из старого парсера + адаптировано для v1.0
"""

import random
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ProxyManager:
    """Менеджер прокси для ротации при парсинге"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_next_proxy(self) -> Optional[dict]:
        """
        Берёт случайный активный прокси из списка.
        Если нет ни одного — вернёт None (парсим без прокси).
        
        Returns:
            dict | None: Прокси в формате {'host': ..., 'port': ..., ...}
        """
        # 🔐 TODO: Добавить модель Proxy в БД
        # Сейчас возвращаем None (парсим без прокси)
        # Когда добавим модель — раскомментировать код:
        
        # proxies = (await self.session.execute(
        #     select(Proxy).where(Proxy.is_active == True)
        # )).scalars().all()
        # 
        # if not proxies:
        #     return None
        # 
        # proxy = random.choice(proxies)
        # proxy.last_used_at = datetime.utcnow()
        # await self.session.commit()
        # return proxy
        
        return None
    
    def get_proxy_args(self, proxy: Optional[dict]) -> Optional[dict]:
        """
        Конвертирует прокси в аргументы для Selenium/requests.
        
        Args:
            proxy: Прокси из get_next_proxy()
            
        Returns:
            dict | None: Аргументы для браузера
        """
        if not proxy:
            return None
        
        # Для Selenium
        return {
            'proxy': f"{proxy['host']}:{proxy['port']}",
            'proxy_auth': f"{proxy['username']}:{proxy['password']}" if proxy.get('username') else None
        }
