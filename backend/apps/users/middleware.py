import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware для логирования всех API запросов.
    Полезно для отладки бота.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Логируем запрос
        if request.path.startswith('/api/'):
            logger.info(
                f"📥 {request.method} {request.path} "
                f"from {request.META.get('REMOTE_ADDR')} "
                f"auth: {request.user.is_authenticated}"
            )
        
        response = self.get_response(request)
        
        # Логируем ответ
        if request.path.startswith('/api/'):
            logger.info(
                f"📤 {request.method} {request.path} "
                f"→ {response.status_code}"
            )
        
        return response