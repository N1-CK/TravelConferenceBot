from database import db
import logging
import os
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utility.lang_utils import t

logger = logging.getLogger(__name__)

# Инициализируем бота
bot = Bot(token=os.getenv("TG_BOT_TOKEN"))


async def notify_ticket_status_change(user_id: int, request_id: int, old_status: str, new_status: str,
                                      username: str = None):
    """Отправка уведомления об изменении статуса заявки на билет"""
    try:
        # Получаем язык пользователя
        user_data = await db.get_user_data(user_id)
        lang = user_data.get('language', 'ru') if user_data else 'ru'

        # Текст уведомления в зависимости от статуса
        status_messages = {
            'pending': {
                'ru': "В ожидании ⏳",
                'en': "Pending ⏳"
            },
            'in_progress': {
                'ru': "В процессе обработки 🔄",
                'en': "In progress 🔄"
            },
            'ready': {
                'ru': "Готов ✅",
                'en': "Ready ✅"
            }
        }

        status_text_ru = status_messages.get(new_status, {}).get('ru', new_status)
        status_text_en = status_messages.get(new_status, {}).get('en', new_status)

        if lang == 'ru':
            status_display = status_text_ru
            message_text = (
                f"🎫 *Изменение статуса заявки на билет на конференцию*\n\n"
                f"Заявка #{request_id}\n"
                f"Новый статус: *{status_display}*\n\n"
            )
            if new_status == 'ready':
                message_text += (
                    f"Ваш билет готов!\n"
                    f"Билет будет отправлен на указанный email в ближайшее время.\n\n"
                    f"Если у вас есть вопросы, обратитесь к организаторам."
                )
            elif new_status == 'in_progress':
                message_text += (
                    f"Ваша заявка принята в работу.\n"
                    f"Мы свяжемся с вами при необходимости."
                )
            else:
                message_text += (
                    f"Ваша заявка зарегистрирована и ожидает обработки."
                )
        else:
            status_display = status_text_en
            message_text = (
                f"🎫 *Ticket conference request status update*\n\n"
                f"Request #{request_id}\n"
                f"New status: *{status_display}*\n\n"
            )
            if new_status == 'ready':
                message_text += (
                    f"Your conference ticket is ready!\n"
                    f"The ticket will be sent to your email shortly.\n\n"
                )
            elif new_status == 'in_progress':
                message_text += (
                    f"Your request has been accepted for processing.\n"
                    f"We will contact you if necessary."
                )
            else:
                message_text += (
                    f"Your request has been registered and is pending processing."
                )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🏠 Главное меню" if lang == 'ru' else "🏠 Main Menu",
                callback_data="menu_main"
            )]
        ])

        # Отправляем уведомление
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        # Логируем отправку
        await db.log_user_action(
            user_id=user_id,
            username=username or str(user_id),
            action="ticket_status_notification_sent",
            details={
                "request_id": request_id,
                "new_status": new_status,
                "language": lang
            }
        )

        logger.info(f"✅ Уведомление о статусе билета #{request_id} отправлено пользователю {user_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления о статусе билета: {e}")
        return False