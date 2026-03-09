from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from utility.auth import check_whitelist
from database import db
from keyboards import get_agreement_keyboard, get_main_menu_keyboard
from datetime import datetime

router = Router()


class RegistrationStates(StatesGroup):
    """Состояния регистрации нового пользователя"""
    waiting_for_language = State()
    waiting_for_fullname = State()
    waiting_for_position = State()
    waiting_for_company = State()

class ConferenceViewStates(StatesGroup):
    viewing_conference = State()

# Тексты на разных языках
LANG_TEXTS = {
    'ru': {
        'welcome': "Добро пожаловать в Travel Conference Bot!",
        'choose_lang': "Пожалуйста, выберите язык:",
        'ask_fullname': "Пожалуйста, введите ваше имя и фамилию:",
        'ask_position': "Укажите вашу должность:",
        'ask_company': "Укажите название вашей компании/партнерской программы:",
        'success': (
            "Добро пожаловать в Travel Conference Bot!"
        ),
        'language_selected': "🇷🇺 Выбран русский язык",
        'error_no_username': (
            "У вас не установлен username в Telegram.\n\n"
            "Пожалуйста, установите username в настройках Telegram:\n"
            "Настройки → Имя пользователя (username)"
        ),
        'error_not_whitelisted': (
            "Извините, у вас нет доступа к боту конференции.\n\n"
            "Обратитесь к своему руководителю."
        )
    },
    'en': {
        'welcome': "Welcome to Travel Conference Bot!",
        'choose_lang': "Please choose your language:",
        'ask_fullname': "Please enter your full name:",
        'ask_position': "Enter your job title:",
        'ask_company': "Enter your company/partner program name:",
        'success': (
            "Welcome to Travel Conference Bot!"
        ),
        'language_selected': "🇬🇧 English selected",
        'error_no_username': (
            "You don't have a username set in Telegram.\n\n"
            "Please set your username in Telegram settings:\n"
            "Settings → Username"
        ),
        'error_not_whitelisted': (
            "Sorry, you do not have access to this bot.\n\n"
            "Please contact your manager."
        )
    }
}


def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown"""
    escape_chars = r'_*[]()~`>#+=|{}!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
    )
    return builder.as_markup()


async def check_and_register_user(message: Message, user_id: int, username: str) -> bool:
    """Проверяет, прошел ли пользователь полную регистрацию"""
    # Проверяем, есть ли уже данные пользователя
    user_data = await db.get_user_data(user_id)
    if user_data and user_data.get('full_name') and user_data.get('company'):
        # Пользователь уже зарегистрирован
        return True
    return False


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    lang = 'ru'

    if not username:
        await message.answer(LANG_TEXTS['ru']['error_no_username'])
        return

    if not await check_whitelist(username):
        await message.answer(LANG_TEXTS['ru']['error_not_whitelisted'])
        return

    if await check_and_register_user(message, user_id, username):
        # Если зарегистрирован - показываем список конференций
        await show_conferences_selection(message, username, lang)
        return

    # Новый пользователь - регистрация
    await state.set_state(RegistrationStates.waiting_for_language)
    await message.answer(
        "🌐 Please choose your language / Пожалуйста, выберите язык:",
        reply_markup=get_language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"), RegistrationStates.waiting_for_language)
async def process_language_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    lang = callback.data.split("_")[1]  # 'ru' или 'en'

    # Сохраняем выбранный язык
    await state.update_data(language=lang)

    # Подтверждаем выбор
    await callback.message.edit_text(
        LANG_TEXTS[lang]['language_selected']
    )

    # Переходим к следующему шагу — запрос ФИО
    await state.set_state(RegistrationStates.waiting_for_fullname)

    await callback.message.answer(
        LANG_TEXTS[lang]['ask_fullname']
    )

    await callback.answer()


@router.message(RegistrationStates.waiting_for_fullname)
async def process_fullname(message: Message, state: FSMContext):
    """Обработка ввода ФИО"""
    fullname = message.text.strip()

    # Валидация (минимальная)
    if len(fullname) < 3 or len(fullname) > 100:
        data = await state.get_data()
        lang = data.get('language', 'ru')
        await message.answer(
            "❌ Пожалуйста, введите корректное имя (от 3 до 100 символов).\n"
            "Please enter a valid name (3-100 characters)."
        )
        return

    # Сохраняем ФИО
    await state.update_data(fullname=fullname)

    # Запрашиваем должность
    data = await state.get_data()
    lang = data.get('language', 'ru')
    await state.set_state(RegistrationStates.waiting_for_position)

    await message.answer(
        LANG_TEXTS[lang]['ask_position']
    )


@router.message(RegistrationStates.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    """Обработка ввода должности"""
    position = message.text.strip()

    if len(position) < 2 or len(position) > 100:
        data = await state.get_data()
        lang = data.get('language', 'ru')
        await message.answer(
            "❌ Пожалуйста, введите корректную должность.\n"
            "Please enter a valid job title."
        )
        return

    await state.update_data(position=position)

    # Запрашиваем компанию
    data = await state.get_data()
    lang = data.get('language', 'ru')
    await state.set_state(RegistrationStates.waiting_for_company)

    await message.answer(
        LANG_TEXTS[lang]['ask_company']
    )


async def show_conferences_selection(message: Message, username: str, lang: str = 'ru'):
    """Показать пользователю список его конференций в виде кнопок"""
    conferences = await db.get_user_conferences(username)

    if not conferences:
        await message.answer(
            LANG_TEXTS[lang]['success'],
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Создаем клавиатуру с кнопками конференций
    builder = InlineKeyboardBuilder()

    for conf in conferences:
        # Формируем текст кнопки с городом если есть
        button_text = conf['conference_name']
        if conf.get('city'):
            button_text += f" ({conf['city']})"

        builder.row(InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_conf_{conf['conference_name']}"
        ))

    # Добавляем кнопку "Пропустить" если нужно
    builder.row(InlineKeyboardButton(
        text="⏭️ Пропустить",
        callback_data="skip_conf_selection"
    ))

    await message.answer(
        "📋 Выберите вашу конференцию / Select your conference:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("select_conf_"))
async def process_conference_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора конференции"""
    conference_name = callback.data.replace("select_conf_", "")

    # Сохраняем выбранную конференцию в состояние
    await state.update_data(selected_conference=conference_name)

    # Логируем выбор
    await db.log_user_action(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        action="conference_selected",
        details={"conference": conference_name}
    )

    # Показываем главное меню с новой кнопкой
    await show_main_menu_with_conf_button(callback.message, state)


