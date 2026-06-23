import asyncio
from datetime import datetime, timedelta
from database import db

class DeadlineReminder:
    def __init__(self, bot):
        self.bot = bot
        self.db = db

    async def check_deadlines(self):
        """Проверка дедлайнов каждые 24 часа"""
        while True:
            await asyncio.sleep(86400)  # 24 часа

            incomplete_users = await self.db.get_incomplete_forms()

            for user in incomplete_users:
                await self.bot.send_message(
                    user['user_id'],
                    f"⏰ Напоминание: у вас есть незаполненные формы для конференции!\n"
                    f"Пожалуйста, завершите их до {user['deadline']}"
                )