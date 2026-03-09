# handlers/navigation.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

router = Router()


@router.callback_query(F.data == "menu_main")
async def go_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в главное меню из любого места"""
    await state.clear()

    from keyboards import get_main_menu_keyboard
    await callback.message.edit_text(
        "Главное меню. Выберите раздел:",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("back_to_"))
async def go_back_in_form(callback: CallbackQuery, state: FSMContext):
    """Назад в форме (универсальный обработчик)"""
    target = callback.data.replace("back_to_", "")

    if target == "menu_pr":
        from handlers.pr import get_pr_menu_keyboard
        await callback.message.edit_text(
            "📢 Раздел PR\n\nВыберите опцию:",
            reply_markup=get_pr_menu_keyboard()
        )
    elif target == "menu_event":
        from handlers.event import get_event_menu_keyboard
        await callback.message.edit_text(
            "🎪 Раздел EVENT\n\nВыберите опцию:",
            reply_markup=get_event_menu_keyboard()
        )
    elif target == "menu_travel":
        from handlers.travel import get_travel_menu_keyboard
        await callback.message.edit_text(
            "✈️ Раздел TRAVEL\n\nВыберите опцию:",
            reply_markup=get_travel_menu_keyboard()
        )
    else:
        await go_to_main_menu(callback, state)

    await state.clear()