from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

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


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
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
    return builder.as_markup()


def get_pr_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎨 Баннер", callback_data="pr_banner"),
        InlineKeyboardButton(text="📇 Визитки", callback_data="pr_business_cards")
    )
    builder.row(
        InlineKeyboardButton(text="🍽 Партнерский ужин", callback_data="pr_dinner"),
        InlineKeyboardButton(text="❓ Вопрос PR", callback_data="pr_question")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="menu_main")
    )
    return builder.as_markup()


def get_event_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню EVENT с короткими названиями кнопок"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎫 Билет на конференцию", callback_data="event_ticket"),
        InlineKeyboardButton(text="ℹ️ О стенде", callback_data="event_booth")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ О конференции", callback_data="event_info"),
        InlineKeyboardButton(text="❓ Вопрос", callback_data="event_question")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")
    )

    return builder.as_markup()


# def get_travel_menu_keyboard() -> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     builder.row(
#         InlineKeyboardButton(text="🛂 Визовая поддержка", callback_data="travel_visa"),
#         InlineKeyboardButton(text="✈️ Билет на самолёт", callback_data="travel_flight")
#     )
#     builder.row(
#         InlineKeyboardButton(text="🏨 Отель", callback_data="travel_hotel"),
#         InlineKeyboardButton(text="💰 Суточные", callback_data="travel_per_diem")
#     )
#     builder.row(
#         InlineKeyboardButton(text="❓ Вопрос к тревел-менеджеру", callback_data="travel_question")
#     )
#     builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
#     return builder.as_markup()


def get_back_next_keyboard(back_to: str, next_disabled: bool = False, cancel: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if next_disabled:
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back_to))
    else:
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_to)
        )

    if cancel:
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_form"))

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
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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