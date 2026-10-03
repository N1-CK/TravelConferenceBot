"""Show the department only in menus and the first information screen below them."""

import logging
from contextvars import ContextVar

from aiogram import BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

from database import db
from utility.lang_utils import get_text_sync, get_user_lang

logger = logging.getLogger(__name__)

_screen_user = ContextVar('department_screen_user', default=None)
_INFO_SCREENS = frozenset({
    'pr_conference_bot', 'pr_conference_rules', 'pr_dinner',
    'event_info', 'event_booth',
    'travel_flight_info', 'travel_hotel', 'travel_my_requests', 'travel_compensation',
})


class DepartmentScreenMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id if event.data in _INFO_SCREENS else None
        token = _screen_user.set(user_id)
        try:
            return await handler(event, data)
        finally:
            _screen_user.reset(token)


def is_department_menu(method):
    keyboard = getattr(method, 'reply_markup', None)
    buttons = {button.callback_data
               for row in getattr(keyboard, 'inline_keyboard', []) for button in row}
    return any(required <= buttons for required in (
        {'menu_pr', 'menu_event', 'menu_travel'},
        {'pr_banner', 'pr_business_cards'},
        {'event_ticket', 'event_booth'},
        {'travel_flight_request', 'travel_hotel'},
    ))


class DepartmentStatusMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        chat_id = getattr(method, 'chat_id', None)
        # Department notifications go to groups; only decorate private user screens.
        if isinstance(chat_id, str) and chat_id.isdigit():
            chat_id = int(chat_id)
        if not isinstance(chat_id, int) or chat_id <= 0:
            return await make_request(bot, method)
        if not is_department_menu(method) and _screen_user.get() != chat_id:
            return await make_request(bot, method)

        field = 'text' if 'text' in type(method).model_fields else 'caption'
        if field not in type(method).model_fields:
            return await make_request(bot, method)
        text = getattr(method, field) or ''
        # The main menu already contains the status, including the unset state.
        labels = [get_text_sync(lang, 'department_status', department='').strip()
                  for lang in ('ru', 'en')]
        if any(label in text for label in labels):
            return await make_request(bot, method)

        try:
            department = await db.get_chat_department(chat_id)
            if department:
                lang = await get_user_lang(chat_id)
                status = get_text_sync(lang, 'department_status', department=department.upper())
                decorated = f'{text}\n\n{status}' if text else status
                # Preserve text/entities and Telegram's text/caption length limits.
                if len(decorated) <= (4096 if field == 'text' else 1024):
                    method = method.model_copy(update={field: decorated})
        except Exception:
            logger.exception('Could not add department status for user %s', chat_id)

        return await make_request(bot, method)
