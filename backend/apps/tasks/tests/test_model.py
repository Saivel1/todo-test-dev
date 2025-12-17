import pytest
from django.utils import timezone
from datetime import timedelta

from apps.tasks.models import Task, Category
from apps.users.models import User


@pytest.mark.django_db
class TestCategory:
    """Тесты для модели Category"""
    
    def test_create_category(self):
        """Тест создания категории"""
        category = Category.objects.create(
            name='Тест',
            color='#123456'
        )
        
        assert category.name == 'Тест'
        assert category.color == '#123456'
        assert len(category.id) == 26  # ULID длина
        assert category.created_at is not None
    
    def test_category_str(self):
        """Тест __str__ метода"""
        category = Category.objects.create(name='Работа')
        assert str(category) == 'Работа'
    
    def test_category_unique_name(self):
        """Тест уникальности имени категории"""
        Category.objects.create(name='Уникальная')
        
        with pytest.raises(Exception):  # IntegrityError
            Category.objects.create(name='Уникальная')
    
    def test_ulid_primary_key(self):
        """Тест что PK является ULID"""
        cat1 = Category.objects.create(name='Cat1')
        cat2 = Category.objects.create(name='Cat2')
        
        # ULID должен быть лексикографически сортируемым
        assert cat1.id < cat2.id  # cat1 создан раньше
        assert len(cat1.id) == 26
        assert cat1.id.isalnum()


@pytest.mark.django_db
class TestTask:
    """Тесты для модели Task"""
    
    def test_create_task(self, user, category):
        """Тест создания задачи"""
        task = Task.objects.create(
            user=user,
            title='Тестовая задача',
            description='Описание',
            status=Task.Status.PENDING
        )
        task.categories.add(category)
        
        assert task.title == 'Тестовая задача'
        assert task.user == user
        assert task.status == Task.Status.PENDING
        assert task.categories.count() == 1
        assert len(task.id) == 26  # ULID
    
    def test_task_str(self, user):
        """Тест __str__ метода"""
        task = Task.objects.create(
            user=user,
            title='Моя задача'
        )
        assert 'Моя задача' in str(task)
    
    def test_is_overdue_property(self, user):
        """Тест свойства is_overdue"""
        # Задача без дедлайна
        task1 = Task.objects.create(user=user, title='Без дедлайна')
        assert task1.is_overdue is False
        
        # Задача с будущим дедлайном
        task2 = Task.objects.create(
            user=user,
            title='Будущий дедлайн',
            deadline=timezone.now() + timedelta(days=1)
        )
        assert task2.is_overdue is False
        
        # Просроченная задача
        task3 = Task.objects.create(
            user=user,
            title='Просроченная',
            deadline=timezone.now() - timedelta(days=1),
            status=Task.Status.PENDING
        )
        assert task3.is_overdue is True
        
        # Завершённая задача не считается просроченной
        task4 = Task.objects.create(
            user=user,
            title='Завершённая',
            deadline=timezone.now() - timedelta(days=1),
            status=Task.Status.COMPLETED
        )
        assert task4.is_overdue is False
    
    def test_should_send_notification(self, user):
        """Тест метода should_send_notification"""
        # Задача без дедлайна
        task1 = Task.objects.create(user=user, title='Без дедлайна')
        assert task1.should_send_notification() is False
        
        # Задача с дедлайном через 2 часа
        task2 = Task.objects.create(
            user=user,
            title='Через 2 часа',
            deadline=timezone.now() + timedelta(hours=2),
            notification_sent=False
        )
        assert task2.should_send_notification() is False
        
        # Задача с дедлайном через 30 минут
        task3 = Task.objects.create(
            user=user,
            title='Через 30 минут',
            deadline=timezone.now() + timedelta(minutes=30),
            notification_sent=False
        )
        assert task3.should_send_notification() is True
        
        # Уже отправлено уведомление
        task4 = Task.objects.create(
            user=user,
            title='Уведомление отправлено',
            deadline=timezone.now() + timedelta(minutes=30),
            notification_sent=True
        )
        assert task4.should_send_notification() is False
        
        # Просроченная задача
        task5 = Task.objects.create(
            user=user,
            title='Просроченная',
            deadline=timezone.now() - timedelta(hours=1),
            notification_sent=False
        )
        assert task5.should_send_notification() is True
    
    def test_task_timestamps(self, user):
        """Тест автоматических timestamp полей"""
        task = Task.objects.create(user=user, title='Тест')
        
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.created_at <= task.updated_at
        
        # Обновляем задачу
        old_updated = task.updated_at
        task.title = 'Новое название'
        task.save()
        task.refresh_from_db()
        
        assert task.updated_at > old_updated


@pytest.mark.django_db
class TestUser:
    """Тесты для модели User"""
    
    def test_create_user_with_telegram(self):
        """Тест создания пользователя с Telegram ID"""
        user = User.objects.create_user(
            username='telegram_user',
            telegram_id=123456789,
            telegram_username='tg_user'
        )
        
        assert user.telegram_id == 123456789
        assert user.telegram_username == 'tg_user'
    
    def test_telegram_id_unique(self):
        """Тест уникальности telegram_id"""
        User.objects.create_user(
            username='user1',
            telegram_id=111111
        )
        
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                username='user2',
                telegram_id=111111
            )
    
    def test_user_str(self):
        """Тест __str__ метода"""
        user = User.objects.create_user(
            username='test',
            telegram_id=123,
            telegram_username='tguser'
        )
        
        assert '@tguser' in str(user)
        assert '123' in str(user)