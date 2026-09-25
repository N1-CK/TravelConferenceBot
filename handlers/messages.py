from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from database import db
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith('chat_department_'))
async def select_chat_department(callback: CallbackQuery):
    department = callback.data[len('chat_department_'):]
    if department not in ('pr', 'event', 'travel'):
        await callback.answer('Неизвестный раздел', show_alert=True)
        return
    await db.set_chat_department(callback.from_user.id, department)
    await callback.message.answer(f'✅ Направление: {department.upper()}. Теперь можете написать сообщение.')
    await callback.answer()


@router.message()
async def handle_user_message(message: Message, state: FSMContext):
    """Сохранение в БД и отправка менеджерам"""
    # Если у пользователя активно состояние FSM (заполняет анкету/форму), пропускаем
    current_state = await state.get_state()
    if current_state:
        return
    if message.chat.type != 'private' or (message.text or '').startswith('/'):
        return

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    text = message.text or message.caption or ""
    file_type = None
    file_id = None

    department = await db.get_chat_department(user_id)
    if not department:
        await message.answer(
            'Выберите отдел для переписки:',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='✈️ Travel', callback_data='chat_department_travel')],
                [InlineKeyboardButton(text='🎪 Event', callback_data='chat_department_event')],
                [InlineKeyboardButton(text='📢 PR', callback_data='chat_department_pr')],
            ])
        )
        return

    if message.photo:
        file_type = 'photo'
        file_id = message.photo[-1].file_id
    elif message.document:
        file_type = 'document'
        file_id = message.document.file_id
    elif message.video:
        file_type = 'video'
        file_id = message.video.file_id
    elif message.audio:
        file_type = 'audio'
        file_id = message.audio.file_id
    elif message.voice:
        file_type = 'voice'
        file_id = message.voice.file_id
    elif message.video_note:
        file_type = 'video_note'
        file_id = message.video_note.file_id

    try:
        await db.save_user_message(
            user_id=user_id,
            username=username,
            message_text=text,
            file_type=file_type,
            file_id=file_id,
            direction='incoming',
            department=department
        )
    except Exception as e:
        logger.error(f"Error saving user message: {e}")
        await message.answer('Не удалось доставить сообщение. Попробуйте ещё раз.')
        return

    from handlers.managers_chat import forward_user_message_to_admin
    await forward_user_message_to_admin(bot=message.bot, message=message, department=department)
