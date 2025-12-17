import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from apps.users.models import User
from apps.tasks.models import Task, Category


@pytest.fixture
def api_client():
    """Фикстура для API клиента"""
    return APIClient()


@pytest.fixture
def user(db):
    """Фикстура для создания тестового пользователя"""
    return User.objects.create_user(
        username='testuser',
        telegram_id=123456789,
        telegram_username='test_user',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def another_user(db):
    """Фикстура для второго пользователя (для тестов изоляции)"""
    return User.objects.create_user(
        username='anotheruser',
        telegram_id=987654321,
        telegram_username='another_user'
    )


@pytest.fixture
def user_token(user):
    """Фикстура для токена пользователя"""
    token, _ = Token.objects.get_or_create(user=user)
    return token.key


@pytest.fixture
def authenticated_client(api_client, user_token):
    """Фикстура для аутентифицированного клиента"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {user_token}')
    return api_client


@pytest.fixture
def category(db):
    """Фикстура для создания категории"""
    return Category.objects.create(
        name='Работа',
        color='#FF5733'
    )


@pytest.fixture
def task(user, category, db):
    """Фикстура для создания задачи"""
    task = Task.objects.create(
        user=user,
        title='Тестовая задача',
        description='Описание',
        status=Task.Status.PENDING
    )
    task.categories.add(category)
    return task


@pytest.fixture
def multiple_tasks(user, category, db):
    """Фикстура для создания нескольких задач"""
    tasks = []
    for i in range(5):
        task = Task.objects.create(
            user=user,
            title=f'Задача {i+1}',
            description=f'Описание {i+1}',
            status=Task.Status.PENDING if i % 2 == 0 else Task.Status.COMPLETED
        )
        task.categories.add(category)
        tasks.append(task)
    return tasks