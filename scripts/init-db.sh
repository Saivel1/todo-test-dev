#!/bin/bash
set -e

echo "🔄 Waiting for database to be ready..."
sleep 5

echo "📦 Running migrations..."
python manage.py migrate

echo "👤 Creating superuser..."
python manage.py shell << END
from apps.users.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
END

echo "📊 Creating test data..."
python manage.py shell << END
from apps.tasks.models import Category, Task
from apps.users.models import User
from django.utils import timezone
from datetime import timedelta

# Создаём категории если их нет
categories_data = [
    ('Работа', '#FF5733'),
    ('Личное', '#33FF57'),
    ('Учёба', '#3357FF'),
]

for name, color in categories_data:
    Category.objects.get_or_create(name=name, defaults={'color': color})

print('✅ Categories created')

# Создаём тестового пользователя
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={
        'telegram_id': 123456789,
        'telegram_username': 'test_user'
    }
)

if created:
    # Создаём тестовые задачи
    work_cat = Category.objects.get(name='Работа')
    personal_cat = Category.objects.get(name='Личное')
    
    task1 = Task.objects.create(
        user=user,
        title='Завершить тестовое задание',
        description='Django + Aiogram бот',
        status=Task.Status.IN_PROGRESS,
        deadline=timezone.now() + timedelta(days=2)
    )
    task1.categories.add(work_cat)
    
    task2 = Task.objects.create(
        user=user,
        title='Купить продукты',
        description='Молоко, хлеб, яйца',
        status=Task.Status.PENDING,
        deadline=timezone.now() + timedelta(hours=3)
    )
    task2.categories.add(personal_cat)
    
    print('✅ Test user and tasks created')
else:
    print('ℹ️  Test user already exists')
END

echo "✅ Initialization complete!"