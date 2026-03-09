from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_keyboard

router = Router()


@router.callback_query(F.data == "menu_main")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню"""
    await state.clear()  # Очищаем все состояния
    try:
        await callback.message.edit_text(
            "Главное меню. Выберите раздел:",
            reply_markup=get_main_menu_keyboard()
        )
    except:
        await callback.message.delete()
        await callback.answer(
            "Главное меню. Выберите раздел:",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "menu_pr")
async def show_pr_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел PR"""
    from keyboards import get_pr_menu_keyboard

    await callback.message.edit_text(
        "📢 Раздел PR\n\n"
        "Выберите опцию:",
        reply_markup=get_pr_menu_keyboard()
    )


@router.callback_query(F.data == "menu_event")
async def show_event_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел EVENT"""
    from keyboards import get_event_menu_keyboard

    await callback.message.edit_text(
        "🎪 Раздел EVENT\n\n"
        "Выберите опцию:",
        reply_markup=get_event_menu_keyboard()
    )


@router.callback_query(F.data == "menu_travel")
async def show_travel_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел TRAVEL - используем единый travel_module.py"""
    # Вместо прямой загрузки клавиатуры, переходим в travel_module
    from handlers.travel_module import show_travel_menu as travel_menu_handler
    await travel_menu_handler(callback, state)


@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
    user = callback.from_user

    # Создаем клавиатуру с кнопкой "Назад"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        f"👤 Ваш профиль:\n"
        f"Username: @{user.username}\n"
        f"Имя: {user.first_name} {user.last_name or ''}\n"
        f"ID: {user.id}",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery):
    """Показать помощь"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from keyboards import get_main_menu_keyboard

    # Создаем клавиатуру с кнопкой "Главное меню"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        "🆘 Помощь по боту:\n\n"
        "• Для возврата в главное меню нажмите кнопку ниже\n"
        "• По вопросам доступа обращайтесь к администратору\n"
        "• Технические проблемы: support@conference.com",
        reply_markup=keyboard
    )