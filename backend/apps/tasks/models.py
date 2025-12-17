from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone
from ulid import ULID


class ULIDField(models.CharField):
    """
    Custom field для ULID как Primary Key.
    ULID = Universally Unique Lexicographically Sortable Identifier
    
    Преимущества:
    - Лексикографически сортируемый (timestamp в начале)
    - 128-bit (как UUID) но более читаемый
    - Без коллизий в распределённой системе
    - Можно извлечь timestamp создания
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 26  # ULID всегда 26 символов
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


class Category(models.Model):
    """Категория (тег) для задач"""
    
    id = ULIDField()
    name = models.CharField('Название', max_length=100, unique=True)
    color = models.CharField('Цвет', max_length=7, default='#808080', 
                            help_text='HEX цвет для отображения в боте')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Task(models.Model):
    """Задача в ToDo списке"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        IN_PROGRESS = 'in_progress', 'В работе'
        COMPLETED = 'completed', 'Завершена'
        CANCELLED = 'cancelled', 'Отменена'
    
    id = ULIDField()
    
    # Связь с пользователем (telegram user_id хранится в связанной модели)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Пользователь'
    )
    
    title = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    categories = models.ManyToManyField(
        Category,
        related_name='tasks',
        verbose_name='Категории',
        blank=True
    )
    
    # Deadline с timezone-aware
    deadline = models.DateTimeField('Срок выполнения', null=True, blank=True)
    
    # Флаг для отслеживания отправки уведомления
    notification_sent = models.BooleanField('Уведомление отправлено', default=False)
    
    # Timestamps (важно для задания - показывать дату создания)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['deadline']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.user})"
    
    @property
    def is_overdue(self):
        """Проверка просрочена ли задача"""
        if not self.deadline:
            return False
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            return False
        return timezone.now() > self.deadline
    
    def should_send_notification(self):
        """
        Нужно ли отправлять уведомление.
        Логика: за час до deadline или при просрочке
        """
        if self.notification_sent or not self.deadline:
            return False
        
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            return False
        
        now = timezone.now()
        time_until_deadline = self.deadline - now
        
        # Уведомляем если осталось меньше часа или уже просрочено
        return time_until_deadline.total_seconds() <= 3600