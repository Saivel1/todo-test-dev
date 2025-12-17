# Трудности и их решения

Документация проблем, с которыми столкнулись при разработке, и способы их решения.

## 1. Кастомные Primary Keys без UUID/Autoincrement

### Проблема
Требование задания: нельзя использовать UUID, модуль random, стандартные функции Postgres и целочисленные инкременты для PK.

### Решение
Использовали **ULID** (Universally Unique Lexicographically Sortable Identifier):
```python
from ulid import ULID

class ULIDField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 26
        kwargs['primary_key'] = True
        kwargs['editable'] = False
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)
    
    def pre_save(self, model_instance, add):
        if add and not getattr(model_instance, self.attname):
            value = str(ULID())
            setattr(model_instance, self.attname, value)
            return value
        return super().pre_save(model_instance, add)
```

**Преимущества ULID:**
- ✅ Лексикографически сортируемый (timestamp в начале)
- ✅ 128-bit как UUID, но более читаемый (26 символов)
- ✅ Без коллизий в распределённой системе
- ✅ Можно извлечь timestamp создания
- ✅ Base32 encoding (URL-safe)

**Пример ULID:** `01HXYZ9M4KQWERTYZXCVBNM123`

---

## 2. Timezone Management (America/Adak)

### Проблема
Требование: Django должна работать в timezone America/Adak (UTC-10 зимой, UTC-9 летом с учётом DST).

### Вызовы
- Все datetime должны быть timezone-aware
- Celery periodic tasks должны учитывать timezone
- API должен принимать и возвращать даты в правильном формате

### Решение

**Django settings:**
```python
TIME_ZONE = 'America/Adak'
USE_TZ = True  # Хранить в UTC, показывать в America/Adak
```

**В моделях:**
```python
deadline = models.DateTimeField('Срок выполнения', null=True, blank=True)
created_at = models.DateTimeField('Дата создания', auto_now_add=True)
```

**В Celery:**
```python
app.conf.update(
    timezone='America/Adak',
    enable_utc=True,
)
```

**В API responses:**
```python
# DRF автоматически конвертирует в timezone пользователя
'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
```

**Lessons learned:**
- Всегда использовать `timezone.now()` вместо `datetime.now()`
- Проверять `is_aware()` для datetime объектов
- Celery beat schedule использует timezone для cron jobs

---

## 3. Django 6.0 format_html() Breaking Changes

### Проблема
В Django 6.0 изменилось поведение `format_html()` - теперь он **всегда** требует аргументы для подстановки.

**Код который работал в Django 5.x:**
```python
format_html('<span style="color: red;">Text</span>')  # ❌ TypeError в 6.0
```

### Ошибка
```
TypeError: args or kwargs must be provided.
```

### Решение

**Вариант 1: mark_safe (использовали мы):**
```python
from django.utils.safestring import mark_safe

def color_badge(self, obj):
    return mark_safe(
        f'<span style="background-color: {obj.color}; '
        f'padding: 5px 10px;">{obj.color}</span>'
    )
```

**Вариант 2: format_html с плейсхолдерами:**
```python
def color_badge(self, obj):
    return format_html(
        '<span style="background-color: {};">{}</span>',
        obj.color, obj.color
    )
```

**Когда использовать что:**
- `mark_safe` - когда HTML статичный или используете f-strings
- `format_html` - когда нужно экранировать пользовательский ввод

---

## 4. PostgreSQL Permissions для Тестов

### Проблема
При запуске pytest получали ошибку:
```
psycopg2.errors.InsufficientPrivilege: permission denied to create database
```

### Причина
Django создаёт отдельную тестовую БД (test_todo_db), но пользователю не хватало прав.

### Решение

**Вариант 1: Дать права CREATEDB (production-like):**
```sql
ALTER USER todo_user CREATEDB;
```

**Вариант 2: SQLite для тестов (быстрее):**
```python
# settings_test.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

**Мы выбрали Вариант 1** - чтобы тесты работали с реальной PostgreSQL и проверяли ULID и другие фичи.

---

## 5. Celery Event Loop Conflicts

### Проблема
При попытке вызвать async функции в Celery tasks:
```python
@shared_task
def send_notification(task_id):
    # ❌ RuntimeError: no running event loop
    result = await api_client.send_message(...)
```

### Причина
Celery worker работает в sync режиме, но API client async.

### Решение

**Вариант 1: Использовать requests вместо aiohttp:**
```python
import requests

