# Backend - Django REST API

## Технологии

- Django 5.1.4
- Django REST Framework 3.15.2
- PostgreSQL 16
- Celery 5.4.0
- Redis 7
- pytest для тестирования

## API Endpoints

См. главный README.md

## Локальная разработка
```bash
# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Запустить сервер
python manage.py runserver

# В другом терминале - Celery worker
celery -A config worker --loglevel=info

# В третьем терминале - Celery beat
celery -A config beat --loglevel=info
```

## Тесты
```bash
# Все тесты
pytest

# С покрытием
pytest --cov=apps --cov-report=html

# Конкретный файл
pytest apps/tasks/tests/test_api.py

# Verbose
pytest -vv
```

## Миграции
```bash
# Создать миграции
python manage.py makemigrations

# Применить
python manage.py migrate

# Откатить
python manage.py migrate app_name migration_name
```