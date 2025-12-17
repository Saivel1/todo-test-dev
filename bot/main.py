import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from services.api_client import APIClient
from middlewares.auth import AuthMiddleware
from handlers import start, tasks, create_task, categories

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    
    # Инициализация API клиента
    api_client = APIClient(config.api_base_url)
    await api_client.start()
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация middleware
    dp.message.middleware(AuthMiddleware(api_client))
    dp.callback_query.middleware(AuthMiddleware(api_client))
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(create_task.router)
    dp.include_router(categories.router)
    
    logger.info("🤖 Bot starting...")
    logger.info(f"📡 API URL: {config.api_base_url}")
    
    try:
        # Запуск polling
        await dp.start_polling(bot)
    finally:
        await api_client.close()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")