@shared_task
def send_notification(task_id):
    response = requests.post(url, json=payload)  # ✅ Работает
```

**Вариант 2: Запускать async код через asyncio.run():**
```python
import asyncio

@shared_task
def send_notification(task_id):
    asyncio.run(async_send_notification(task_id))  # ✅ Работает

async def async_send_notification(task_id):
    await api_client.send_message(...)
```

**Мы выбрали Вариант 1** для простоты и стабильности.

---

## 6. Telegram Bot API 400 Bad Request

### Проблема
При отправке уведомлений через Celery:
```
400 Client Error: Bad Request for url: https://api.telegram.org/bot.../sendMessage
```

### Причины
1. **Фейковый telegram_id** - тестовый пользователь с ID=123456789
2. **Пользователь не написал /start** - бот не может отправить первое сообщение
3. **Невалидный формат сообщения** - проблемы с HTML разметкой

### Решение

**1. Валидация telegram_id:**
```python
if not user_telegram_id or user_telegram_id <= 0:
    logger.warning(f"Invalid telegram_id: {user_telegram_id}")
    return {"status": "error", "message": "Invalid telegram_id"}
```

**2. Обработка ошибок без retry:**
```python
except requests.HTTPError as e:
    if e.response.status_code in [400, 403, 404]:
        # Пользователь не начал чат - не ретраим
        logger.warning(f"User {user_id} hasn't started chat with bot")
        return {"status": "skipped"}
    # Для других ошибок - retry
    raise self.retry(exc=e, countdown=60)
```

**3. Тестирование с реальным telegram_id:**
```python
# Узнать свой ID: @userinfobot в Telegram
user = User.objects.create_user(
    username='realuser',
    telegram_id=YOUR_REAL_TELEGRAM_ID,
    telegram_username='your_username'
)
```

---

## 7. Docker Networking между сервисами

### Проблема
Бот не мог подключиться к Django API:
```python
# ❌ Не работает в Docker
API_BASE_URL = 'http://localhost:8000/api'
```

### Причина
В Docker контейнеры изолированы. `localhost` указывает на сам контейнер бота, а не на хост или другой контейнер.

### Решение

**Использовать имя сервиса из docker compose:**
```yaml
# docker compose.yml
services:
  backend:
    container_name: todo_backend
    ...
  
  bot:
    environment:
      API_BASE_URL: http://backend:8000/api  # ✅ Имя сервиса
```

**Docker создаёт DNS для сервисов:**
- `backend` резолвится в IP контейнера Django
- Все контейнеры в одной сети (`todo_network`)

---

## 8. Aiogram FSM State Persistence

### Проблема
При перезапуске бота пользователь терял состояние FSM (в процессе создания задачи).

### Причина
По умолчанию FSM хранит состояния в памяти Python процесса.

### Решение

**Вариант 1: MemoryStorage (текущий, для простоты):**
```python
# По умолчанию в Aiogram 3.x
dp = Dispatcher()  # Использует MemoryStorage
```

**Вариант 2: Redis storage (для production):**
```python
from aiogram.fsm.storage.redis import RedisStorage

storage = RedisStorage.from_url('redis://redis:6379/1')
dp = Dispatcher(storage=storage)
```

**Мы оставили MemoryStorage** - для тестового задания достаточно, состояния не критичны.

---

## 9. API Response Pagination

### Проблема
DRF возвращает paginated response:
```json
{
  "count": 42,
  "next": "...",
  "previous": "...",
  "results": [...]
}
```

Но бот ожидал просто массив задач.

### Решение

**Хелпер для обработки обоих форматов:**
```python
def extract_results(response_data):
    """Работает с paginated и non-paginated ответами"""
    if isinstance(response_data, dict) and 'results' in response_data:
        return response_data['results']
    return response_data if isinstance(response_data, list) else []
```

**В API client:**
```python
async def get_tasks(self, token: str) -> List[Dict]:
    response = await self._request('GET', '/tasks/', token=token)
    
    # Handle pagination
    if 'results' in response:
        return response['results']
    return response if isinstance(response, list) else []
```

---

## 10. Celery Task Serialization

### Проблема
При передаче сложных объектов в Celery task:
```python
# ❌ Не сериализуется
send_notification.delay(task_object)
```

### Решение

**Передавать только примитивы:**
```python
# ✅ Работает
send_task_notification.delay(
    task_id=str(task.id),  # Строка
    user_telegram_id=task.user.telegram_id  # Число
)
```

**В task восстанавливать объект:**
```python
@shared_task
def send_task_notification(task_id: str, user_telegram_id: int):
    task = Task.objects.get(id=task_id)
    # ... дальше работа с task
