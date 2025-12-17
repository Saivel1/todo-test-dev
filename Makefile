.PHONY: help build up down logs shell migrate test clean

help: ## Показать помощь
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	  docker compose build

up: ## Запустить все сервисы
	  docker compose up -d
	@echo "✅ Сервисы запущены!"
	@echo "📝 Backend: http://localhost:8000"
	@echo "🔧 Admin: http://localhost:8000/admin"

down: ## Остановить все сервисы
	  docker compose down

restart: ## Перезапустить сервисы
	  docker compose restart

logs: ## Показать логи всех сервисов
	  docker compose logs -f

logs-backend: ## Логи Django
	  docker compose logs -f backend

logs-celery: ## Логи Celery worker
	  docker compose logs -f celery_worker

logs-beat: ## Логи Celery beat
	  docker compose logs -f celery_beat

logs-bot: ## Логи бота
	  docker compose logs -f bot

shell: ## Django shell
	  docker compose exec backend python manage.py shell

bash: ## Bash в контейнере backend
	  docker compose exec backend bash

migrate: ## Применить миграции
	  docker compose exec backend python manage.py migrate

makemigrations: ## Создать миграции
	  docker compose exec backend python manage.py makemigrations

createsuperuser: ## Создать суперпользователя
	  docker compose exec backend python manage.py createsuperuser

test: ## Запустить тесты
	  docker compose exec backend pytest --cov=apps --cov-report=html

test-watch: ## Запустить тесты в watch режиме
	  docker compose exec backend pytest-watch

collectstatic: ## Собрать статику
	  docker compose exec backend python manage.py collectstatic --noinput

db-reset: ## Сбросить базу данных
	  docker compose down -v
	  docker compose up -d db
	sleep 5
	$(MAKE) migrate

init-db: ## Инициализация БД с тестовыми данными
	  docker compose exec backend python manage.py shell < scripts/init-db.sh

backup-db: ## Backup базы данных
	  docker compose exec db pg_dump -U todo_user todo_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore базы данных (make restore-db FILE=backup.sql)
	cat $(FILE) |   docker compose exec -T db psql -U todo_user todo_db

clean: ## Очистить всё (контейнеры, volumes, образы)
	  docker compose down -v --rmi all
	rm -rf backend/htmlcov backend/.pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

ps: ## Показать статус контейнеров
	  docker compose ps

init: build up migrate ## Полная инициализация проекта
	@echo "⏳ Waiting for services to be ready..."
	sleep 10
	  docker compose exec backend python manage.py shell < scripts/init-db.sh || true
	@echo "🎉 Проект готов к работе!"