from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Union

from utility.auth import check_whitelist
from database import db
from keyboards import get_main_menu_keyboard
from utility.lang_utils import *

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_language = State()
    waiting_for_fullname = State()
    waiting_for_position = State()
    waiting_for_company = State()


def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
    )
    return builder.as_markup()


async def check_and_register_user(user_id: int, username: str) -> bool:
    user_data = await db.get_user_data(user_id)
    if user_data and user_data.get('full_name') and user_data.get('company'):
        return True
    return False


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        await message.answer(await t(user_id, 'error_no_username'))
        return

    if not await check_whitelist(username):
        await message.answer(await t(user_id, 'error_not_whitelisted'))
        return

    if await check_and_register_user(user_id, username):
        await show_conferences_selection(message, username, user_id)
        return

    await state.set_state(RegistrationStates.waiting_for_language)
    await message.answer(
        await t(user_id, 'choose_lang'),
        reply_markup=get_language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"), RegistrationStates.waiting_for_language)
async def process_language_choice(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)
    await callback.message.edit_text(await t(callback.from_user.id, 'language_selected'))
    await state.set_state(RegistrationStates.waiting_for_fullname)
    await callback.message.answer(await t(callback.from_user.id, 'ask_fullname'))
    await callback.answer()


@router.message(RegistrationStates.waiting_for_fullname)
async def process_fullname(message: Message, state: FSMContext):
    fullname = message.text.strip()
    if len(fullname) < 3 or len(fullname) > 100:
        await message.answer(await t(message.from_user.id, 'error_invalid_name'))
        return
    await state.update_data(fullname=fullname)
    await state.set_state(RegistrationStates.waiting_for_position)
    await message.answer(await t(message.from_user.id, 'ask_position'))


@router.message(RegistrationStates.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    position = message.text.strip()
    if len(position) < 2 or len(position) > 100:
        await message.answer(await t(message.from_user.id, 'error_invalid_position'))
        return
    await state.update_data(position=position)
    await state.set_state(RegistrationStates.waiting_for_company)
    await message.answer(await t(message.from_user.id, 'ask_company'))


@router.message(RegistrationStates.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    company_input = message.text.strip()

    if len(company_input) < 2:
        await message.answer(await t(message.from_user.id, 'error_invalid_company'))
        return

    # Ищем компании по префиксу
    matches = await db.search_companies_by_prefix(company_input)

    if len(matches) == 1:
        # Точное совпадение
        await complete_registration(message, state, matches[0])

    elif len(matches) > 1:
        # Несколько совпадений - показываем кнопки
        builder = InlineKeyboardBuilder()
        for comp in matches:
            builder.row(InlineKeyboardButton(text=comp, callback_data=f"reg_company_{comp}"))
        builder.row(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="reg_company_manual"))

        await state.update_data(manual_company=company_input)
        await message.answer(
            "🔍 Найдено несколько компаний. Выберите одну:",
            reply_markup=builder.as_markup()
        )

    else:
        # Нет совпадений
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"✅ Подтвердить '{company_input}'",
            callback_data=f"reg_company_confirm_{company_input}"
        ))
        builder.row(InlineKeyboardButton(
            text="📋 Выбрать из списка",
            callback_data="reg_company_show_list"
        ))

        await state.update_data(manual_company=company_input)
        await message.answer(
            f"Компания '{company_input}' не найдена в списке.\n\n"
            f"Если это правильное название, нажмите подтвердить.\n"
            f"Иначе выберите из списка:",
            reply_markup=builder.as_markup()
        )


@router.message(RegistrationStates.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    company_input = message.text.strip()

    if len(company_input) < 2:
        await message.answer(await t(message.from_user.id, 'error_invalid_company'))
        return

    # Ищем компании по префиксу
    matches = await db.search_companies_by_prefix(company_input)

    # Сохраняем введенное значение
    await state.update_data(manual_company=company_input)

    if matches:
        # Найдены совпадения - показываем кнопки
        builder = InlineKeyboardBuilder()
        for comp in matches[:10]:  # Не более 10 вариантов
            builder.row(InlineKeyboardButton(text=comp, callback_data=f"reg_company_{comp}"))
        builder.row(InlineKeyboardButton(
            text=f"✅ Подтвердить '{company_input}'",
            callback_data=f"reg_company_confirm_{company_input}"
        ))

        await message.answer(
            f"🔍 Найдено несколько компаний. Выберите одну или подтвердите свой вариант:\n\n"
            f"Ваш ввод: {company_input}",
            reply_markup=builder.as_markup()
        )
    else:
        # Нет совпадений - только подтверждение
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"✅ Подтвердить '{company_input}'",
            callback_data=f"reg_company_confirm_{company_input}"
        ))

        await message.answer(
            f"Компания '{company_input}' не найдена в списке.\n\n"
            f"Если это правильное название, нажмите подтвердить.\n"
            f"Иначе введите название заново:",
            reply_markup=builder.as_markup()
        )


@router.callback_query(F.data.startswith("reg_company_"))
async def process_company_callback(callback: CallbackQuery, state: FSMContext):
    action = callback.data.replace("reg_company_", "")

    if action.startswith("confirm_"):
        company = action.replace("confirm_", "")
        await complete_registration(callback, state, company)
    elif action.startswith("select_"):
        company = action.replace("select_", "")
        await complete_registration(callback, state, company)
    else:
        # Обычный выбор компании из списка
        company = action
        await complete_registration(callback, state, company)


