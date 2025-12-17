from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TelegramAuthSerializer, UserSerializer


class TelegramAuthView(APIView):
    """
    POST /api/auth/telegram/
    
    Регистрация или авторизация пользователя через Telegram.
    
    Request:
    {
        "telegram_id": 123456789,
        "telegram_username": "username",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    Response:
    {
        "token": "abc123...",
        "user": {
            "id": 1,
            "username": "tg_123456789",
            "telegram_id": 123456789,
            "telegram_username": "username",
            ...
        },
        "created": true
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        print(request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user, token, created = serializer.create_or_update_user() #type: ignore
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    GET /api/auth/me/
    
    Получить информацию о текущем пользователе.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    POST /api/auth/logout/
    
    Удалить токен текущего пользователя (logout).
    """
    # Удаляем токен
    request.user.auth_token.delete()
    return Response({
        'message': 'Successfully logged out'
    }, status=status.HTTP_200_OK)