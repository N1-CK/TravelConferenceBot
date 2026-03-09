from aiogram import Router, F
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
    lang = 'ru'  # По умолчанию русский, потом может быть изменен

    # Проверяем наличие username
    if not username:
        await message.answer(LANG_TEXTS['ru']['error_no_username'])
        return

    # Проверяем whitelist
    if not await check_whitelist(username):
        await message.answer(LANG_TEXTS['ru']['error_not_whitelisted'])
        return

    # Проверяем, не проходил ли пользователь уже регистрацию
    if await check_and_register_user(message, user_id, username):
        # Если уже зарегистрирован — сразу показываем главное меню
        await message.answer(
            LANG_TEXTS['ru']['success'],
            reply_markup=get_main_menu_keyboard()
        )
        return

    # НОВЫЙ ПОЛЬЗОВАТЕЛЬ — начинаем регистрацию с выбора языка
    await state.set_state(RegistrationStates.waiting_for_language)

    # Отправляем приветствие и предлагаем выбрать язык
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

        # Показываем финальное приветствие и главное меню
        await message.answer(
            LANG_TEXTS[lang]['success'],
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Ошибка сохранения
        await message.answer(
            "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.\n"
            "An error occurred. Please try again later."
        )

    # Очищаем состояние
    await state.clear()


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