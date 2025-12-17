from typing import Optional, Dict


class TokenStorage:
    """Простое in-memory хранилище токенов"""
    
    def __init__(self):
        self._storage: Dict[int, str] = {}
    
    def save_token(self, user_id: int, token: str):
        """Сохранить токен пользователя"""
        self._storage[user_id] = token
    
    def get_token(self, user_id: int) -> Optional[str]:
        """Получить токен пользователя"""
        return self._storage.get(user_id)
    
    def remove_token(self, user_id: int):
        """Удалить токен пользователя"""
        self._storage.pop(user_id, None)
    
    def has_token(self, user_id: int) -> bool:
        """Проверить есть ли токен"""
        return user_id in self._storage


# Глобальное хранилище
token_storage = TokenStorage()