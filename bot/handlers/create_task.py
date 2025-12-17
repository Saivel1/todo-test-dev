from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.api_client import APIClient, APIError
from datetime import datetime, timedelta

router = Router()


class CreateTaskStates(StatesGroup):
    """Состояния для создания задачи"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()
    waiting_for_category = State()


@router.message(Command('create'))
@router.message(F.text == "➕ Создать задачу")
async def cmd_create_task(message: Message, state: FSMContext):
    """Начать создание задачи"""
    await state.set_state(CreateTaskStates.waiting_for_title)
    await message.answer(
        "📝 <b>Создание новой задачи</b>\n\n"
        "Шаг 1/4: Введите название задачи:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отменить")]],
            resize_keyboard=True
        )
    )


@router.message(CreateTaskStates.waiting_for_title, F.text == "❌ Отменить")
@router.message(CreateTaskStates.waiting_for_description, F.text == "❌ Отменить")
@router.message(CreateTaskStates.waiting_for_deadline, F.text == "❌ Отменить")
@router.message(CreateTaskStates.waiting_for_category, F.text == "❌ Отменить")
async def cancel_creation(message: Message, state: FSMContext):
    """Отменить создание задачи"""
    await state.clear()
    
    # Возвращаем основное меню
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Создать задачу")],
            [KeyboardButton(text="🏷 Категории"), KeyboardButton(text="⚠️ Просроченные")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "❌ Создание задачи отменено.",
        reply_markup=kb
    )


@router.message(CreateTaskStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    title = message.text.strip()
    
    if len(title) < 3:
        await message.answer("⚠️ Название должно быть не менее 3 символов. Попробуйте ещё раз:")
        return
    
    if len(title) > 255:
        await message.answer("⚠️ Название слишком длинное (макс. 255 символов). Попробуйте ещё раз:")
        return
    
    await state.update_data(title=title)
    await state.set_state(CreateTaskStates.waiting_for_description)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "✅ Название сохранено!\n\n"
        "Шаг 2/4: Введите описание задачи (или нажмите 'Пропустить'):",
        reply_markup=kb
    )


@router.message(CreateTaskStates.waiting_for_description, F.text == "⏭ Пропустить")
async def skip_description(message: Message, state: FSMContext):
    """Пропустить описание"""
    await state.update_data(description='')
    await ask_for_deadline(message, state)


@router.message(CreateTaskStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания задачи"""
    description = message.text.strip()
    
    if len(description) > 1000:
        await message.answer("⚠️ Описание слишком длинное (макс. 1000 символов). Попробуйте ещё раз:")
        return
    
    await state.update_data(description=description)
    await ask_for_deadline(message, state)


async def ask_for_deadline(message: Message, state: FSMContext):
    """Запросить дедлайн"""
    await state.set_state(CreateTaskStates.waiting_for_deadline)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")],
            [KeyboardButton(text="Через неделю"), KeyboardButton(text="Через месяц")],
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Шаг 3/4: Выберите или введите дедлайн:\n\n"
        "Формат: ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 25.12.2024 или 25.12.2024 14:30",
        reply_markup=kb
    )


@router.message(CreateTaskStates.waiting_for_deadline, F.text == "⏭ Пропустить")
async def skip_deadline(message: Message, state: FSMContext, token: str, api_client: APIClient):
    """Пропустить дедлайн"""
    await state.update_data(deadline=None)
    await ask_for_category(message, state, token, api_client)


