from django.urls import path
from .views import TelegramAuthView, current_user, logout

urlpatterns = [
    path('telegram/', TelegramAuthView.as_view(), name='telegram-auth'),
    path('me/', current_user, name='current-user'),
    path('logout/', logout, name='logout'),
]