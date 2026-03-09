from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_back_next_keyboard, get_event_menu_keyboard
from database import db
import logging
import os
from handlers.managers_chat import send_question_to_manager

EVENT_MANAGER_CHAT_ID = int(os.getenv("TG_EVENT_MANAGER_CHAT_ID", 0))


router = Router()
logger = logging.getLogger(__name__)

class EventCertificateForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_company_legal = State()
    waiting_for_addressee = State()
    waiting_for_dates = State()


class EventQuestionForm(StatesGroup):
    waiting_for_category = State()
    waiting_for_question = State()


@router.callback_query(F.data == "event_rules")
async def show_event_rules(callback: CallbackQuery):
    """Правила поведения с согласием"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я прочитал и принимаю", callback_data="accept_rules")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_event")]
    ])

    await callback.message.edit_text(
        "📋 Правила поведения на конференции:\n\n"
        "1. Будьте вежливы\n"
        "2. Соблюдайте дресс-код\n"
        "3. ...",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "accept_rules")
async def accept_rules(callback: CallbackQuery):
    """Логирование согласия с правилами"""
    try:
        await db.log_user_action(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            action="rules_accepted",
            details={"version": "1.0"}
        )

        await callback.answer("✅ Правила приняты")

        # Пробуем отредактировать, если не получается - отправляем новое сообщение
        try:
            await callback.message.edit_text(
                "✅ Правила приняты\n\nМеню EVENT:",
                reply_markup=get_event_menu_keyboard()
            )
        except:
            # Если редактирование не удалось, отправляем новое сообщение
            await callback.message.answer(
                "✅ Правила приняты\n\nМеню EVENT:",
                reply_markup=get_event_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка в accept_rules: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "event_info")
async def show_event_info(callback: CallbackQuery):
    """Общая информация о мероприятии"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Создаем клавиатуру с кнопками навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в EVENT", callback_data="menu_event")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        "ℹ️ Общая информация:\n\n"
        "📅 Дата мероприятия: 15-17 ноября 2024\n"
        "⏰ Время: 9:00 - 18:00\n"
        "📍 Локация: Конференц-центр, Москва\n"
        "👔 Дресс-код: Business casual\n"
        "📶 Wi-Fi: Conference2024 / pass1234\n"
        "🚗 Схема проезда: [ссылка]\n"
        "📞 Контакты на день ивента: +7 (999) 123-45-67",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "event_ticket")
