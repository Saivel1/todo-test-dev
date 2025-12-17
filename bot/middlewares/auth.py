from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.token_storage import token_storage
from services.api_client import APIClient


class AuthMiddleware(BaseMiddleware):
    """Middleware для автоматической аутентификации"""
    
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user

        if user is None:
            return
        
        # Проверяем есть ли токен
        token = token_storage.get_token(user.id)
        
        if not token:
            # Регистрируем пользователя
            try:
                result = await self.api_client.register_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                token = result['token']
                token_storage.save_token(user.id, token)
            except Exception as e:
                if isinstance(event, Message):
                    await event.answer(
                        "❌ Ошибка аутентификации. Попробуйте позже."
                    )
                return
        
        # Добавляем токен в data
        data['token'] = token
        data['api_client'] = self.api_client
        
        return await handler(event, data) #type: ignore