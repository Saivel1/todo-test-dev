from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import User


class TelegramAuthSerializer(serializers.Serializer):
    """
    Сериализатор для регистрации/авторизации через Telegram
    """
    telegram_id = serializers.IntegerField(required=True)
    telegram_username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_telegram_id(self, value):
        """Проверка что telegram_id валидный"""
        if value <= 0:
            raise serializers.ValidationError("Invalid telegram_id")
        return value
    
    def create_or_update_user(self):
        """
        Создать или обновить пользователя по Telegram ID.
        Возвращает (user, token, created)
        """
        telegram_id = self.validated_data['telegram_id'] #type: ignore
        telegram_username = self.validated_data.get('telegram_username') #type: ignore
        first_name = self.validated_data.get('first_name', '') #type: ignore
        last_name = self.validated_data.get('last_name', '') #type: ignore
        
        # Ищем существующего пользователя
        user, created = User.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'username': f'tg_{telegram_id}',
                'telegram_username': telegram_username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        
        # Обновляем данные если пользователь уже существует
        if not created:
            updated = False
            if telegram_username and user.telegram_username != telegram_username:
                user.telegram_username = telegram_username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            
            if updated:
                user.save()
        
        # Получаем или создаём токен
        token, _ = Token.objects.get_or_create(user=user)
        
        return user, token, created


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для информации о пользователе"""
    
    tasks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'telegram_id', 'telegram_username',
            'first_name', 'last_name', 'date_joined', 'tasks_count'
        ]
        read_only_fields = ['id', 'username', 'date_joined']
    
    def get_tasks_count(self, obj):
        return obj.tasks.count()