async def show_ticket_info(callback: CallbackQuery):
    """Информация о билете"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в EVENT", callback_data="menu_event")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        "🎫 Твой билет на конференцию\n\n"
        "Ты получишь билет на email: user@example.com\n\n"
        "После отправки билета администратором, вы получите уведомление.",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "ticket_sent")
async def ticket_sent_handler(callback: CallbackQuery):
    """Администратор отправил билет"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я получил билет", callback_data="ticket_received")],
        [InlineKeyboardButton(text="❌ Я не получил билет", callback_data="ticket_not_received")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_event")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")]
    ])
    await callback.message.edit_text(
        "🎫 Билет отправлен на ваш email.\n"
        "Пожалуйста, подтвердите получение:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "ticket_not_received")
async def ticket_not_received_handler(callback: CallbackQuery, state: FSMContext):
    """Форма для проблем с получением билета"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проверить email", callback_data="check_email")],
        [InlineKeyboardButton(text="Проверить спам", callback_data="check_spam")],
        [InlineKeyboardButton(text="Отправить повторно", callback_data="resend_ticket")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="event_ticket")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")]
    ])
    await callback.message.edit_text(
        "❌ Вы не получили билет?\n\n"
        "1. Проверьте правильность email\n"
        "2. Проверьте папку 'Спам'\n"
        "3. Запросите повторную отправку",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "event_certificate")
async def start_certificate_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы справки-вызова"""
    await state.set_state(EventCertificateForm.waiting_for_name)
    await callback.message.edit_text(
        "📄 Справка-вызов\n\nШаг 1 из 6\nУкажите ФИО:",
        reply_markup=get_back_next_keyboard(back_to="menu_event", next_disabled=True)
    )


@router.message(EventCertificateForm.waiting_for_name)
async def process_certificate_name(message: Message, state: FSMContext):
    """Обработка ФИО для справки"""
    await state.update_data(full_name=message.text)
    await state.set_state(EventCertificateForm.waiting_for_position)
    await message.answer(
        "Шаг 2 из 6\nУкажите должность:",
        reply_markup=get_back_next_keyboard(back_to="certificate_step1")
    )


@router.message(EventCertificateForm.waiting_for_position)
async def process_certificate_position(message: Message, state: FSMContext):
    """Обработка должности"""
    await state.update_data(position=message.text)
    await state.set_state(EventCertificateForm.waiting_for_company)
    await message.answer(
        "Шаг 3 из 6\nНазвание компании:",
        reply_markup=get_back_next_keyboard(back_to="certificate_step2")
    )


@router.message(EventCertificateForm.waiting_for_company)
async def process_certificate_company(message: Message, state: FSMContext):
    """Обработка компании"""
    await state.update_data(company=message.text)
    await state.set_state(EventCertificateForm.waiting_for_company_legal)
    await message.answer(
        "Шаг 4 из 6\nЮридические данные компании (ИНН, ОГРН и т.д.):",
        reply_markup=get_back_next_keyboard(back_to="certificate_step3")
    )


@router.message(EventCertificateForm.waiting_for_company_legal)
async def process_certificate_legal(message: Message, state: FSMContext):
    """Обработка юр. данных"""
    await state.update_data(company_legal=message.text)
    await state.set_state(EventCertificateForm.waiting_for_addressee)
    await message.answer(
        "Шаг 5 из 6\nКому адресовать справку? (ФИО, должность):",
        reply_markup=get_back_next_keyboard(back_to="certificate_step4")
    )


@router.message(EventCertificateForm.waiting_for_addressee)
async def process_certificate_addressee(message: Message, state: FSMContext):
    """Обработка адресата"""
    await state.update_data(addressee=message.text)
    await state.set_state(EventCertificateForm.waiting_for_dates)
    await message.answer(
        "Шаг 6 из 6\nДаты участия (например: 15.11.2024 - 17.11.2024):",
        reply_markup=get_back_next_keyboard(back_to="certificate_step5")
    )


@router.message(EventCertificateForm.waiting_for_dates)
async def process_certificate_dates(message: Message, state: FSMContext):
    """Обработка дат и сохранение заявки"""
    await state.update_data(dates=message.text)
    data = await state.get_data()

    # Сохранение в БД
    certificate_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'full_name': data.get('full_name', ''),
        'position': data.get('position', ''),
        'company': data.get('company', ''),
        'company_legal': data.get('company_legal', ''),
        'addressee': data.get('addressee', ''),
        'dates': data.get('dates', '')
    }

    if await db.save_certificate_request(certificate_data):
        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="certificate_request_submitted",
            details={"data": certificate_data}
        )

    await message.answer(
        "✅ Заявка на справку-вызов отправлена!\n\n"
        "Благодарим за ответ, наша команда получила твой запрос. "
        "Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи."
    )
    await state.clear()


@router.callback_query(F.data == "event_question")
async def start_event_question(callback: CallbackQuery, state: FSMContext):
    """Вопрос к EVENT-менеджеру"""
    await state.set_state(EventQuestionForm.waiting_for_category)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Правила поведения", callback_data="cat_rules")],
        [InlineKeyboardButton(text="Билеты", callback_data="cat_tickets")],
        [InlineKeyboardButton(text="Справка-вызов", callback_data="cat_certificate")],
        [InlineKeyboardButton(text="Локация/проезд", callback_data="cat_location")],
        [InlineKeyboardButton(text="Другое", callback_data="cat_other")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_event")]
    ])

    await callback.message.edit_text(
        "❓ Вопрос к EVENT-менеджеру\n\nВыберите категорию вопроса:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("cat_"), EventQuestionForm.waiting_for_category)
async def process_event_question_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории вопроса"""
    category = callback.data.replace("cat_", "")
    await state.update_data(category=category)
    await state.set_state(EventQuestionForm.waiting_for_question)

    await callback.message.edit_text(
        f"📝 Категория: {category}\n\n"
        "Введите ваш вопрос (максимум 500 символов):",
        reply_markup=get_back_next_keyboard(back_to="event_question", next_disabled=True)
    )


@router.message(EventQuestionForm.waiting_for_question, F.text.len() <= 500)
async def process_event_question(message: Message, state: FSMContext):
    """Обработка вопроса"""
    question_text = message.text
    data = await state.get_data()

    event_question_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'category': data.get('category', ''),
        'question': question_text
    }

    # Сохраняем в БД
    if await db.save_event_question(event_question_data):
        # Отправляем в чат event-менеджера
        await send_question_to_manager(
            bot=message.bot,  # Используем message.bot
            manager_chat_id=EVENT_MANAGER_CHAT_ID,
            user_data=event_question_data,
            question_text=question_text,
            question_type="event"
        )

        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="event_question_submitted",
            details={"data": event_question_data}
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to EVENT Menu", callback_data="menu_event")]
    ])

    await message.answer(
        "✅ Question sent!\n\n"
        "Thank you for your question. Our EVENT team will contact you soon.",
        reply_markup=keyboard
    )
    await state.clear()

@router.message(EventQuestionForm.waiting_for_question, F.text.len() > 500)
async def process_event_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    await message.answer("❌ Вопрос слишком длинный. Максимум 500 символов.")