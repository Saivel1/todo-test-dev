from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.api_client import APIClient, APIError

router = Router()


def format_task(task: dict) -> str:
    """Форматировать задачу для отображения"""
    status_emoji = {
        'pending': '⏳',
        'in_progress': '🔄',
        'completed': '✅',
        'cancelled': '❌'
    }
    
    status_names = {
        'pending': 'Ожидает',
        'in_progress': 'В работе',
        'completed': 'Завершена',
        'cancelled': 'Отменена'
    }
    
    emoji = status_emoji.get(task['status'], '❓')
    status_name = status_names.get(task['status'], task['status'])
    
    text = f"{emoji} <b>{task['title']}</b>\n"
    text += f"Статус: {status_name}\n"
    
    if task.get('description'):
        text += f"📝 {task['description']}\n"
    
    if task.get('categories'):
        cats = ', '.join([c['name'] for c in task['categories']])
        text += f"🏷 {cats}\n"
    
    if task.get('deadline'):
        text += f"⏰ До: {task['deadline'][:16].replace('T', ' ')}\n"
    
    if task.get('is_overdue'):
        text += "⚠️ <b>ПРОСРОЧЕНА</b>\n"
    
    text += f"\n📅 Создана: {task['created_at'][:10]}"
    
    return text


@router.message(Command('tasks'))
@router.message(F.text == "📋 Мои задачи")
async def cmd_tasks(message: Message, token: str, api_client: APIClient):
    """Показать все задачи"""
    try:
        tasks = await api_client.get_tasks(token=token, status="in_progress")
        
        if not tasks:
            await message.answer("📭 У вас пока нет задач.\n\nИспользуйте /create чтобы создать первую задачу.")
            return
        
        await message.answer(f"📋 <b>Ваши задачи ({len(tasks)}):</b>")
        
        for task in tasks[:10]:  # Показываем первые 10
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Выполнить", callback_data=f"complete:{task['id']}")
            kb.button(text="✏️ Детали", callback_data=f"details:{task['id']}")
            kb.button(text="🗑 Удалить", callback_data=f"delete:{task['id']}")
            kb.adjust(2)
            
            await message.answer(
                format_task(task),
                reply_markup=kb.as_markup()
            )
        
        if len(tasks) > 10:
            await message.answer(f"... и ещё {len(tasks) - 10} задач")
    
    except APIError as e:
        await message.answer(f"❌ Ошибка API: {e.detail}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("complete:"))
async def callback_complete_task(callback: CallbackQuery, token: str, api_client: APIClient):
    """Отметить задачу выполненной"""
    task_id = callback.data.split(':')[1]
    
    try:
        await api_client.complete_task(token, task_id)
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Задача выполнена!</b>"
        )
        await callback.answer("✅ Задача отмечена как выполненная")
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)


@router.callback_query(F.data.startswith("delete:"))
async def callback_delete_task(callback: CallbackQuery, token: str, api_client: APIClient):
    """Удалить задачу"""
    task_id = callback.data.split(':')[1]
    
    try:
        await api_client.delete_task(token, task_id)
        await callback.message.delete()
        await callback.answer("🗑 Задача удалена")
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)


@router.callback_query(F.data.startswith("details:"))
async def callback_task_details(callback: CallbackQuery, token: str, api_client: APIClient):
    """Показать детали задачи"""
    task_id = callback.data.split(':')[1]
    
    try:
        task = await api_client.get_task(token, task_id)
        
        text = format_task(task)
        text += f"\n\n🆔 ID: <code>{task['id']}</code>"
        
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Выполнить", callback_data=f"complete:{task_id}")
        kb.button(text="❌ Отменить", callback_data=f"cancel:{task_id}")
        kb.button(text="🗑 Удалить", callback_data=f"delete:{task_id}")
        kb.button(text="◀️ Назад", callback_data=f"back")
        kb.adjust(2)
        
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup()
        )
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)


@router.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery):
    """Вернуться назад"""
    await callback.message.delete()
    await callback.answer()


@router.message(Command('overdue'))
@router.message(F.text == "⚠️ Просроченные")
async def cmd_overdue(message: Message, token: str, api_client: APIClient):
    """Показать просроченные задачи"""
    try:
        tasks = await api_client.get_overdue_tasks(token)
        
        if not tasks:
            await message.answer("✅ У вас нет просроченных задач!")
            return
        
        await message.answer(f"⚠️ <b>Просроченные задачи ({len(tasks)}):</b>")
        
        for task in tasks:
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Выполнить", callback_data=f"complete:{task['id']}")
            kb.button(text="🗑 Удалить", callback_data=f"delete:{task['id']}")
            kb.adjust(2)
            
            await message.answer(
                format_task(task),
                reply_markup=kb.as_markup()
            )
    
    except APIError as e:
        await message.answer(f"❌ Ошибка API: {e.detail}")