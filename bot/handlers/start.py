from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from services.api_client import APIClient

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message, token: str, api_client: APIClient):
    """Команда /start"""
    try:
        user_info = await api_client.get_current_user(token)
        
        kb = ReplyKeyboardBuilder()
        kb.button(text="📋 Мои задачи")
        kb.button(text="➕ Создать задачу")
        kb.button(text="🏷 Категории")
        kb.button(text="⚠️ Просроченные")
        kb.adjust(2)
        
        await message.answer(
            f"👋 Привет, {user_info.get('first_name', 'пользователь')}!\n\n"
            f"Это ToDo бот для управления задачами.\n\n"
            f"Используй кнопки меню или команды:\n"
            f"/tasks - список задач\n"
            f"/create - создать задачу\n"
            f"/categories - категории",
            reply_markup=kb.as_markup(resize_keyboard=True)
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command('help'))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
📚 <b>Доступные команды:</b>

/start - Главное меню
/tasks - Список задач
/create - Создать задачу
/categories - Управление категориями
/overdue - Просроченные задачи

<b>Кнопки:</b>
📋 Мои задачи - показать все задачи
➕ Создать задачу - добавить новую
🏷 Категории - управление категориями
⚠️ Просроченные - показать просроченные
"""
    await message.answer(help_text)