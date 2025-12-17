from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.api_client import APIClient, APIError

router = Router()


class CreateCategoryStates(StatesGroup):
    """Состояния для создания категории"""
    waiting_for_name = State()


@router.message(Command('categories'))
@router.message(F.text == "🏷 Категории")
async def cmd_categories(message: Message, token: str, api_client: APIClient):
    """Показать список категорий"""
    try:
        categories = await api_client.get_categories(token)
        
        if not categories:
            kb = InlineKeyboardBuilder()
            kb.button(text="➕ Создать категорию", callback_data="create_category")
            
            await message.answer(
                "🏷 У вас пока нет категорий.\n\n"
                "Категории помогают организовать задачи по темам.",
                reply_markup=kb.as_markup()
            )
            return
        
        text = f"🏷 <b>Ваши категории ({len(categories)}):</b>\n\n"
        
        kb = InlineKeyboardBuilder()
        for cat in categories:
            tasks_count = cat.get('tasks_count', 0)
            text += f"• {cat['name']} ({tasks_count} задач)\n"
            kb.button(
                text=f"{cat['name']} ({tasks_count})",
                callback_data=f"catfilter:{cat['id']}"
            )
        
        kb.button(text="➕ Создать категорию", callback_data="create_category")
        kb.adjust(2)
        
        await message.answer(text, reply_markup=kb.as_markup())
    
    except APIError as e:
        await message.answer(f"❌ Ошибка: {e.detail}")


@router.callback_query(F.data == "create_category")
async def callback_create_category(callback: CallbackQuery, state: FSMContext):
    """Начать создание категории"""
    await state.set_state(CreateCategoryStates.waiting_for_name)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True
    )
    
    await callback.message.answer(
        "➕ <b>Создание новой категории</b>\n\n"
        "Введите название категории:",
        reply_markup=kb
    )
    await callback.answer()


@router.message(CreateCategoryStates.waiting_for_name, F.text == "❌ Отменить")
async def cancel_category_creation(message: Message, state: FSMContext):
    """Отменить создание категории"""
    await state.clear()
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Создать задачу")],
            [KeyboardButton(text="🏷 Категории"), KeyboardButton(text="⚠️ Просроченные")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("❌ Создание категории отменено.", reply_markup=kb)


@router.message(CreateCategoryStates.waiting_for_name)
async def process_category_name(
    message: Message,
    state: FSMContext,
    token: str,
    api_client: APIClient
):
    """Обработка названия категории"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("⚠️ Название должно быть не менее 2 символов. Попробуйте ещё раз:")
        return
    
    if len(name) > 100:
        await message.answer("⚠️ Название слишком длинное (макс. 100 символов). Попробуйте ещё раз:")
        return
    
    try:
        category = await api_client.create_category(token, name)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Создать задачу")],
                [KeyboardButton(text="🏷 Категории"), KeyboardButton(text="⚠️ Просроченные")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            f"✅ Категория создана!\n\n"
            f"🏷 {category['name']}\n"
            f"🆔 ID: <code>{category['id']}</code>",
            reply_markup=kb
        )
        
        await state.clear()
    
    except APIError as e:
        if e.status_code == 400:
            await message.answer(
                "⚠️ Категория с таким названием уже существует.\n"
                "Попробуйте другое название:"
            )
        else:
            await message.answer(f"❌ Ошибка при создании категории: {e.detail}")
            await state.clear()


@router.callback_query(F.data.startswith("catfilter:"))
async def callback_filter_by_category(
    callback: CallbackQuery,
    token: str,
    api_client: APIClient
):
    """Показать задачи по категории"""
    category_id = callback.data.split(':')[1]
    
    try:
        tasks = await api_client.get_tasks(token, category_id=category_id)
        
        if not tasks:
            await callback.answer("В этой категории пока нет задач", show_alert=True)
            return
        
        # Получаем имя категории
        categories = await api_client.get_categories(token)
        category_name = next((c['name'] for c in categories if c['id'] == category_id), "Категория")
        
        await callback.message.answer(f"🏷 <b>Задачи в категории '{category_name}':</b>")
        
        from bot.handlers.tasks import format_task
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        for task in tasks[:10]:
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Выполнить", callback_data=f"complete:{task['id']}")
            kb.button(text="🗑 Удалить", callback_data=f"delete:{task['id']}")
            kb.adjust(2)
            
            await callback.message.answer(
                format_task(task),
                reply_markup=kb.as_markup()
            )
        
        await callback.answer()
    
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)