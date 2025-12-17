from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Task, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_badge', 'tasks_count', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at']
    
    def color_badge(self, obj):
        return mark_safe(
            f'<span style="background-color: {obj.color}; padding: 5px 10px; '
            f'border-radius: 3px; color: white;">{obj.color}</span>'
        )
    color_badge.short_description = 'Цвет'
    
    def tasks_count(self, obj):
        return obj.tasks.count()
    tasks_count.short_description = 'Кол-во задач'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'status', 'deadline',
        'overdue_status', 'notification_sent', 'created_at'
    ]
    list_filter = ['status', 'notification_sent', 'created_at', 'deadline']
    search_fields = ['title', 'description', 'user__username', 'user__telegram_username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'overdue_display']
    filter_horizontal = ['categories']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'user', 'title', 'description', 'status')
        }),
        ('Категории и сроки', {
            'fields': ('categories', 'deadline', 'overdue_display')
        }),
        ('Уведомления', {
            'fields': ('notification_sent',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def overdue_status(self, obj):
        """Для list_display - короткий статус"""
        if obj.is_overdue:
            return mark_safe('<span style="color: red; font-weight: bold;">⚠️ Просрочена</span>')
        return mark_safe('<span style="color: green;">✓ В срок</span>')
    overdue_status.short_description = 'Статус срока'
    
    def overdue_display(self, obj):
        """Для readonly_fields - детальная информация"""
        if not obj.deadline:
            return mark_safe('<span style="color: gray;">Нет дедлайна</span>')
        
        if obj.is_overdue:
            return mark_safe(
                '<span style="color: red; font-weight: bold; font-size: 14px;">'
                '⚠️ ПРОСРОЧЕНА</span>'
            )
        return mark_safe(
            '<span style="color: green; font-weight: bold; font-size: 14px;">'
            '✓ В СРОК</span>'
        )
    overdue_display.short_description = 'Статус просрочки'