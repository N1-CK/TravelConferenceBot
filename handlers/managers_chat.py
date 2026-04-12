# handlers/managers_chat.py - ПОЛНАЯ ВЕРСИЯ С ПОДДЕРЖКОЙ ПЕРЕСЫЛКИ

import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
import logging

router = Router()
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


def get_manager_chat_id(department: str) -> int:
    """Получить ID чата по отделу"""
    mapping = {
        'pr': PR_MANAGER_CHAT_ID,
        'event': EVENT_MANAGER_CHAT_ID,
        'travel': TRAVEL_MANAGER_CHAT_ID
    }
    return mapping.get(department, 0)


async def send_question_to_manager(bot: Bot, manager_chat_id: int, user_data: dict,
                                   question_text: str, question_type: str):
    """Отправка вопроса в чат менеджера"""
    if not manager_chat_id:
        logger.warning(f"⚠️ Chat ID для менеджера {question_type} не настроен")
        return

    # Определяем отдел по типу вопроса
    department = question_type.replace('_question', '')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Ответить пользователю",
            callback_data=f"reply_to_{user_data['user_id']}_{question_type}"
        )],
        [InlineKeyboardButton(
            text="🔄 Переслать в другой отдел",
            callback_data=f"share_question_{question_type}_{user_data.get('question_id', 'new')}"
        )]
    ])

    message_text = (
        f"❓ Новый вопрос ({question_type.upper()})\n\n"
        f"👤 Пользователь: @{user_data['username']}\n"
        f"🆔 ID: {user_data['user_id']}\n"
        f"📂 Категория: {user_data.get('category', 'general')}\n"
        f"📝 Вопрос: {question_text}\n"
    )

    try:
        message = await bot.send_message(
            chat_id=manager_chat_id,
            text=message_text,
            reply_markup=keyboard
        )

        # Сохраняем соответствие
        key = f"{manager_chat_id}_{message.message_id}"
        user_manager_mapping[key] = {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'question_type': question_type,
            'question_id': user_data.get('question_id')
        }
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в чат менеджера {question_type}: {e}")


@router.callback_query(F.data.startswith("reply_to_"))
async def start_reply_to_user(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
    await callback.answer()


@router.callback_query(F.data.startswith("share_question_"))
async def share_question_dialog(callback: CallbackQuery, state: FSMContext):
    """Диалог для пересылки вопроса в другой отдел"""
    data_parts = callback.data.split("_")
    question_type = data_parts[2]  # pr_question, event_question, travel_question
    question_id = data_parts[3] if len(data_parts) > 3 else "new"

    # Определяем текущий отдел
    current_department = question_type.replace('_question', '')

    # Доступные отделы для пересылки
    departments = []
    if current_department != 'pr':
        departments.append(('pr', '📢 PR отдел'))
    if current_department != 'event':
        departments.append(('event', '🎪 Event отдел'))
    if current_department != 'travel':
        departments.append(('travel', '✈️ Travel отдел'))

    builder = InlineKeyboardBuilder()
    for dept, label in departments:
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"share_confirm_{question_type}_{question_id}_{dept}"
        ))
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel_share"
    ))

    await callback.message.answer(
        f"🔄 Выберите отдел для пересылки вопроса:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("share_confirm_"))
async def confirm_share_question(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение пересылки вопроса"""
    data_parts = callback.data.split("_")
    # share_confirm_pr_question_123_travel
    question_type = data_parts[2]  # pr_question
    question_id = data_parts[3]  # 123 или new
    target_department = data_parts[4]  # travel

    source_department = question_type.replace('_question', '')

    # Получаем детали вопроса
    if question_id != 'new':
        question_details = await db.get_question_details(int(question_id), source_department)
    else:
        # Для нового вопроса берем из состояния или маппинга
        question_details = {
            'username': callback.from_user.username,
            'user_id': callback.from_user.id,
            'question': "Вопрос будет переслан",
            'category': 'general'
        }

    # Сохраняем в БД пересылку
    success = await db.share_question_with_department(
        question_id=int(question_id) if question_id != 'new' else 0,
        question_type=question_type,
        source_department=source_department,
        target_department=target_department,
        shared_by=callback.from_user.username
    )

    if success:
        # Отправляем уведомление в чат целевого отдела
        target_chat_id = get_manager_chat_id(target_department)
        if target_chat_id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📝 Ответить пользователю",
                    callback_data=f"reply_to_{question_details.get('user_id', callback.from_user.id)}_{target_department}_question"
                )]
            ])

            await bot.send_message(
                chat_id=target_chat_id,
                text=f"🔄 Пересланный вопрос из отдела {source_department.upper()}\n\n"
                     f"👤 Пользователь: @{question_details.get('username', callback.from_user.username)}\n"
                     f"🆔 ID: {question_details.get('user_id', callback.from_user.id)}\n"
                     f"📝 Вопрос: {question_details.get('question', 'Нет текста вопроса')[:500]}\n\n"
                     f"⚠️ Пожалуйста, ответьте пользователю.",
                reply_markup=keyboard
            )

        await callback.message.edit_text(
            f"✅ Вопрос успешно переслан в отдел {target_department.upper()}"
        )
    else:
        await callback.message.edit_text("❌ Ошибка при пересылке вопроса")

    await callback.answer()


@router.callback_query(F.data == "cancel_share")
async def cancel_share(callback: CallbackQuery):
    """Отмена пересылки"""
    await callback.message.edit_text("❌ Пересылка отменена")
    await callback.answer()


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
        bot = message.bot

        # Отправляем пользователю
        await bot.send_message(
            chat_id=user_id,
            text=f"📨 Ответ от менеджера:\n\n{reply_text}",
            parse_mode="Markdown"
        )

        # Сохраняем в БД
        await db.save_user_message(
            user_id=user_id,
            username=str(user_id),
            message_text=reply_text,
            direction='outgoing',
            manager_id=message.from_user.id
        )

        # Уведомляем менеджера
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")

        # Логируем
        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="manager_reply_sent",
            details={
                "to_user_id": user_id,
                "question_type": data.get('question_type'),
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