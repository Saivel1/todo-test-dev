from rest_framework import serializers
from .models import Task, Category
from apps.users.models import User


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""
    
    tasks_count = serializers.IntegerField(read_only=True, required=False)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'color', 'created_at', 'tasks_count']
        read_only_fields = ['id', 'created_at']


class TaskListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка задач (минимальная информация)"""
    
    categories = CategorySerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'status', 'categories',
            'deadline', 'is_overdue', 'created_at'
        ]


class TaskDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о задаче"""
    
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    is_overdue = serializers.BooleanField(read_only=True)
    user_telegram_id = serializers.IntegerField(source='user.telegram_id', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status',
            'categories', 'category_ids',
            'deadline', 'is_overdue',
            'notification_sent',
            'created_at', 'updated_at',
            'user_telegram_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'notification_sent']
    
    def create(self, validated_data):
        category_ids = validated_data.pop('category_ids', [])
        task = Task.objects.create(**validated_data)
        
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids)
            task.categories.set(categories)
        
        return task
    
    def update(self, instance, validated_data):
        category_ids = validated_data.pop('category_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids)
            instance.categories.set(categories)
        
        return instance


class TaskCreateSerializer(serializers.ModelSerializer):
    """Упрощённый сериализатор для создания задачи через бота"""
    
    category_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'deadline', 'category_ids']
    
    def create(self, validated_data):
        category_ids = validated_data.pop('category_ids', [])
        
        # user придёт из view (request.user)
        task = Task.objects.create(**validated_data)
        
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids)
            task.categories.set(categories)
        
        return task