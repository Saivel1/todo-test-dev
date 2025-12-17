import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str
    api_base_url: str
    
    @classmethod
    def from_env(cls):
        return cls(
            token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            api_base_url=os.getenv('API_BASE_URL', 'http://localhost:8000/api')
        )


# Глобальный конфиг
config = BotConfig.from_env()