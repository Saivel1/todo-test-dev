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


def get_task_keyboard(task: dict) -> InlineKeyboardBuilder:
    """
    Создать клавиатуру для задачи в зависимости от её статуса
    """
    kb = InlineKeyboardBuilder()
    status = task['status']
    task_id = task['id']
    
    # Кнопки в зависимости от статуса
    if status in ['pending', 'in_progress']:
        # Активная задача - можно завершить или отменить
        kb.button(text="✅ Выполнить", callback_data=f"complete:{task_id}")
        kb.button(text="❌ Отменить", callback_data=f"cancel:{task_id}")
        kb.button(text="✏️ Детали", callback_data=f"details:{task_id}")
        kb.button(text="🗑 Удалить", callback_data=f"delete:{task_id}")
        kb.adjust(2, 2)
    
    elif status == 'completed':
        # Завершённая задача - только детали и удаление
        kb.button(text="✏️ Детали", callback_data=f"details:{task_id}")
        kb.button(text="🗑 Удалить", callback_data=f"delete:{task_id}")
        kb.adjust(2)
    
    elif status == 'cancelled':
        # Отменённая задача - можно вернуть в работу
        kb.button(text="🔄 Вернуть в работу", callback_data=f"reopen:{task_id}")
        kb.button(text="✏️ Детали", callback_data=f"details:{task_id}")
        kb.button(text="🗑 Удалить", callback_data=f"delete:{task_id}")
        kb.adjust(1, 2)
    
    return kb


@router.message(Command('tasks'))
@router.message(F.text == "📋 Мои задачи")
async def cmd_tasks(message: Message, token: str, api_client: APIClient):
    """Показать все задачи"""
    try:
        # По умолчанию показываем только активные задачи
        # (можно передать ?status=-completed,-cancelled)
        tasks = await api_client.get_tasks(token)
        
        if not tasks:
            await message.answer(
                "📭 У вас пока нет задач.\n\n"
                "Используйте /create чтобы создать первую задачу."
            )
            return
        
        # Фильтруем только активные задачи для списка
        active_tasks = [t for t in tasks if t['status'] in ['pending', 'in_progress']]
        completed_tasks = [t for t in tasks if t['status'] == 'completed']
        
        # Показываем статистику
        await message.answer(
            f"📋 <b>Ваши задачи:</b>\n\n"
            f"⏳ Активных: {len(active_tasks)}\n"
            f"✅ Завершённых: {len(completed_tasks)}\n"
            f"📊 Всего: {len(tasks)}"
        )
        
        # Показываем активные задачи
        if active_tasks:
            await message.answer("⏳ <b>Активные задачи:</b>")
            for task in active_tasks[:10]:  # Первые 10
                kb = get_task_keyboard(task)
                await message.answer(
                    format_task(task),
                    reply_markup=kb.as_markup()
                )
        
        # Если есть завершённые - предлагаем посмотреть
        if completed_tasks:
            kb = InlineKeyboardBuilder()
            kb.button(text=f"✅ Показать завершённые ({len(completed_tasks)})", 
                     callback_data="show_completed")
            await message.answer(
                "Есть завершённые задачи:",
                reply_markup=kb.as_markup()
            )
        
        if len(active_tasks) > 10:
            await message.answer(f"... и ещё {len(active_tasks) - 10} активных задач")
    
    except APIError as e:
        await message.answer(f"❌ Ошибка API: {e.detail}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "show_completed")
async def show_completed_tasks(callback: CallbackQuery, token: str, api_client: APIClient):
    """Показать завершённые задачи"""
    try:
        tasks = await api_client.get_tasks(token)
        completed_tasks = [t for t in tasks if t['status'] == 'completed']
        
        if not completed_tasks:
            await callback.answer("Нет завершённых задач")
            return
        
        await callback.message.answer("✅ <b>Завершённые задачи:</b>")
        
        for task in completed_tasks[:10]:
            kb = get_task_keyboard(task)
            await callback.message.answer(
                format_task(task),
                reply_markup=kb.as_markup()
            )
        
        await callback.answer()
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)


@router.callback_query(F.data.startswith("complete:"))
async def callback_complete_task(callback: CallbackQuery, token: str, api_client: APIClient):
    """Отметить задачу выполненной"""
    task_id = callback.data.split(':')[1]
    
    try:
        task = await api_client.complete_task(token, task_id)
        
        # Обновляем сообщение с новым статусом
        kb = get_task_keyboard(task)
        await callback.message.edit_text(
            format_task(task),
            reply_markup=kb.as_markup()
        )
        await callback.answer("✅ Задача отмечена как выполненная")
    
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)


@router.callback_query(F.data.startswith("cancel:"))
async def callback_cancel_task(callback: CallbackQuery, token: str, api_client: APIClient):
    """Отменить задачу"""
    task_id = callback.data.split(':')[1]
    
    try:
        task = await api_client.cancel_task(token, task_id)
        
        # Обновляем сообщение
        kb = get_task_keyboard(task)
        await callback.message.edit_text(
            format_task(task),
            reply_markup=kb.as_markup()
        )
        await callback.answer("❌ Задача отменена")
    
    except APIError as e:
        await callback.answer(f"❌ Ошибка: {e.detail}", show_alert=True)


@router.callback_query(F.data.startswith("reopen:"))
async def callback_reopen_task(callback: CallbackQuery, token: str, api_client: APIClient):
    """Вернуть задачу в работу"""
    task_id = callback.data.split(':')[1]
    
    try:
        # Обновляем статус на pending
        task = await api_client.update_task(token, task_id, status='pending')
        
        # Обновляем сообщение
        kb = get_task_keyboard(task)
        await callback.message.edit_text(
            format_task(task),
            reply_markup=kb.as_markup()
        )
        await callback.answer("🔄 Задача возвращена в работу")
    
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
        
        kb = get_task_keyboard(task)
        kb.button(text="◀️ Назад", callback_data="back")
        
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
            kb = get_task_keyboard(task)
            await message.answer(
                format_task(task),
                reply_markup=kb.as_markup()
            )
    
    except APIError as e:
        await message.answer(f"❌ Ошибка API: {e.detail}")