@router.callback_query(F.data == "skip_conf_selection")
async def skip_conference_selection(callback: CallbackQuery, state: FSMContext):
    """Пропустить выбор конференции"""
    await show_main_menu_with_conf_button(callback.message, state)


async def show_main_menu_with_conf_button(message: Message, state: FSMContext):
    """Показать главное меню с кнопкой выбора конференции"""
    from keyboards import get_main_menu_keyboard

    # Получаем выбранную конференцию из состояния
    data = await state.get_data()
    selected_conf = data.get('selected_conference')

    # Модифицируем главное меню - добавляем кнопку выбора конференции
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 PR", callback_data="menu_pr"),
        InlineKeyboardButton(text="🎪 EVENT", callback_data="menu_event"),
        InlineKeyboardButton(text="✈️ TRAVEL", callback_data="menu_travel")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
        InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile")
    )
    # Добавляем кнопку выбора конференции
    conf_text = "🔄 Сменить конференцию" if selected_conf else "🎯 Выбрать конференцию"
    builder.row(InlineKeyboardButton(text=conf_text, callback_data="show_conference_list"))

    welcome_text = f"Выбрана конференция: *{selected_conf}*\n\n" if selected_conf else ""
    welcome_text += "Главное меню. Выберите раздел:"

    await message.edit_text(
        welcome_text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN if selected_conf else None
    )

@router.callback_query(F.data == "show_conference_list")
async def show_conference_list(callback: CallbackQuery, state: FSMContext):
    """Показать список конференций для выбора"""
    username = callback.from_user.username
    await show_conferences_selection(callback.message, username)

@router.message(RegistrationStates.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    """Обработка ввода компании и завершение регистрации"""
    company = message.text.strip()

    if len(company) < 2 or len(company) > 100:
        data = await state.get_data()
        lang = data.get('language', 'ru')
        await message.answer(
            "❌ Пожалуйста, введите корректное название компании.\n"
            "Please enter a valid company name."
        )
        return

    # Получаем все данные из state
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username
    lang = data.get('language', 'ru')
    fullname = data.get('fullname')
    position = data.get('position')

    # Сохраняем пользователя в БД
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
        # Логируем успешную регистрацию
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="user_registered",
            details={
                "language": lang,
                "full_name": fullname,
                "position": position,
                "company": company
            }
        )

        # ПОКАЗЫВАЕМ КОНФЕРЕНЦИИ ПЕРЕД ГЛАВНЫМ МЕНЮ
        await show_conferences_selection(message, username, lang)
    else:
        # Ошибка сохранения
        await message.answer(
            "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.\n"
            "An error occurred. Please try again later."
        )

    # Очищаем состояние
    await state.clear()


@router.callback_query(F.data.startswith("view_conf_"))
async def view_conference_details(callback: CallbackQuery):
    """Показать детали конкретной конференции"""
    conference_name = callback.data.replace("view_conf_", "")
    username = callback.from_user.username

    conferences = await db.get_user_conferences(username)
    conference = next((c for c in conferences if c['conference_name'] == conference_name), None)

    if not conference:
        await callback.answer("Conference not found", show_alert=True)
        return

    # Формируем детальное сообщение
    details = f"📋 *{conference['conference_name']}*\n\n"

    if conference.get('city'):
        details += f"📍 *City:* {conference['city']}\n"

    if conference.get('conference_start_date') and conference.get('conference_end_date'):
        details += f"📅 *Conference dates:* {conference['conference_start_date']} - {conference['conference_end_date']}\n"

    if conference.get('trip_start_date') and conference.get('trip_end_date'):
        details += f"✈️ *Trip dates:* {conference['trip_start_date']} - {conference['trip_end_date']}\n"

    # Клавиатура для возврата
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Back to conferences", callback_data="back_to_conferences"),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")
    )

    await callback.message.edit_text(
        details,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "back_to_conferences")
async def back_to_conferences(callback: CallbackQuery):
    """Вернуться к списку конференций"""
    username = callback.from_user.username
    user_data = await db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru') if user_data else 'ru'

    await show_conferences_selection(callback.message, username, lang)


# Обработчик для уже зарегистрированных пользователей
@router.callback_query(F.data == "menu_main")
async def return_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню для зарегистрированных пользователей"""
    await state.clear()

    # Получаем язык пользователя из БД
    user_data = await db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru') if user_data else 'ru'

    await callback.message.edit_text(
        LANG_TEXTS[lang]['success'],
        reply_markup=get_main_menu_keyboard()
    )