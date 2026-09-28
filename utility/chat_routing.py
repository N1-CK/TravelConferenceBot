"""Text shown to a user when a manager changes the reply destination."""

from database import db
from utility.lang_utils import t


async def prepare_department_message(user_id: int, department: str, text: str) -> str:
    if department not in ('pr', 'event', 'travel'):
        raise ValueError('Invalid department')
    if (await db.get_chat_department(user_id) != department
            or await db.get_last_outgoing_department(user_id) != department):
        intro = await t(user_id, 'chat_from_department', department=department.upper())
        return f'{intro}\n\n{text}' if text else intro
    return text
