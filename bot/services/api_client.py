import logging
from typing import Optional, List, Dict, Any
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    """Клиент для работы с Django API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start(self):
        """Инициализация сессии"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Базовый метод для запросов"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.pop('headers', {})
        
        if token:
            headers['Authorization'] = f'Token {token}'
        
        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response: #type: ignore
                if response.status == 204:  # No content
                    return {}
                
                data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"API Error {response.status}: {data}")
                    raise APIError(response.status, data)
                
                return data
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            raise APIError(0, str(e))
    
    # Auth endpoints
    async def register_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Регистрация/авторизация пользователя через Telegram"""
        data = {
            'telegram_id': telegram_id,
            'telegram_username': username,
            'first_name': first_name or '',
            'last_name': last_name or ''
        }
        return await self._request('POST', '/auth/telegram/', json=data)
    
    async def get_current_user(self, token: str) -> Dict[str, Any]:
        """Получить информацию о текущем пользователе"""
        return await self._request('GET', '/auth/me/', token=token)
    
    # Task endpoints
    async def get_tasks(
        self,
        token: str,
        status: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Получить список задач"""
        params = {}
        if status:
            params['status'] = status
        if category_id:
            params['category'] = category_id
        
        response = await self._request('GET', '/tasks/my/', token=token, params=params)
        
        # Handle pagination
        if 'results' in response:
            return response['results']
        return response if isinstance(response, list) else []
    
    async def get_task(self, token: str, task_id: str) -> Dict[str, Any]:
        """Получить детали задачи"""
        return await self._request('GET', f'/tasks/{task_id}/', token=token)
    
    async def create_task(
        self,
        token: str,
        title: str,
        description: str = '',
        deadline: Optional[str] = None,
        category_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Создать новую задачу"""
        data = {
            'title': title,
            'description': description,
        }
        if deadline:
            data['deadline'] = deadline
        if category_ids:
            data['category_ids'] = category_ids #type: ignore
        
        return await self._request('POST', '/tasks/', token=token, json=data)
    
    async def update_task(
        self,
        token: str,
        task_id: str,
        **fields
    ) -> Dict[str, Any]:
        """Обновить задачу"""
        return await self._request('PATCH', f'/tasks/{task_id}/', token=token, json=fields)
    
    async def delete_task(self, token: str, task_id: str) -> None:
        """Удалить задачу"""
        await self._request('DELETE', f'/tasks/{task_id}/', token=token)
    
    async def complete_task(self, token: str, task_id: str) -> Dict[str, Any]:
        """Отметить задачу выполненной"""
        return await self._request('POST', f'/tasks/{task_id}/complete/', token=token)
    
    async def cancel_task(self, token: str, task_id: str) -> Dict[str, Any]:
        """Отменить задачу"""
        return await self._request('POST', f'/tasks/{task_id}/cancel/', token=token)
    
    async def get_overdue_tasks(self, token: str) -> List[Dict[str, Any]]:
        """Получить просроченные задачи"""
        response = await self._request('GET', '/tasks/overdue/', token=token)
        if 'results' in response:
            return response['results']
        return response if isinstance(response, list) else []
    
    # Category endpoints
    async def get_categories(self, token: str) -> List[Dict[str, Any]]:
        """Получить список категорий"""
        response = await self._request('GET', '/categories/', token=token)
        if 'results' in response:
            return response['results']
        return response if isinstance(response, list) else []
    
    async def create_category(
        self,
        token: str,
        name: str,
        color: str = '#808080'
    ) -> Dict[str, Any]:
        """Создать категорию"""
        return await self._request(
            'POST',
            '/categories/',
            token=token,
            json={'name': name, 'color': color}
        )


class APIError(Exception):
    """Ошибка API"""
    
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error {status_code}: {detail}")