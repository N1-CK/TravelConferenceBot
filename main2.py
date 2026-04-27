# main2.py - отдельный скрипт для периодической синхронизации whitelist
import asyncio
import logging
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from database import db

# Загружаем переменные окружения
load_dotenv()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sync.log')
    ]
)
logger = logging.getLogger(__name__)

# Глобальный планировщик
scheduler = AsyncIOScheduler()
sync_running = False


async def sync_whitelist_periodically():
    """Периодическая синхронизация whitelist из Google Sheets"""
    global sync_running

    # Предотвращаем одновременный запуск нескольких синхронизаций
    if sync_running:
        logger.warning("⚠️ Sync already in progress, skipping...")
        return

    # Проверяем, инициализирована ли БД
    if db.pool is None:
        logger.warning("⚠️ Database not initialized, skipping sync")
        return

    sync_running = True

    try:
        logger.info("🔄 Starting periodic whitelist sync from Google Sheets...")
        # clear_existing=False при периодической синхронизации,
        # чтобы не терять пользователей, которые могли добавиться вручную
        success = await db.sync_whitelist_from_google_sheets(clear_existing=False)
        if success:
            logger.info("✅ Periodic whitelist sync completed successfully")
        else:
            logger.warning("⚠️ Periodic whitelist sync completed with issues")
    except Exception as e:
        logger.error(f"❌ Error during periodic whitelist sync: {e}")
    finally:
        sync_running = False


async def initial_sync():
    """Первоначальная синхронизация при запуске"""
    try:
        logger.info("🔄 Running initial whitelist sync...")
        # При первом запуске делаем полную очистку
        success = await db.sync_whitelist_from_google_sheets(clear_existing=True)
        if success:
            logger.info("✅ Initial whitelist sync completed successfully")
        else:
            logger.warning("⚠️ Initial whitelist sync completed with issues")
    except Exception as e:
        logger.error(f"❌ Error during initial sync: {e}")


async def on_startup():
    """Инициализация при старте синхронизатора"""
    try:
        # Подключаемся к БД
        if not await db.create_pool():
            logger.error("❌ Failed to connect to database")
            return False

        logger.info("✅ Database connection established")

        # Выполняем первоначальную синхронизацию
        await initial_sync()

        # Настраиваем периодическую синхронизацию каждые 3 минуты
        scheduler.add_job(
            sync_whitelist_periodically,
            trigger=IntervalTrigger(minutes=3),
            id='whitelist_sync',
            next_run_time=datetime.now()
        )

        scheduler.start()
        logger.info("✅ Periodic whitelist sync scheduled (every 3 minutes)")

        return True
    except Exception as e:
        logger.error(f"❌ Error on startup: {e}")
        return False


async def on_shutdown():
    """Остановка синхронизатора"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("✅ Scheduler stopped")

        await db.close()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error on shutdown: {e}")


async def main():
    """Главная функция"""
    logger.info("🚀 Starting Whitelist Sync Service...")

    if not await on_startup():
        logger.error("❌ Failed to start sync service")
        return

    try:
        # Держим скрипт запущенным
        while True:
            await asyncio.sleep(60)  # Проверяем каждую минуту, жив ли планировщик
    except KeyboardInterrupt:
        logger.info("🛑 Stopping sync service...")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("✅ Sync service stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")