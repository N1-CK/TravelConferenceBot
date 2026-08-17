from database import db
import logging

logger = logging.getLogger(__name__)

async def check_whitelist(username: str) -> bool:
    """Проверка whitelist (удобная обертка)"""
    if not username:
        return False
    clean_username = username.lstrip('@').strip()
    return await db.check_whitelist(clean_username)

async def add_to_whitelist(username: str, telegram_id: int = None, company: str = None, role: str = None):
    """Добавление пользователя в whitelist"""
    if not username:
        return False
    clean_username = username.lstrip('@').strip()
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f'''
                INSERT INTO {db.db_schema_config}.whitelist (username, telegram_id, company, role)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (username) DO UPDATE
                SET telegram_id = EXCLUDED.telegram_id,
                    company = EXCLUDED.company,
                    role = EXCLUDED.role,
                    is_active = TRUE
            ''', clean_username, telegram_id, company, role)
            logger.info(f"✅ Пользователь {clean_username} добавлен в whitelist")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления в whitelist: {e}")
        return False