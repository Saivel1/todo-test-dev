# Telegram Bot - Aiogram 3.x

## Технологии

- Aiogram 3.15.0
- Aiogram-dialog 2.2.0
- aiohttp 3.11.10

## Команды бота

- `/start` - Начало работы, главное меню
- `/help` - Справка по командам
- `/tasks` - Список всех задач
- `/create` - Создать новую задачу
- `/categories` - Управление категориями
- `/overdue` - Просроченные задачи

## Локальная разработка
```bash
# Установить зависимости
pip install -r requirements.txt

# Создать .env
cp .env.example .env
# Добавить TELEGRAM_BOT_TOKEN

# Запустить
python main.py
```

## Структура
```
bot/
├── handlers/          # Обработчики команд и callback
├── services/          # API client, token storage
├── middlewares/       # Автоматическая регистрация
├── config.py          # Конфигурация
└── main.py            # Точка входа
```

## FSM States

Создание задачи проходит через 4 шага:
1. Название задачи
2. Описание (опционально)
3. Дедлайн (опционально)
4. Категория (опционально)

## API Integration

Бот использует HTTP API для всех операций:
- Автоматическая регистрация при `/start`
- Token-based authentication
- Все данные хранятся на backend