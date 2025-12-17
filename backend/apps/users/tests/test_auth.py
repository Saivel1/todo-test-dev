import pytest
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.users.models import User


@pytest.mark.django_db
class TestTelegramAuth:
    """Тесты для Telegram аутентификации"""
    
    def test_register_new_user(self, api_client):
        """Тест регистрации нового пользователя"""
        response = api_client.post('/api/auth/telegram/', {
            'telegram_id': 123456789,
            'telegram_username': 'new_user',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'token' in response.data
        assert 'user' in response.data
        assert response.data['created'] is True
        assert response.data['user']['telegram_id'] == 123456789
        
        # Проверяем что пользователь создан в БД
        user = User.objects.get(telegram_id=123456789)
        assert user.telegram_username == 'new_user'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'
        
        # Проверяем что токен создан
        token = Token.objects.get(user=user)
        assert token.key == response.data['token']
    
    def test_login_existing_user(self, api_client, user):
        """Тест авторизации существующего пользователя"""
        response = api_client.post('/api/auth/telegram/', {
            'telegram_id': user.telegram_id,
            'telegram_username': 'updated_username'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['created'] is False
        assert 'token' in response.data
        
        # Проверяем что username обновился
        user.refresh_from_db()
        assert user.telegram_username == 'updated_username'
    
    def test_register_without_telegram_id(self, api_client):
        """Тест регистрации без telegram_id"""
        response = api_client.post('/api/auth/telegram/', {
            'telegram_username': 'user'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'telegram_id' in response.data
    
    def test_register_with_invalid_telegram_id(self, api_client):
        """Тест с невалидным telegram_id"""
        response = api_client.post('/api/auth/telegram/', {
            'telegram_id': -123
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'telegram_id' in response.data
    
    def test_get_current_user(self, authenticated_client, user):
        """Тест получения информации о текущем пользователе"""
        response = authenticated_client.get('/api/auth/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['telegram_id'] == user.telegram_id
        assert response.data['username'] == user.username
    
    def test_get_current_user_unauthorized(self, api_client):
        """Тест получения профиля без аутентификации"""
        response = api_client.get('/api/auth/me/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout(self, authenticated_client, user):
        """Тест выхода из системы"""
        # Проверяем что токен существует
        assert Token.objects.filter(user=user).exists()
        
        response = authenticated_client.post('/api/auth/logout/')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем что токен удалён
        assert not Token.objects.filter(user=user).exists()
    
    def test_logout_unauthorized(self, api_client):
        """Тест выхода без аутентификации"""
        response = api_client.post('/api/auth/logout/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED