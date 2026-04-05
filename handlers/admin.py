import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
import logging
from datetime import datetime

import os
from keyboards import get_main_menu_keyboard
import asyncio

logger = logging.getLogger(__name__)
router = Router()


class TravelStatusForm(StatesGroup):
    waiting_for_request_id = State()
    waiting_for_new_status = State()
    waiting_for_comment = State()


async def is_admin(user_id: int) -> bool:
    # Получаем список админов из переменной окружения
    admins_str = os.getenv("ADMIN_USER_IDS", "252703147")
    admins = [int(id.strip()) for id in admins_str.split(",")]

    # Или проверяем в БД
    try:
        async with db.pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT 1 FROM {db.db_schema}.admins WHERE user_id = $1",
                user_id
            )
            return bool(result) or (user_id in admins)
    except:
        return user_id in admins


@router.message(Command("admin"))
async def admin_command(message: Message):
    """Доступ к админ-панели"""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав доступа к админ-панели")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="📝 Заявки", callback_data="admin_requests")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast")]
    ])

    await message.answer(
        "🛠️ Админ-панель\n\n"
        "Выберите раздел:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав доступа", show_alert=True)
        return

    try:
        async with db.pool.acquire() as conn:
            # Общая статистика
            total_users = await conn.fetchval(f"SELECT COUNT(*) FROM {db.db_schema_config}.whitelist WHERE is_active = TRUE")
            active_today = await conn.fetchval(f"""
                SELECT COUNT(DISTINCT user_id) FROM {db.db_schema}.user_logs 
                WHERE timestamp > NOW() - INTERVAL '1 day'
            """)

            # Статистика по заявкам
            banner_requests = await conn.fetchval(f"SELECT COUNT(*) FROM {db.db_schema}.pr_banner_requests")
            business_cards = await conn.fetchval(f"SELECT COUNT(*) FROM {db.db_schema}.pr_business_cards")
            visa_requests = await conn.fetchval(f"SELECT COUNT(*) FROM {db.db_schema}.travel_visa_requests")
            certificates = await conn.fetchval(f"SELECT COUNT(*) FROM {db.db_schema}.event_certificates")

            stats_text = (
                "📊 Статистика бота:\n\n"
                f"👥 Пользователи: {total_users}\n"
                f"🟢 Активных за 24ч: {active_today}\n\n"
                f"📈 Заявок всего:\n"
                f"• Баннеры: {banner_requests}\n"
                f"• Визитки: {business_cards}\n"
                f"• Визы: {visa_requests}\n"
                f"• Справки: {certificates}\n\n"
                f"🔄 Последнее обновление: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )

            await callback.message.edit_text(stats_text)

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.message.edit_text("❌ Ошибка получения статистики")


@router.callback_query(F.data == "admin_users")
async def manage_users(callback: CallbackQuery):
    """Управление пользователями"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав доступа", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Загрузить CSV", callback_data="upload_csv")],
        [InlineKeyboardButton(text="👁️ Просмотреть список", callback_data="view_users")],
        [InlineKeyboardButton(text="➕ Добавить вручную", callback_data="add_user")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(
        "👥 Управление пользователями\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


class BroadcastForm(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав доступа", show_alert=True)
        return

    await state.set_state(BroadcastForm.waiting_for_message)
    await callback.message.edit_text(
        "📨 Массовая рассылка\n\n"
        "Введите сообщение для рассылки (можно использовать HTML разметку):\n\n"
        "⚠️ Максимум 4000 символов\n"
        "❌ Для отмены отправьте /cancel"
    )


@router.message(BroadcastForm.waiting_for_message, F.text)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if len(message.text) > 4000:
        await message.answer("❌ Сообщение слишком длинное. Максимум 4000 символов.")
        return

    await state.update_data(broadcast_message=message.text)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_send_all")],
        [InlineKeyboardButton(text="👥 Отправить активным", callback_data="broadcast_send_active")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")]
    ])

    await message.answer(
        f"📨 Подтвердите рассылку:\n\n"
        f"Сообщение ({len(message.text)} символов):\n"
        f"---\n"
        f"{message.text[:300]}...\n"
        f"---\n\n"
        f"Кому отправить?",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "broadcast_send_all")
async def send_broadcast_all(callback: CallbackQuery, state: FSMContext, bot):
    """Отправка рассылки всем пользователям"""
    data = await state.get_data()
    message_text = data.get('broadcast_message', '')

    await callback.message.edit_text("🔄 Начинаю рассылку...")

    try:
        async with db.pool.acquire() as conn:
            # Получаем всех активных пользователей
            users = await conn.fetch(f"""
                SELECT DISTINCT user_id FROM {db.db_schema}.user_logs 
                WHERE user_id IS NOT NULL
            """)

            success_count = 0
            fail_count = 0

            from main import bot

            await callback.message.edit_text("🔄 Начинаю рассылку...")

            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user['user_id'],
                        text=message_text,
                        parse_mode="HTML"
                    )
                    success_count += 1
                    await asyncio.sleep(0.05)  # Защита от лимитов Telegram
                except Exception as e:
                    logger.error(f"Не удалось отправить пользователю {user['user_id']}: {e}")
                    fail_count += 1

            await callback.message.edit_text(
                f"✅ Рассылка завершена!\n\n"
                f"📊 Результаты:\n"
                f"• Успешно: {success_count}\n"
                f"• Не удалось: {fail_count}\n"
                f"• Всего: {len(users)}"
            )

            # Логируем рассылку
            await db.log_user_action(
                user_id=callback.from_user.id,
                username=callback.from_user.username,
                action="broadcast_sent",
                details={
                    "type": "all",
                    "success": success_count,
                    "failed": fail_count,
                    "message_length": len(message_text)
                }
            )

    except Exception as e:
        logger.error(f"Ошибка рассылки: {e}")
        await callback.message.edit_text(f"❌ Ошибка при рассылке: {e}")

    await state.clear()


@router.callback_query(F.data == "admin_travel_requests")
async def manage_travel_requests(callback: CallbackQuery):
    """Управление travel-заявками (админ)"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав доступа", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛂 Visa Requests", callback_data="admin_visa_requests")],
        [InlineKeyboardButton(text="✈️ Flight Requests", callback_data="admin_flight_requests")],
        [InlineKeyboardButton(text="📝 Change Status", callback_data="admin_change_status")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="admin_back")]
    ])

    await callback.message.edit_text(
        "🛄 Travel Requests Management\n\n"
        "Select category to manage:",
        reply_markup=keyboard
    )



@router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: CallbackQuery):
    """Вернуться в админ-панель"""
    await admin_command(callback.message)