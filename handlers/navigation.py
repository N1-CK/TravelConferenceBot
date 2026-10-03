# handlers/navigation.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from utility.lang_utils import format_main_menu_text

router = Router()


async def go_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Общий fallback возврата в главное меню."""
    from keyboards import get_main_menu_keyboard

    await state.clear()
    await callback.message.edit_text(
        await format_main_menu_text(callback.from_user.id),
        reply_markup=await get_main_menu_keyboard(callback.from_user.id)
    )


@router.callback_query(F.data.in_({'back_to_menu_pr', 'back_to_menu_event', 'back_to_menu_travel'}))
async def go_back_in_form(callback: CallbackQuery, state: FSMContext):
    """Legacy department aliases; never intercept another form's Back button."""
    from handlers.menu import render_department_menu
    department = callback.data.removeprefix('back_to_menu_')
    await render_department_menu(callback, state, department)