```

---

## 11. Docker Volume Permissions

### Проблема
При монтировании volumes в development:
```
Permission denied: '/app/media/...'
```

### Причина
Файлы создаются от имени пользователя в контейнере (UID 1000), но на хосте другой пользователь.

### Решение

**Создать пользователя с правильным UID в Dockerfile:**
```dockerfile
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser
```

**Или использовать user в docker compose:**
```yaml
services:
  backend:
    user: "${UID}:${GID}"  # Из .env файла
```

---

## 12. Testing with Authentication

### Проблема
Каждый тест требовал создания пользователя и токена.

### Решение

**Fixtures в conftest.py:**
```python
@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        telegram_id=123456789,
    )

@pytest.fixture
def user_token(user):
    token, _ = Token.objects.get_or_create(user=user)
    return token.key

@pytest.fixture
def authenticated_client(api_client, user_token):
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {user_token}')
    return api_client
```

**Использование:**
```python
def test_create_task(authenticated_client):
    response = authenticated_client.post('/api/tasks/', {...})
    assert response.status_code == 201
```

---

## Общие Lessons Learned

### 1. Timezone-aware datetime
**Всегда используй:**
- `timezone.now()` вместо `datetime.now()`
- Проверяй `is_aware()` перед операциями с datetime
- Тестируй с разными timezones

### 2. API Design
**Best practices:**
- Консистентные ответы (всегда пагинация или никогда)
- Детальные error messages с кодами
- Версионирование API (/api/v1/)

### 3. Testing
**Что помогло:**
- Fixtures для переиспользования
- Покрытие не только happy path, но и edge cases
- Тесты на уровне API, а не только unit tests

### 4. Docker
**Уроки:**
- Multi-stage builds для меньшего размера образов
- Health checks критичны для зависимостей
- .dockerignore экономит время сборки

### 5. Async Programming
**Важно:**
- Не смешивать sync и async код без понимания
- Event loop - один на процесс
- Используй правильные библиотеки (aiohttp vs requests)

### 6. Celery
**Best practices:**
- Идемпотентные tasks (можно запускать несколько раз)
- Retry механизм с exponential backoff
- Dead letter queue для failed tasks
- Мониторинг очередей

### 7. Security
**Нельзя забывать:**
- Никогда не коммитить токены в git
- Валидировать все входные данные
- Rate limiting для API
- HTTPS в production

---

## Метрики проекта

**Время разработки:** ~8-10 часов
**Строк кода:**
- Backend: ~2000 строк
- Bot: ~800 строк
- Tests: ~500 строк
- Config: ~300 строк

**Покрытие тестами:** 84%

**Docker образы:**
- backend: ~180 MB
- bot: ~150 MB
- postgres: ~150 MB
- redis: ~30 MB

**Итого:** ~510 MB все сервисы

---

## Что бы сделал по-другому

### 1. Architecture
- ✅ **Хорошо:** Separation of concerns (bot → API → DB)
- 🔄 **Улучшил бы:** Использовать Redis для token storage вместо in-memory

### 2. Testing
- ✅ **Хорошо:** 84% coverage, integration tests
- 🔄 **Улучшил бы:** E2E тесты с реальным Telegram API (через mock bot)

### 3. Error Handling
- ✅ **Хорошо:** Retry механизм, логирование
- 🔄 **Улучшил бы:** Structured logging (JSON format), Sentry integration

### 4. Bot UX
- ✅ **Хорошо:** FSM для создания задач, inline кнопки
- 🔄 **Улучшил бы:** Aiogram-dialog для более сложных диалогов, i18n

### 5. Production Readiness
- ✅ **Хорошо:** Docker, healthchecks, environment variables
- 🔄 **Нужно добавить:** 
  - Nginx reverse proxy
  - SSL certificates
  - Prometheus + Grafana
  - Backup strategy
  - CI/CD pipeline

---

## Заключение

Проект демонстрирует:
- ✅ Понимание Django ecosystem (ORM, DRF, Celery, Admin)
- ✅ Опыт с async Python (Aiogram, aiohttp)
- ✅ Умение работать с Docker и микросервисами
- ✅ Навыки тестирования и отладки
- ✅ Понимание production best practices

**Основная сложность:** Интеграция множества технологий в единую систему, где каждая часть зависит от другой. Решалось через правильную архитектуру и четкое разделение ответственности между компонентами.