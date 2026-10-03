# handlers/menu.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_event_menu_keyboard, get_pr_menu_keyboard, get_travel_menu_keyboard
from database import db
import logging
from utility.lang_utils import get_text_sync, get_user_lang, t, format_main_menu_text

logger = logging.getLogger(__name__)
router = Router()


class ProfileEditStates(StatesGroup):
    """Состояния для редактирования профиля"""
    waiting_for_fullname = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_language = State()

def escape_md(text: str) -> str:
    """Экранирование символов для Markdown во избежание Telegram API Errors"""
    if not text:
        return str(text)
    chars = ['_', '*', '[', ']', '`']
    text = str(text)
    for c in chars:
        text = text.replace(c, f'\\{c}')
    return text


@router.callback_query(F.data == "menu_main")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id

    text = await format_main_menu_text(user_id)

    from keyboards import get_main_menu_keyboard

    markup = await get_main_menu_keyboard(user_id)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode=None
        )
        await callback.answer()
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=markup,
            parse_mode=None
        )


@router.callback_query(F.data == "change_conference")
async def change_conference_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username

    confs = await db.get_user_active_conferences(username)
    if not confs:
        await callback.message.answer("Нет доступных конференций / No available conferences.")
        await callback.answer()
        return

    # Удаляем текущее сообщение с меню
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Вызываем твою готовую функцию показа конференций
    from handlers.start import show_conferences_selection
    await show_conferences_selection(callback.message, username, user_id)

    await callback.answer()


async def render_department_menu(update, state: FSMContext, department: str, cancelled=False):
    """All department entry/return paths share the same screen and routing."""
    await state.clear()
    user_id = update.from_user.id
    await db.set_chat_department(user_id, department)
    selected_conf = await db.get_selected_conference(user_id)
    text = await t(user_id, f'{department}_title')
    text += "\n\n" + await t(user_id, 'department_menu_prompt')
    if selected_conf:
        text += "\n\n" + await t(user_id, 'conference_selected', conference=selected_conf)
    if cancelled:
        text = await t(user_id, 'form_cancelled') + "\n\n" + text
    keyboard_factory = {'pr': get_pr_menu_keyboard, 'event': get_event_menu_keyboard,
                        'travel': get_travel_menu_keyboard}[department]
    keyboard = await keyboard_factory(user_id)
    if isinstance(update, Message):
        await update.answer(text, reply_markup=keyboard)
        return
    try:
        await update.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc).lower():
            # A photo/document cannot be edited into a text menu.
            try:
                await update.message.edit_reply_markup(reply_markup=None)
            except TelegramBadRequest:
                pass
            await update.message.answer(text, reply_markup=keyboard)
    await update.answer()


@router.callback_query(F.data.in_({'menu_pr', 'pr_menu', 'back_to_menu_pr'}))
async def show_pr_menu(callback: CallbackQuery, state: FSMContext):
    await render_department_menu(callback, state, 'pr')


@router.callback_query(F.data.in_({'menu_event', 'back_to_menu_event'}))
async def show_event_menu(callback: CallbackQuery, state: FSMContext):
    await render_department_menu(callback, state, 'event')


@router.callback_query(F.data.in_({'menu_travel', 'travel_back_to_menu', 'back_to_menu_travel'}))
async def show_travel_menu(callback: CallbackQuery, state: FSMContext):
    await render_department_menu(callback, state, 'travel')


def form_department(current_state):
    group = (current_state or '').split(':', 1)[0]
    if group in {'PRBannerForm', 'BusinessCardsForm', 'PRQuestionForm'}:
        return 'pr'
    if group in {'EventTicketForm', 'EventQuestionForm', 'EventCertificateForm'}:
        return 'event'
    if group == 'TravelStates':
        return 'travel'
    return None


