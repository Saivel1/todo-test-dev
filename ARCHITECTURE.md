# Архитектура проекта

## Общая схема
```
┌──────────────────────────────────────────────────────────┐
│                     Telegram User                         │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│                   Aiogram Bot (Python)                    │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │  Handlers  │  │ Middlewares │  │   API Client     │  │
│  │  (FSM)     │  │   (Auth)    │  │  (aiohttp)       │  │
│  └────────────┘  └─────────────┘  └──────────────────┘  │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP REST API
                        ▼
┌──────────────────────────────────────────────────────────┐
│              Django REST Framework Backend                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   Views     │  │ Serializers  │  │    Models      │  │
│  │  (API)      │  │  (DRF)       │  │  (ULID PK)     │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└─────┬─────────────────────┬─────────────────┬───────────┘
      │                     │                 │
      ▼                     ▼                 ▼
┌───────────┐        ┌──────────┐      ┌──────────────┐
│PostgreSQL │        │  Redis   │      │   Celery     │
│  (Data)   │        │ (Queue)  │      │(Background)  │
└───────────┘        └──────────┘      └──────────────┘
```

## Компоненты

### 1. Telegram Bot Layer
- **Aiogram 3.x**: Асинхронный фреймворк для Telegram Bot API
- **FSM**: Конечный автомат для многошаговых диалогов
- **Middleware**: Автоматическая аутентификация пользователей
- **API Client**: HTTP клиент для взаимодействия с backend

### 2. Backend Layer
- **Django**: Web framework
- **DRF**: REST API с токен-аутентификацией
- **Custom Models**: ULID primary keys, timezone-aware datetime
- **Admin Panel**: Управление через Django admin

### 3. Background Tasks Layer
- **Celery Worker**: Асинхронная обработка задач
- **Celery Beat**: Периодические задачи (cron)
- **Redis**: Брокер сообщений

### 4. Data Layer
- **PostgreSQL**: Основное хранилище данных
- **Redis**: Кеш и очередь задач

## Data Flow

### Создание задачи через бота
```
User → /create
  ↓
Bot: FSM State Machine (4 шага)
  ↓
Bot: POST /api/tasks/ (with token)
  ↓
Django: TaskCreateSerializer validation
  ↓
Django: Task.objects.create() с ULID
  ↓
PostgreSQL: INSERT INTO tasks
  ↓
Django: TaskDetailSerializer response
  ↓
Bot: Показать созданную задачу
  ↓
User: Видит подтверждение
```

### Уведомление о дедлайне
```
Celery Beat (каждые 5 минут)
  ↓
Task: check_task_deadlines
  ↓
Django ORM: Query задачи с deadline < now + 1h
  ↓
Для каждой задачи:
  ↓
  Task: send_task_notification.delay()
  ↓
  Celery Worker: Получает из Redis queue
  ↓
  Telegram API: sendMessage
  ↓
  Django: task.notification_sent = True
```

## Security

### Authentication Flow

1. User нажимает /start в боте
2. Bot извлекает telegram_id, username
3. Bot → POST /api/auth/telegram/ {telegram_id, ...}
4. Django: User.objects.get_or_create()
5. Django: Token.objects.get_or_create()
6. Django → {token, user, created}
7. Bot сохраняет token in-memory
8. Все последующие запросы: Header "Authorization: Token XXX"

### Token Storage

**Текущая реализация**: In-memory словарь
```python
{user_id: token}
```

**Production улучшение**: Redis с TTL
```python
redis.setex(f"bot:token:{user_id}", 86400, token)
```

## Scalability Considerations

### Горизонтальное масштабирование

**Backend:**
- Load balancer перед Django instances
- Shared PostgreSQL
- Shared Redis

**Bot:**
- Webhook режим вместо polling
- Load balancer перед bot instances
- Persistent token storage (Redis/DB)

**Celery:**
- Добавить больше workers
- Разные queues для разных типов задач

### Vertical Scaling

- PostgreSQL connection pooling
- Redis clustering
- Celery concurrency settings

## Design Patterns

### 1. Repository Pattern
API Client абстрагирует HTTP вызовы:
```python
task = await api_client.create_task(token, title="...")
```

### 2. Middleware Pattern
Автоматическая регистрация пользователей:
```python
class AuthMiddleware:
    async def __call__(self, handler, event, data):
        token = await register_or_get_token(user_id)
        data['token'] = token
        return await handler(event, data)
```

### 3. State Pattern (FSM)
Многошаговые диалоги:
```python
class CreateTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    ...
```

### 4. Strategy Pattern
Разные сериализаторы для разных действий:
```python
def get_serializer_class(self):
    if self.action == 'list':
        return TaskListSerializer
    elif self.action == 'create':
        return TaskCreateSerializer
    return TaskDetailSerializer
```

## Performance Optimization

### Database
- Индексы на часто запрашиваемые поля
- `select_related()` и `prefetch_related()` для joins
- Connection pooling

### API
- Пагинация результатов
- Lazy loading категорий
- Кеширование списка категорий в Redis

### Bot
- Batch операции где возможно
- Async/await для конкурентных запросов
- Rate limiting для Telegram API

## Monitoring & Logging

### Logs
- Django: структурированные логи в файл + console
- Celery: отдельные логи для worker и beat
- Bot: логи команд и ошибок API

### Metrics (будущее)
- Prometheus + Grafana
- Метрики: requests/sec, response time, error rate
- Celery: queue length, task duration

### Alerts
- Dead letter queue для failed tasks
- Email/Telegram alerts при критических ошибках