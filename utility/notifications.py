from database import db
import logging

logger = logging.getLogger(__name__)


async def notify_status_change(user_id: int, request_type: str, request_id: int, new_status: str, comment: str = None):
    """Отправка уведомления об изменении статуса"""
    # Сохраняем в лог
    await db.log_user_action(
        user_id=user_id,
        username="system",
        action=f"{request_type}_status_changed",
        details={
            "request_id": request_id,
            "new_status": new_status,
            "comment": comment
        }
    )


    # TODO: Реализовать отправку через бота
    # await bot.send_message(user_id, f"Статус вашей заявки изменен на: {new_status}")