@router.callback_query((F.data == 'cancel_form') | F.data.startswith('cancel_form:'))
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    # New buttons carry their owner; old buttons resolve it from the active FSM.
    department = callback.data.partition(':')[2]
    if department not in {'pr', 'event', 'travel'}:
        department = form_department(await state.get_state())
    if not department:
        department = await db.get_chat_department(callback.from_user.id)
    if department in {'pr', 'event', 'travel'}:
        await render_department_menu(callback, state, department, cancelled=True)
    else:
        await show_main_menu(callback, state)


async def cancel_edit(message: Message, state: FSMContext):
    """Handle /cancel before text handlers can consume it as a form answer."""
    current_state = await state.get_state()
    group = (current_state or '').split(':', 1)[0]
    department = form_department(current_state)
    await state.clear()
    if group == 'ProfileEditStates':
        await message.answer(await t(message.from_user.id, 'cancel_edit'))
        await show_profile_as_new_message(message)
    elif group in {'BookingStates', 'ReportStates', 'AffiliateAuthStates'}:
        from handlers.dinner.affiliate_integrated import show_affiliate_main_menu
        if group == 'AffiliateAuthStates':
            from handlers.start import cmd_start
            await cmd_start(message, state)
        else:
            await db.set_chat_department(message.from_user.id, 'pr')
            await show_affiliate_main_menu(message)
    elif department:
        await render_department_menu(message, state, department, cancelled=True)
    else:
        from handlers.start import cmd_start
        await cmd_start(message, state)


@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    """Показать профиль пользователя с данными из БД"""
    await state.clear()
    user_id = callback.from_user.id
    username = callback.from_user.username
    lang = await get_user_lang(user_id)

    # Получаем данные пользователя из БД
    user_data = await db.get_user_data(user_id)

    if not user_data:
        user_data = {
            'user_id': user_id,
            'username': username,
            'full_name': get_text_sync(lang, 'not_specified'),
            'position': get_text_sync(lang, 'not_specified'),
            'company': get_text_sync(lang, 'not_specified'),
            'language': 'ru'
        }
        await db.save_user_registration(user_data)

    lang = user_data.get('language', 'ru')

    # Экранируем поля, чтобы символы вроде подчеркивания не ломали Markdown
    f_name = escape_md(user_data.get('full_name', get_text_sync(lang, 'not_specified')))
    pos = escape_md(user_data.get('position', get_text_sync(lang, 'not_specified')))
    comp = escape_md(user_data.get('company', get_text_sync(lang, 'not_specified')))

    profile_text = await t(
        user_id,
        'profile_template',
        userid=user_id,
        username=escape_md(username),
        full_name=f_name,
        position=pos,
        company=comp,
        language='🇷🇺 Русский' if user_data.get('language') == 'ru' else '🇬🇧 English',
        registered_at=user_data.get('registered_at', '').strftime('%d.%m.%Y') if user_data.get(
            'registered_at') else get_text_sync(lang, 'not_specified')
    )

    # Локализованные кнопки профиля
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_name'), callback_data="profile_edit_name"),
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_position'), callback_data="profile_edit_position")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_company'), callback_data="profile_edit_company"),
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_language'), callback_data="profile_edit_language")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'refresh_profile'), callback_data="profile_refresh"),
        InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="menu_main")
    )

    try:
        await callback.message.edit_text(
            profile_text,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        # Игнорируем ошибку, если сообщение просто не изменилось
        if "message is not modified" not in str(e).lower():
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                profile_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )

    try:
        await callback.answer()
    except Exception:
        pass


@router.callback_query(F.data == "profile_refresh")
async def refresh_profile(callback: CallbackQuery, state: FSMContext):
    """Обновить отображение профиля"""
    await show_profile(callback, state)


@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery):
    """Показать помощь"""
    user_id = callback.from_user.id
    lang = await get_user_lang(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        get_text_sync(lang, 'help_text'),
        reply_markup=keyboard
    )


# ============================================
# РЕДАКТИРОВАНИЕ ИМЕНИ (ЛОКАЛИЗОВАННОЕ)
# ============================================

