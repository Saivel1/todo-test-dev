from celery import shared_task
from django.utils import timezone
from django.conf import settings
import requests
import logging

from .models import Task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_task_notification(self, task_id: str, user_telegram_id: int):
    """
    Отправить уведомление пользователю в Telegram
    
    Args:
        task_id: ID задачи
        user_telegram_id: Telegram ID пользователя
    """
    try:
        task = Task.objects.get(id=task_id)
        
        # Формируем сообщение
        if task.is_overdue:
            emoji = "⚠️"
            status_text = "ПРОСРОЧЕНА"
        else:
            emoji = "⏰"
            status_text = "скоро дедлайн"
        
        message = (
            f"{emoji} <b>{status_text}</b>\n\n"
            f"📝 Задача: <b>{task.title}</b>\n"
        )
        
        if task.description:
            message += f"📄 Описание: {task.description}\n"
        
        if task.deadline:
            # Конвертируем в timezone пользователя (America/Adak из settings)
            local_deadline = timezone.localtime(task.deadline)
            message += f"⏱ Дедлайн: {local_deadline.strftime('%d.%m.%Y %H:%M')}\n"
        
        if task.categories.exists():
            cats = ", ".join([c.name for c in task.categories.all()])
            message += f"🏷 Категории: {cats}\n"
        
        # Отправляем через Telegram Bot API
        bot_token = settings.TELEGRAM_BOT_TOKEN
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": user_telegram_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        # Отмечаем что уведомление отправлено
        task.notification_sent = True
        task.save(update_fields=['notification_sent'])
        
        logger.info(f"✅ Notification sent for task {task_id} to user {user_telegram_id}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "user_id": user_telegram_id
        }
        
    except Task.DoesNotExist:
        logger.error(f"❌ Task {task_id} not found")
        return {"status": "error", "message": "Task not found"}
    
    except requests.RequestException as e:
        logger.error(f"❌ Failed to send notification: {e}")
        # Retry через 1 минуту
        raise self.retry(exc=e, countdown=60)
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise


@shared_task
def check_task_deadlines():
    """
    Периодическая задача для проверки дедлайнов задач.
    Запускается каждые 5 минут через Celery Beat.
    """
    now = timezone.now()
    
    # Находим задачи которым нужно отправить уведомление
    tasks_to_notify = Task.objects.filter(
        notification_sent=False,
        deadline__isnull=False,
        status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS]
    ).select_related('user')
    
    notified_count = 0
    
    for task in tasks_to_notify:
        if task.should_send_notification():
            # Отправляем уведомление асинхронно
            send_task_notification.delay(
                task_id=str(task.id),
                user_telegram_id=task.user.telegram_id
            ) #type: ignore
            notified_count += 1
    
    logger.info(f"🔔 Checked deadlines, sent {notified_count} notifications")
    
    return {
        "checked_at": now.isoformat(),
        "notifications_sent": notified_count
    }


@shared_task
def cleanup_old_completed_tasks(days: int = 30):
    """
    Очистка старых выполненных задач.
    Опционально: можно запускать раз в день через beat.
    
    Args:
        days: Удалять задачи старше N дней
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    deleted_count, _ = Task.objects.filter(
        status=Task.Status.COMPLETED,
        updated_at__lt=cutoff_date
    ).delete()
    
    logger.info(f"🗑 Cleaned up {deleted_count} old completed tasks")
    
    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat()
    }