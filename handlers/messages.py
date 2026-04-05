# handlers/messages.py
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import db
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик /start - сохраняем сообщение"""
    # Используем await напрямую, так как мы в асинхронной функции
    await db.save_user_message(
        user_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name,
        message_text="/start",
        direction='incoming'
    )
    # Передаем управление основному обработчику start
    from handlers.start import cmd_start as start_handler
    await start_handler(message)


@router.message()
async def handle_user_message(message: Message):
    """Сохраняем все сообщения пользователей в БД для отображения в веб-интерфейсе"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    text = message.text or message.caption or ""
    file_type = None
    file_id = None

    # Определяем тип вложения
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

    # Сохраняем сообщение в БД - используем await
    try:
        msg_id = await db.save_user_message(
            user_id=user_id,
            username=username,
            message_text=text,
            file_type=file_type,
            file_id=file_id,
            direction='incoming'
        )
        logger.info(f"Saved message {msg_id} from user {username} (ID: {user_id})")
    except Exception as e:
        logger.error(f"Error saving user message: {e}")