@router.callback_query(F.data == "profile_edit_name")
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования имени"""
    user_id = callback.from_user.id
    await state.set_state(ProfileEditStates.waiting_for_fullname)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'cancel'), callback_data="menu_profile")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'edit_name_title'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(ProfileEditStates.waiting_for_fullname)
async def process_name_edit(message: Message, state: FSMContext):
    """Обработка нового имени"""
    user_id = message.from_user.id
    new_name = message.text.strip()

    # Валидация
    if len(new_name) < 2 or len(new_name) > 100:
        await message.answer(
            f"{await t(user_id, 'error_invalid_name')}"
        )
        return

    # Обновляем в БД
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {db.db_schema_config}.user_profiles 
                SET full_name = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_name, user_id)

        # Логируем действие
        await db.log_user_action(
            user_id=user_id,
            username=message.from_user.username,
            action="profile_updated",
            details={"field": "full_name", "new_value": new_name}
        )

        field_name = await t(user_id, 'field_name')
        await message.answer(await t(user_id, 'profile_updated', field=field_name))

        # Возвращаемся к профилю
        await show_profile_as_new_message(message)

    except Exception as e:
        logger.error(f"Error updating name: {e}")
        field_name = await t(user_id, 'field_name')
        await message.answer(await t(user_id, 'profile_update_error', field=field_name))

    await state.clear()


# ============================================
# РЕДАКТИРОВАНИЕ ДОЛЖНОСТИ (ЛОКАЛИЗОВАННОЕ)
# ============================================

@router.callback_query(F.data == "profile_edit_position")
async def edit_position_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования должности"""
    user_id = callback.from_user.id
    await state.set_state(ProfileEditStates.waiting_for_position)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'cancel'), callback_data="menu_profile")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'edit_position_title'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(ProfileEditStates.waiting_for_position)
async def process_position_edit(message: Message, state: FSMContext):
    """Обработка новой должности"""
    user_id = message.from_user.id
    new_position = message.text.strip()

    if len(new_position) < 2 or len(new_position) > 100:
        await message.answer(
            f"❌ {await t(user_id, 'error_invalid_position')}"
        )
        return

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {db.db_schema_config}.user_profiles 
                SET position = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_position, user_id)

        await db.log_user_action(
            user_id=user_id,
            username=message.from_user.username,
            action="profile_updated",
            details={"field": "position", "new_value": new_position}
        )

        field_name = await t(user_id, 'field_position')
        await message.answer(await t(user_id, 'profile_updated', field=field_name))
        await show_profile_as_new_message(message)

    except Exception as e:
        logger.error(f"Error updating position: {e}")
        field_name = await t(user_id, 'field_position')
        await message.answer(await t(user_id, 'profile_update_error', field=field_name))

    await state.clear()


# ============================================
# РЕДАКТИРОВАНИЕ КОМПАНИИ (ЛОКАЛИЗОВАННОЕ)
# ============================================

@router.callback_query(F.data == "profile_edit_company")
async def edit_company_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования компании"""
    user_id = callback.from_user.id
    await state.set_state(ProfileEditStates.waiting_for_company)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'cancel'), callback_data="menu_profile")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'edit_company_title'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(ProfileEditStates.waiting_for_company)
async def process_company_edit(message: Message, state: FSMContext):
    """Обработка новой компании"""
    user_id = message.from_user.id
    username = message.from_user.username
    new_company = message.text.strip()

    if len(new_company) < 2 or len(new_company) > 100:
        await message.answer(
            f"❌ {await t(user_id, 'error_invalid_company')}"
        )
        return

    try:
        async with db.pool.acquire() as conn:
            # Обновляем в user_profiles
            await conn.execute(f"""
                UPDATE {db.db_schema_config}.user_profiles 
                SET company = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_company, user_id)


        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="profile_updated",
            details={"field": "company", "new_value": new_company}
        )

        field_name = await t(user_id, 'field_company')
        await message.answer(await t(user_id, 'profile_updated', field=field_name))
        await show_profile_as_new_message(message)

    except Exception as e:
        logger.error(f"Error updating company: {e}")
        field_name = await t(user_id, 'field_company')
        await message.answer(await t(user_id, 'profile_update_error', field=field_name))

    await state.clear()


