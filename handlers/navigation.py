# handlers/navigation.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db

router = Router()


async def go_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Общий fallback возврата в главное меню."""
    from keyboards import get_main_menu_keyboard

    await state.clear()
    await callback.message.edit_text(
        "Главное меню. Выберите раздел:",
        reply_markup=await get_main_menu_keyboard(callback.from_user.id)
    )


@router.callback_query(F.data.startswith("back_to_"))
async def go_back_in_form(callback: CallbackQuery, state: FSMContext):
    """Назад в форме (универсальный обработчик)"""
    target = callback.data.replace("back_to_", "")
    user_id = callback.from_user.id
    if target == "menu_pr":
        await db.set_chat_department(user_id, 'pr')
        from handlers.pr import get_pr_menu_keyboard
        await callback.message.edit_text(
            "📢 Раздел PR\n\nВыберите опцию:",
            reply_markup=await get_pr_menu_keyboard(user_id)
        )
    elif target == "menu_event":
        await db.set_chat_department(user_id, 'event')
        from handlers.event import get_event_menu_keyboard
        await callback.message.edit_text(
            "🎪 Раздел EVENT\n\nВыберите опцию:",
            reply_markup=await get_event_menu_keyboard(user_id)
        )
    elif target == "menu_travel":
        await db.set_chat_department(user_id, 'travel')
        from handlers.travel_module import get_travel_menu_keyboard
        await callback.message.edit_text(
            "✈️ Раздел TRAVEL\n\nВыберите опцию:",
            reply_markup=await get_travel_menu_keyboard(user_id)
        )
    else:
        await go_to_main_menu(callback, state)

    await state.clear()
