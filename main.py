# main.py
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from database import db

# Загружаем переменные окружения
load_dotenv()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Создаем бота и диспетчер
bot = Bot(token=os.getenv("TG_BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def on_startup():
    """Функция, выполняемая при старте бота"""
    try:
        # Подключаемся к БД
        if not await db.create_pool():
            logger.error("❌ Не удалось подключиться к БД")
            return False

        # Создаем таблицы для менеджеров (если нет)
        await db.create_managers_tables()

        logger.info("✅ Бот запущен. База данных инициализирована.")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при старте бота: {e}")
        return False


async def on_shutdown():
    """Функция, выполняемая при выключении бота"""
    try:
        await db.close()
        logger.info("✅ Бот выключен. Соединения закрыты.")
    except Exception as e:
        logger.error(f"❌ Ошибка при выключении бота: {e}")


async def main():
    # Создаем пул соединений с БД
    if not await db.create_pool():
        logger.error("❌ Failed to connect to database")
        return

    try:
        from handlers import (
            start_router, menu_router, pr_router,
            event_router, admin_router,
            navigation_router, messages_router
        )

        from handlers.travel_module import router as travel_router
        from handlers.dinner.affiliate_integrated import router as affiliate_router
        from handlers.managers_chat import router as managers_chat_router

        dp.include_router(start_router)
        dp.include_router(menu_router)
        dp.include_router(pr_router)
        dp.include_router(event_router)
        dp.include_router(travel_router)
        dp.include_router(admin_router)
        dp.include_router(navigation_router)
        dp.include_router(affiliate_router)
        dp.include_router(managers_chat_router)
        dp.include_router(messages_router)

        logger.info("✅ All routers registered")

    except ImportError as e:
        logger.error(f"❌ Router import error: {e}")
        return

    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("✅ Bot started and ready")

    # Start bot
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot start error: {e}")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("✅ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")