from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Расширенная модель пользователя с telegram_id
    """
    
    telegram_id = models.BigIntegerField(
        'Telegram ID',
        unique=True,
        null=True,
        blank=True,
        help_text='ID пользователя в Telegram'
    )
    
    telegram_username = models.CharField(
        'Telegram Username',
        max_length=255,
        blank=True,
        null=True
    )
    
    # Для API токена бота
    api_token = models.CharField(
        'API Token',
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text='Токен для аутентификации бота'
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        if self.telegram_username:
            return f"@{self.telegram_username} ({self.telegram_id})"
        return f"User {self.telegram_id or self.username}"