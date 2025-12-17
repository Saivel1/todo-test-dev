from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'telegram_id', 'telegram_username', 'is_staff', 'date_joined']
    search_fields = ['username', 'telegram_id', 'telegram_username', 'email']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Telegram', {
            'fields': ('telegram_id', 'telegram_username', 'api_token')
        }),
    ) #type: ignore
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Telegram', {
            'fields': ('telegram_id', 'telegram_username')
        }),
    )