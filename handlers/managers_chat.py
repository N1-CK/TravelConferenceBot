import asyncio
import json
import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db

router = Router()

import logging
logger = logging.getLogger(__name__)


class ManagerReplyForm(StatesGroup):
    waiting_for_reply = State()


# Хранение соответствия сообщений
user_manager_mapping = {}

# Получаем ID чатов из переменных окружения
PR_MANAGER_CHAT_ID = int(os.getenv("TG_PR_MANAGER_CHAT_ID", 0))
EVENT_MANAGER_CHAT_ID = int(os.getenv("TG_EVENT_MANAGER_CHAT_ID", 0))
TRAVEL_MANAGER_CHAT_ID = int(os.getenv("TG_TRAVEL_MANAGER_CHAT_ID", 0))
ADMIN_CHAT_ID = int(os.getenv("TG_ADMIN_CHAT_ID", 0))


def run_async_safe(coro):
    """Безопасное выполнение асинхронной функции с созданием нового loop"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error in run_async_safe: {e}")
        return None


async def send_question_to_manager(bot: Bot, manager_chat_id: int, user_data: dict,
                                  question_text: str, question_type: str):
    """Отправка вопроса в чат менеджера"""
    if not manager_chat_id:
        print(f"⚠️ Chat ID для менеджера {question_type} не настроен")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Ответить пользователю",
            callback_data=f"reply_to_{user_data['user_id']}_{question_type}"
        )]
    ])

    message_text = (
        f"❓ Новый вопрос ({question_type.upper()})\n\n"
        f"Пользователь: @{user_data['username']}\n"
        f"ID: {user_data['user_id']}\n"
        f"Категория: {user_data['category']}\n"
        f"Вопрос: {question_text}\n"
    )

    try:
        message = run_async_safe(await bot.send_message(
            chat_id=manager_chat_id,
            text=message_text,
            reply_markup=keyboard
        ))

        # Сохраняем соответствие
        key = f"{manager_chat_id}_{message.message_id}"
        user_manager_mapping[key] = {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'question_type': question_type
        }
    except Exception as e:
        print(f"❌ Ошибка отправки в чат менеджера {question_type}: {e}")


@router.callback_query(F.data.startswith("reply_to_"))
async def start_reply_to_user(callback: CallbackQuery, state: FSMContext, bot: Bot):  # ← добавьте bot
    """Начало ответа пользователю"""
    data_parts = callback.data.split("_")
    user_id = int(data_parts[2])
    question_type = data_parts[3] if len(data_parts) > 3 else "general"

    await state.set_state(ManagerReplyForm.waiting_for_reply)
    await state.update_data(
        target_user_id=user_id,
        question_type=question_type,
        manager_message_id=callback.message.message_id
    )

    await callback.message.answer(
        f"📝 Введите ответ для пользователя (ID: {user_id}):\n\n"
        f"Можно использовать форматирование Markdown.\n"
        f"Для отмены отправьте /cancel"
    )


@router.message(ManagerReplyForm.waiting_for_reply)
async def send_reply_to_user(message: Message, state: FSMContext):
    """Отправка ответа пользователю"""
    data = await state.get_data()
    user_id = data['target_user_id']
    reply_text = message.text

    # Отменяем команду /cancel
    if reply_text == "/cancel":
        await message.answer("❌ Отправка ответа отменена.")
        await state.clear()
        return

    try:
        # Получаем бота из контекста сообщения
        bot = message.bot

        # Отправляем пользователю
        run_async_safe(await bot.send_message(
            chat_id=user_id,
            text=f"📨 Ответ от менеджера:\n\n{reply_text}",
            parse_mode="Markdown"
        ))

        # Уведомляем менеджера
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")

        # Логируем с преобразованием в JSON
        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="manager_reply_sent",
            details={
                "to_user_id": user_id,
                "question_type": data['question_type'],
                "reply_length": len(reply_text)
            }
        )

    except Exception as e:
        error_msg = str(e)
        if "Forbidden" in error_msg or "bot was blocked" in error_msg:
            await message.answer(f"❌ Пользователь заблокировал бота или недоступен.")
        elif "user not found" in error_msg:
            await message.answer(f"❌ Пользователь не найден.")
        else:
            await message.answer(f"❌ Ошибка отправки: {error_msg}")

    await state.clear()