@router.message(CreateTaskStates.waiting_for_deadline)
async def process_deadline(message: Message, state: FSMContext, token: str, api_client: APIClient):
    """Обработка дедлайна"""
    text = message.text.strip()
    
    # Быстрые кнопки
    if text == "Сегодня":
        deadline = datetime.now().replace(hour=23, minute=59, second=59)
    elif text == "Завтра":
        deadline = (datetime.now() + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    elif text == "Через неделю":
        deadline = (datetime.now() + timedelta(days=7)).replace(hour=23, minute=59, second=59)
    elif text == "Через месяц":
        deadline = (datetime.now() + timedelta(days=30)).replace(hour=23, minute=59, second=59)
    else:
        # Парсинг пользовательского ввода
        try:
            # Пробуем формат ДД.ММ.ГГГГ ЧЧ:ММ
            if ' ' in text:
                deadline = datetime.strptime(text, "%d.%m.%Y %H:%M")
            else:
                # Формат ДД.ММ.ГГГГ (время - конец дня)
                deadline = datetime.strptime(text, "%d.%m.%Y").replace(hour=23, minute=59)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат даты!\n\n"
                "Используйте: ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.12.2024 или 25.12.2024 14:30"
            )
            return
        
        # Проверка что дата в будущем
        if deadline < datetime.now():
            await message.answer("⚠️ Дедлайн не может быть в прошлом! Введите корректную дату:")
            return
    
    # Конвертируем в ISO формат для API
    deadline_iso = deadline.isoformat()
    await state.update_data(deadline=deadline_iso)
    await ask_for_category(message, state, token, api_client)


async def ask_for_category(message: Message, state: FSMContext, token: str, api_client: APIClient):
    """Запросить категорию"""
    await state.set_state(CreateTaskStates.waiting_for_category)
    
    try:
        categories = await api_client.get_categories(token)
        
        if categories:
            kb = InlineKeyboardBuilder()
            for cat in categories[:10]:  # Первые 10 категорий
                kb.button(text=cat['name'], callback_data=f"selectcat:{cat['id']}")
            kb.button(text="⏭ Без категории", callback_data="selectcat:none")
            kb.button(text="❌ Отменить", callback_data="selectcat:cancel")
            kb.adjust(2)
            
            await message.answer(
                "✅ Дедлайн установлен!\n\n"
                "Шаг 4/4: Выберите категорию:",
                reply_markup=kb.as_markup()
            )
        else:
            # Нет категорий
            await finalize_task_creation(message, state, token, api_client, category_ids=None)
    
    except APIError as e:
        await message.answer(f"⚠️ Не удалось загрузить категории: {e.detail}")
        await finalize_task_creation(message, state, token, api_client, category_ids=None)


@router.callback_query(F.data.startswith("selectcat:"), StateFilter(CreateTaskStates.waiting_for_category))
async def process_category_selection(
    callback: CallbackQuery,
    state: FSMContext,
    token: str,
    api_client: APIClient
):
    """Обработка выбора категории"""
    action = callback.data.split(':')[1]
    
    if action == "cancel":
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("❌ Создание задачи отменено.")
        await callback.answer()
        return
    
    category_ids = None if action == "none" else [action]
    await callback.message.delete()
    await finalize_task_creation(callback.message, state, token, api_client, category_ids)
    await callback.answer()


async def finalize_task_creation(
    message: Message,
    state: FSMContext,
    token: str,
    api_client: APIClient,
    category_ids: list = None
):
    """Финализировать создание задачи"""
    data = await state.get_data()
    
    try:
        task = await api_client.create_task(
            token=token,
            title=data['title'],
            description=data.get('description', ''),
            deadline=data.get('deadline'),
            category_ids=category_ids
        )
        
        # Возвращаем основное меню
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="➕ Создать задачу")],
                [KeyboardButton(text="🏷 Категории"), KeyboardButton(text="⚠️ Просроченные")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            f"✅ <b>Задача создана!</b>\n\n"
            f"📝 {task['title']}\n"
            f"🆔 ID: <code>{task['id']}</code>",
            reply_markup=kb
        )
        
        await state.clear()
    
    except APIError as e:
        await message.answer(
            f"❌ Ошибка при создании задачи: {e.detail}\n\n"
            f"Попробуйте ещё раз: /create"
        )
        await state.clear()