from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utility.lang_utils import get_text_sync, get_user_lang


# Глобальные сообщения
SUCCESS_MESSAGES = {
    'banner': "✅ Заявка на баннер отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",
    'business_cards': "✅ Заявка на визитки отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",
    'certificate': "✅ Заявка на справку-вызов отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",
    'visa': "✅ Заявка на визовую поддержку отправлена!\n\nБлагодарим за ответ, наша команда скоро свяжется с тобой для обсуждения деталей.",
    'question': "✅ Вопрос отправлен!\n\nБлагодарим за вопрос. Наша команда скоро свяжется с тобой для обсуждения деталей.",
    'default': "✅ Ваша заявка отправлена!"
}


# Навигационные клавиатуры
def get_agreement_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Принимаю", callback_data="accept_terms"))
    return builder.as_markup()


# keyboards.py - заменить get_main_menu_keyboard

async def get_main_menu_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Главное меню с кнопками Помощь и Профиль"""
    builder = InlineKeyboardBuilder()

    if user_id:
        lang = await get_user_lang(user_id)
        pr_text = get_text_sync(lang, 'pr')
        event_text = get_text_sync(lang, 'event')
        travel_text = get_text_sync(lang, 'travel')
        help_text = get_text_sync(lang, 'help')
        profile_text = get_text_sync(lang, 'my_profile')
    else:
        pr_text = "📢 PR"
        event_text = "🎪 EVENT"
        travel_text = "✈️ TRAVEL"
        help_text = "❓ Помощь"
        profile_text = "👤 Профиль"

    builder.row(
        InlineKeyboardButton(text=pr_text, callback_data="menu_pr"),
        InlineKeyboardButton(text=event_text, callback_data="menu_event"),
        InlineKeyboardButton(text=travel_text, callback_data="menu_travel")
    )
    builder.row(
        InlineKeyboardButton(text=help_text, callback_data="menu_help"),
        InlineKeyboardButton(text=profile_text, callback_data="menu_profile")
    )

    return builder.as_markup()


async def get_pr_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Меню PR с локализацией"""
    lang = await get_user_lang(user_id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'pr_banner'), callback_data="pr_banner"),
        InlineKeyboardButton(text=get_text_sync(lang, 'pr_business_cards'), callback_data="pr_business_cards")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'pr_dinner'), callback_data="pr_dinner"),
        InlineKeyboardButton(text=get_text_sync(lang, 'pr_conference_bot'), callback_data="pr_conference_bot")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'pr_question'), callback_data="pr_question")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="menu_main"),
        InlineKeyboardButton(text=get_text_sync(lang, 'main_menu'), callback_data="menu_main")
    )
    return builder.as_markup()



async def get_event_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Меню EVENT с локализацией - убрана кнопка правил и справки"""
    lang = await get_user_lang(user_id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'event_ticket'), callback_data="event_ticket"),
        InlineKeyboardButton(text=get_text_sync(lang, 'event_booth'), callback_data="event_booth")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'event_info'), callback_data="event_info"),
        InlineKeyboardButton(text=get_text_sync(lang, 'event_question'), callback_data="event_question")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="menu_main")
    )
    return builder.as_markup()


async def get_travel_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню Travel в новом порядке"""
    lang = await get_user_lang(user_id)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_flight_request'), callback_data="travel_flight_request")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_visa_support'), callback_data="travel_visa_support"),
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_flight_info'), callback_data="travel_flight_info")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_hotel'), callback_data="travel_hotel"),
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_per_diem'), callback_data="travel_per_diem")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_my_requests'), callback_data="travel_my_requests"),
        InlineKeyboardButton(text=get_text_sync(lang, 'travel_question'), callback_data="travel_question")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="menu_main")
    )
    return builder.as_markup()


async def get_back_next_keyboard(back_to: str, next_disabled: bool = False,
                                 cancel: bool = True, user_id: int = None) -> InlineKeyboardMarkup:
    """Универсальная клавиатура с кнопками Назад/Отмена"""
    builder = InlineKeyboardBuilder()
    lang = await get_user_lang(user_id) if user_id else 'ru'

    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data=back_to))

    if cancel:
        builder.row(InlineKeyboardButton(text=get_text_sync(lang, 'cancel'), callback_data="cancel_form"))

    return builder.as_markup()


# Специальные клавиатуры
def get_visa_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ У меня есть виза", callback_data="visa_have")],
        [InlineKeyboardButton(text="❌ У меня нет визы", callback_data="visa_not_have")],
        [InlineKeyboardButton(text="🔄 Особый случай", callback_data="visa_special")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_travel")]
    ])


def get_baggage_keyboard(back_callback: str = "visa_back_step3") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="baggage_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="baggage_no")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)]
    ])


def get_ticket_received_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я получил билет", callback_data="ticket_received")],
        [InlineKeyboardButton(text="❌ Я не получил билет", callback_data="ticket_not_received")]
    ])


def get_ticket_problem_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проверить email", callback_data="check_email")],
        [InlineKeyboardButton(text="Проверить спам", callback_data="check_spam")],
        [InlineKeyboardButton(text="Отправить повторно", callback_data="resend_ticket")]
    ])


def get_navigation_keyboard(include_main: bool = True, include_back: bool = True) -> InlineKeyboardMarkup:
    """Универсальная клавиатура навигации"""
    builder = InlineKeyboardBuilder()

    if include_back:
        builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="form_back"))

    if include_main:
        builder.add(InlineKeyboardButton(text="🏠 Главная", callback_data="menu_main"))

    return builder.as_markup()


def get_form_navigation_keyboard(back_to: str) -> InlineKeyboardMarkup:
    """Навигация для форм"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"back_to_{back_to}"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="menu_main")
    )

    return builder.as_markup()


# Добавить в файл keyboards.py:

def get_profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для редактирования профиля"""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Имя", callback_data="profile_edit_name"),
        InlineKeyboardButton(text="✏️ Должность", callback_data="profile_edit_position")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Компания", callback_data="profile_edit_company"),
        InlineKeyboardButton(text="🌐 Язык", callback_data="profile_edit_language")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к профилю", callback_data="menu_profile")
    )
    return builder.as_markup()


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к профилю", callback_data="menu_profile")
    )
    return builder.as_markup()