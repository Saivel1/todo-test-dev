import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('todo_bot')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Добавь эту строку чтобы убрать warning
app.conf.broker_connection_retry_on_startup = True

# Расписание периодических задач
app.conf.beat_schedule = {
    'check-task-deadlines': {
        'task': 'apps.tasks.tasks.check_task_deadlines',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup-old-tasks': {
        'task': 'apps.tasks.tasks.cleanup_old_completed_tasks',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 30}
    },
}

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Adak',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')