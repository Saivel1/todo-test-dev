from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from logger_setup import logger

from .models import Task, Category
from .serializers import (
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    CategorySerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet для категорий.
    """
    
    queryset = Category.objects.annotate(
        tasks_count=Count('tasks')
    ).all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'tasks_count']
    ordering = ['name']


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet для задач.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'deadline', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Возвращаем только задачи текущего пользователя"""
        res = Task.objects.filter(
            user=self.request.user
        ).select_related('user').prefetch_related('categories')

        print("Вошли в get_queryset")
        print(res)

        logger.debug("Вошли в get_queryset")
        logger.debug(res)

        return res
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'create':
            return TaskCreateSerializer
        return TaskDetailSerializer
    
    def perform_create(self, serializer):
        """При создании автоматически назначаем текущего пользователя"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Переопределяем create чтобы возвращать детальный serializer
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Получаем созданную задачу и возвращаем детальный serializer
        task = serializer.instance
        detail_serializer = TaskDetailSerializer(task)
        headers = self.get_success_headers(detail_serializer.data)
        
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=False, methods=['get'])
    def my(self, request):
        """
        GET /api/tasks/my/
        Альтернативный эндпоинт для получения задач пользователя
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Фильтрация по статусу
        status_filter: str = request.query_params.get('status')
        if status_filter.startswith("-"):
            queryset = queryset.exclude(status=status_filter)

        elif status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Фильтрация по категории
        category_id = request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(categories__id=category_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        GET /api/tasks/overdue/
        Получить просроченные задачи
        """
        now = timezone.now()
        queryset = self.get_queryset().filter(
            deadline__lt=now,
            status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS]
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TaskListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        POST /api/tasks/{id}/complete/
        Отметить задачу как выполненную
        """
        task = self.get_object()
        task.status = Task.Status.COMPLETED
        task.save()
        
        serializer = TaskDetailSerializer(task)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/tasks/{id}/cancel/
        Отменить задачу
        """
        task = self.get_object()
        task.status = Task.Status.CANCELLED
        task.save()
        
        serializer = TaskDetailSerializer(task)
        return Response(serializer.data)