async def complete_registration(update: Union[Message, CallbackQuery], state: FSMContext, company: str):
    """Завершение регистрации"""
    data = await state.get_data()
    user_id = update.from_user.id
    username = update.from_user.username
    lang = data.get('language', 'ru')
    fullname = data.get('fullname')
    position = data.get('position')

    user_data = {
        'user_id': user_id,
        'username': username,
        'language': lang,
        'full_name': fullname,
        'position': position,
        'company': company
    }

    success = await db.save_user_registration(user_data)

    if success:
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="user_registered",
            details={"company": company, "language": lang}
        )

        # Показываем выбор конференции (теперь обязательный)
        if isinstance(update, Message):
            await show_conferences_selection(update, username, user_id)
        else:
            await show_conferences_selection(update.message, username, user_id)
            await update.answer()
    else:
        error_text = await t(user_id, 'error_registration_failed')
        if isinstance(update, Message):
            await update.answer(error_text)
        else:
            await update.message.answer(error_text)

    await state.clear()


async def show_conferences_selection(message: Message, username: str, user_id: int):
    """Показать список конференций пользователя (обязательный выбор)"""
    conferences = await db.get_user_conferences(username)
    lang = await get_user_lang(user_id)

    if not conferences:
        # Если нет конференций, показываем главное меню без выбора
        await message.answer(
            await t(user_id, 'welcome'),
            reply_markup=await get_main_menu_keyboard(user_id)
        )
        return

    builder = InlineKeyboardBuilder()
    for conf in conferences:
        button_text = conf['conference_name']
        if conf.get('city'):
            button_text += f" ({conf['city']})"
        builder.row(InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_conf_{conf['conference_name']}"
        ))

    # Убрали кнопку "Пропустить" - выбор обязателен

    await message.answer(
        get_text_sync(lang, 'select_conference'),  # Локализованный текст
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("select_conf_"))
async def process_conference_selection(callback: CallbackQuery, state: FSMContext):
    conference_name = callback.data.replace("select_conf_", "")
    await state.update_data(selected_conference=conference_name)

    # Сохраняем выбранную конференцию в БД
    user_id = callback.from_user.id
    async with db.pool.acquire() as conn:
        await conn.execute(f"""
            UPDATE {db.db_schema_config}.user_profiles 
            SET selected_conference = $1, updated_at = NOW()
            WHERE user_id = $2
        """, conference_name, user_id)

    await db.log_user_action(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        action="conference_selected",
        details={"conference": conference_name}
    )

    await show_main_menu_with_conf_button(callback.message, state, callback.from_user.id)


@router.callback_query(F.data.startswith("select_conf_"))
async def process_conference_selection(callback: CallbackQuery, state: FSMContext):
    conference_name = callback.data.replace("select_conf_", "")
    await state.update_data(selected_conference=conference_name)

    await db.log_user_action(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        action="conference_selected",
        details={"conference": conference_name}
    )

    await show_main_menu_with_conf_button(callback.message, state)


@router.callback_query(F.data == "skip_conf_selection")
async def skip_conference_selection(callback: CallbackQuery, state: FSMContext):
    await show_main_menu_with_conf_button(callback.message, state)


async def show_main_menu_with_conf_button(message: Message, state: FSMContext, user_id: int = None):
    """Показать главное меню с отображением выбранной конференции"""
    if user_id is None:
        user_id = message.from_user.id

    lang = await get_user_lang(user_id)

    # Получаем выбранную конференцию из БД
    async with db.pool.acquire() as conn:
        selected_conf = await conn.fetchval(f"""
            SELECT selected_conference FROM {db.db_schema_config}.user_profiles 
            WHERE user_id = $1
        """, user_id)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'pr'), callback_data="menu_pr"),
        InlineKeyboardButton(text=get_text_sync(lang, 'event'), callback_data="menu_event"),
        InlineKeyboardButton(text=get_text_sync(lang, 'travel'), callback_data="menu_travel")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'help'), callback_data="menu_help"),
        InlineKeyboardButton(text=get_text_sync(lang, 'my_profile'), callback_data="menu_profile")
    )

    if selected_conf:
        conf_text = get_text_sync(lang, 'switch_conference')
        welcome_text = f"{get_text_sync(lang, 'conference_selected', conference=selected_conf)}\n\n{get_text_sync(lang, 'main_menu_title')}"
    else:
        conf_text = get_text_sync(lang, 'select_conference_button')
        welcome_text = get_text_sync(lang, 'main_menu_title')

    builder.row(InlineKeyboardButton(text=conf_text, callback_data="show_conference_list"))

    await message.edit_text(
        welcome_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown" if selected_conf else None
    )


@router.callback_query(F.data == "show_conference_list")
async def show_conference_list(callback: CallbackQuery, state: FSMContext):
    """Показать список конференций для смены"""
    username = callback.from_user.username
    user_id = callback.from_user.id

    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass

    await show_conferences_selection(callback.message, username, user_id)


@router.callback_query(F.data == "menu_main")
async def return_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_data = await db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru') if user_data else 'ru'

    await callback.message.edit_text(
        await t(callback.from_user.id, 'welcome'),
        reply_markup=await get_main_menu_keyboard(callback.from_user.id)
    )