# ============================================
# РЕДАКТИРОВАНИЕ ЯЗЫКА (ЛОКАЛИЗОВАННОЕ)
# ============================================

@router.callback_query(F.data == "profile_edit_language")
async def edit_language_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования языка"""
    user_id = callback.from_user.id
    await state.set_state(ProfileEditStates.waiting_for_language)

    # Клавиатура выбора языка
    from keyboards import get_language_keyboard

    await callback.message.edit_text(
        await t(user_id, 'edit_language_title'),
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("lang_"), ProfileEditStates.waiting_for_language)
async def process_language_edit(callback: CallbackQuery, state: FSMContext):
    """Обработка нового языка"""
    user_id = callback.from_user.id
    new_lang = callback.data.split("_")[1]  # 'ru' или 'en'

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {db.db_schema_config}.user_profiles 
                SET language = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_lang, user_id)

        await db.log_user_action(
            user_id=user_id,
            username=callback.from_user.username,
            action="profile_updated",
            details={"field": "language", "new_value": new_lang}
        )

        # Уведомление на выбранном языке
        confirm_text = "✅ Language updated to English!" if new_lang == "en" else "✅ Язык обновлен на русский!"
        await callback.message.edit_text(confirm_text)

        # Возвращаемся к профилю
        await show_profile(callback, state)

    except Exception as e:
        logger.error(f"Error updating language: {e}")
        await callback.message.edit_text(f"❌ {await t(user_id, 'profile_update_error', field=await t(user_id, 'field_language'))}")

    await state.clear()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def show_profile_as_new_message(message: Message):
    """Показать профиль как новое сообщение (когда нельзя отредактировать)"""
    user_id = message.from_user.id
    username = message.from_user.username
    lang = await get_user_lang(user_id)

    user_data = await db.get_user_data(user_id)

    if not user_data:
        user_data = {
            'full_name': message.from_user.full_name,
            'position': get_text_sync(lang, 'not_specified'),
            'company': get_text_sync(lang, 'not_specified'),
            'language': 'ru'
        }

    # Экранируем
    f_name = escape_md(user_data.get('full_name', get_text_sync(lang, 'not_specified')))
    pos = escape_md(user_data.get('position', get_text_sync(lang, 'not_specified')))
    comp = escape_md(user_data.get('company', get_text_sync(lang, 'not_specified')))

    profile_text = await t(
        user_id,
        'profile_template',
        userid=user_id,
        username=escape_md(username),
        full_name=f_name,
        position=pos,
        company=comp,
        language='🇷🇺 Русский' if user_data.get('language') == 'ru' else '🇬🇧 English',
        registered_at=user_data.get('registered_at', '').strftime('%d.%m.%Y') if user_data.get('registered_at') else get_text_sync(lang, 'not_specified')
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_name'), callback_data="profile_edit_name"),
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_position'), callback_data="profile_edit_position")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_company'), callback_data="profile_edit_company"),
        InlineKeyboardButton(text=get_text_sync(lang, 'edit_language'), callback_data="profile_edit_language")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'refresh_profile'), callback_data="profile_refresh"),
        InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="menu_main")
    )

    await message.answer(
        profile_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "pr_conference_bot")
async def pr_conference_bot_handler(callback: CallbackQuery):
    """Отправка ссылки на бота конференции"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    selected_conf = await db.get_selected_conference(user_id)
    bot_link = None

    confs = await db.get_user_active_conferences(username)
    for c in confs:
        if c.get('conference_name') == selected_conf:
            bot_link = c.get('bot_link')
            break

    if not bot_link and confs:
        bot_link = confs[0].get('bot_link')

    # Создаем клавиатуру с кнопками Назад и Главное меню
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="menu_pr"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    if bot_link:
        text = f"🤖 Бот конференции: {bot_link}"
    else:
        text = await t(user_id, 'no_bot_link')

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# Обработчик отмены
