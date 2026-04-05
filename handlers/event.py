import re

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_back_next_keyboard, get_event_menu_keyboard
from database import db
import logging
import os
from handlers.managers_chat import send_question_to_manager
from utility.lang_utils import t, get_user_lang

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


class EventTicketForm(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_country = State()


async def get_selected_conference_text(user_id: int) -> str:
    """Получить текст с выбранной конференцией"""
    selected_conf = await db.get_selected_conference(user_id)
    if selected_conf:
        return f"\n\n📌 *Текущая конференция:* {selected_conf}"
    return ""


@router.callback_query(F.data == "event_rules_pdf")
async def show_event_rules_pdf(callback: CallbackQuery):
    """Отправка PDF с правилами поведения в зависимости от компании"""
    username = callback.from_user.username

    # Получаем компанию пользователя
    user_data = await db.get_user_data(callback.from_user.id)
    company = user_data.get('company', '') if user_data else ''

    # Пути к PDF файлам правил
    base_path = './instructions/rules/'

    # Сначала ищем файл для конкретной компании
    company_file = f'{company} - Conference Rules.pdf' if company else None
    default_file = 'Conference Rules.pdf'

    file_to_send = None

    # Проверяем файл компании
    if company_file:
        file_path = os.path.join(base_path, company_file)
        if os.path.exists(file_path):
            file_to_send = FSInputFile(file_path)

    # Если нет файла компании, используем общий
    if not file_to_send:
        default_path = os.path.join(base_path, default_file)
        if os.path.exists(default_path):
            file_to_send = FSInputFile(default_path)

    # Если файлов нет, отправляем текстовую версию
    if not file_to_send:
        await callback.message.edit_text(
            "📋 **Правила поведения на конференции**\n\n"
            "1. Будьте вежливы и уважительны к другим участникам\n"
            "2. Соблюдайте дресс-код: Business casual\n"
            "3. Не опаздывайте на сессии и встречи\n"
            "4. Выключайте звук мобильных устройств во время выступлений\n"
            "5. Соблюдайте чистоту в конференц-зонах\n"
            "6. Фото и видео съемка разрешена только с согласия участников\n"
            "7. Запрещено распространение материалов без разрешения\n\n"
            "Нарушение правил может привести к ограничению доступа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я ознакомился(ась)", callback_data="accept_rules")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_event")]
            ]),
            parse_mode="Markdown"
        )
        return

    # Клавиатура для подтверждения после PDF
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я ознакомился(ась) с правилами", callback_data="accept_rules")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_event")]
    ])

    # Отправляем PDF
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer_document(
        document=file_to_send,
        caption="📋 **Правила поведения на конференции**\n\nПожалуйста, ознакомьтесь с правилами.",
        reply_markup=keyboard,
        parse_mode="Markdown"
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
        user_id = int(callback.from_user.id)
        await callback.answer("✅ Правила приняты")

        # Пробуем отредактировать, если не получается - отправляем новое сообщение
        try:
            await callback.message.edit_text(
                "✅ Правила приняты\n\nМеню EVENT:",
                reply_markup=await get_event_menu_keyboard(user_id)
            )
        except:
            # Если редактирование не удалось, отправляем новое сообщение
            await callback.message.answer(
                "✅ Правила приняты\n\nМеню EVENT:",
                reply_markup=await get_event_menu_keyboard(user_id)
            )

    except Exception as e:
        logger.error(f"Ошибка в accept_rules: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "event_info")
async def show_event_info(callback: CallbackQuery):
    """Общая информация о мероприятии - из БД"""
    username = callback.from_user.username

    # Получаем конференции пользователя
    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            "ℹ️ Информация о конференции не найдена.\n\n"
            "Пожалуйста, обратитесь к организаторам.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад в EVENT", callback_data="menu_event")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")]
            ])
        )
        return

    # Берем первую конференцию (или можно показать список)
    conference = conferences[0]

    # Формируем текст из данных БД
    info_text = (
        f"ℹ️ Общая информация о конференции:\n\n"
        f"📅 Название: {conference.get('conference_name', 'Не указано')}\n"
        f"📍 Город: {conference.get('city', 'Не указано')}\n"
        f"📅 Даты конференции: {conference.get('conference_start_date', 'Не указано')} - {conference.get('conference_end_date', 'Не указано')}\n"
        f"✈️ Даты поездки: {conference.get('trip_start_date', 'Не указано')} - {conference.get('trip_end_date', 'Не указано')}\n"
        f"🤖 Бот конференции: {conference.get('bot_link', 'Не указан')}\n\n"
        f"ℹ️ Дополнительная информация: {conference.get('additional_info', 'Уточняйте у организаторов')}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в EVENT", callback_data="menu_event")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")]
    ])

    await callback.message.edit_text(info_text, reply_markup=keyboard)


@router.callback_query(F.data == "event_ticket")
async def start_ticket_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы заказа билета"""
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_full_name)

    step_text = await t(user_id, 'ticket_step', step=1, total=6)
    question_text = await t(user_id, 'ticket_full_name')

    await callback.message.edit_text(
        f"🎫 **{await t(user_id, 'event_ticket')}**\n\n{step_text}\n\n{question_text}",
        reply_markup=await get_back_next_keyboard(back_to="menu_event", next_disabled=True, user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_full_name)
async def process_ticket_full_name(message: Message, state: FSMContext):
    """Шаг 1: ФИО"""
    if len(message.text.strip()) < 3:
        await message.answer("❌ Пожалуйста, введите корректные имя и фамилию (минимум 3 символа):")
        return

    await state.update_data(full_name=message.text.strip())
    await state.set_state(EventTicketForm.waiting_for_position)

    await message.answer(
        await t(message.from_user.id, 'ticket_step', step=2, total=6) + "\n\n" + await t(message.from_user.id,
                                                                                         'ticket_position'),
        reply_markup=await get_back_next_keyboard(back_to="event_ticket", user_id=message.from_user.id)
    )


@router.message(EventTicketForm.waiting_for_position)
async def process_ticket_position(message: Message, state: FSMContext):
    """Шаг 2: Должность"""
    if len(message.text.strip()) < 2:
        await message.answer("❌ Пожалуйста, введите корректную должность:")
        return

    await state.update_data(position=message.text.strip())
    await state.set_state(EventTicketForm.waiting_for_company)

    await message.answer(
        "Шаг 3 из 6\n\n"
        "🏢 Название партнерской программы/компании:",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step2")
    )


@router.message(EventTicketForm.waiting_for_company)
async def process_ticket_company(message: Message, state: FSMContext):
    """Шаг 3: Компания"""
    if len(message.text.strip()) < 2:
        await message.answer("❌ Пожалуйста, введите название компании:")
        return

    await state.update_data(company=message.text.strip())
    await state.set_state(EventTicketForm.waiting_for_email)

    await message.answer(
        "Шаг 4 из 6\n\n"
        "📧 Ваш email (на него придет билет):",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step3")
    )


@router.message(EventTicketForm.waiting_for_email)
async def process_ticket_email(message: Message, state: FSMContext):
    """Шаг 4: Email с валидацией"""
    email = message.text.strip()

    # Простая валидация email
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        await message.answer("❌ Пожалуйста, введите корректный email (пример: name@domain.com):")
        return

    await state.update_data(email=email)
    await state.set_state(EventTicketForm.waiting_for_phone)

    await message.answer(
        "Шаг 5 из 6\n\n"
        "📱 Ваш номер телефона (для связи):",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step4")
    )


@router.message(EventTicketForm.waiting_for_phone)
async def process_ticket_phone(message: Message, state: FSMContext):
    """Шаг 5: Телефон"""
    phone = message.text.strip()

    # Простая валидация телефона
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 10:
        await message.answer("❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр):")
        return

    await state.update_data(phone=phone)
    await state.set_state(EventTicketForm.waiting_for_country)

    # Клавиатура выбора страны
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Россия", callback_data="ticket_country_russia")],
        [InlineKeyboardButton(text="🇦🇪 ОАЭ", callback_data="ticket_country_uae")],
        [InlineKeyboardButton(text="🇰🇿 Казахстан", callback_data="ticket_country_kazakhstan")],
        [InlineKeyboardButton(text="🇺🇿 Узбекистан", callback_data="ticket_country_uzbekistan")],
        [InlineKeyboardButton(text="🇨🇳 Китай", callback_data="ticket_country_china")],
        [InlineKeyboardButton(text="🇮🇳 Индия", callback_data="ticket_country_india")],
        [InlineKeyboardButton(text="🌍 Другая", callback_data="ticket_country_other")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="ticket_back_step5")]
    ])

    await message.answer(
        "Шаг 6 из 6\n\n"
        "🌍 Какую страну указывать для регистрации билета?\n\n"
        "Выберите из списка:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("ticket_country_"), EventTicketForm.waiting_for_country)
async def process_ticket_country(callback: CallbackQuery, state: FSMContext):
    """Шаг 6: Выбор страны и сохранение заявки"""
    country_map = {
        "russia": "Россия",
        "uae": "ОАЭ (Объединенные Арабские Эмираты)",
        "kazakhstan": "Казахстан",
        "uzbekistan": "Узбекистан",
        "china": "Китай",
        "india": "Индия",
        "other": "Другая"
    }

    country_key = callback.data.replace("ticket_country_", "")
    country = country_map.get(country_key, country_key)

    if country_key == "other":
        await state.update_data(waiting_for_custom_country=True)
        await callback.message.edit_text(
            "Шаг 6 из 6\n\n"
            "🌍 Пожалуйста, напишите название вашей страны:"
        )
        return

    await state.update_data(country=country)
    await save_ticket_request(callback, state)


@router.message(EventTicketForm.waiting_for_country)
async def process_ticket_custom_country(message: Message, state: FSMContext):
    """Обработка ручного ввода страны"""
    data = await state.get_data()
    if data.get('waiting_for_custom_country'):
        await state.update_data(country=message.text.strip(), waiting_for_custom_country=False)
        await save_ticket_request(message, state)
    else:
        await message.answer("Пожалуйста, выберите страну из кнопок выше.")


async def save_ticket_request(update, state: FSMContext):
    """Сохранение заявки на билет"""
    data = await state.get_data()

    if isinstance(update, Message):
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update
    else:
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update.message

    ticket_data = {
        'username': username,
        'user_id': user_id,
        'full_name': data.get('full_name', ''),
        'position': data.get('position', ''),
        'company': data.get('company', ''),
        'email': data.get('email', ''),
        'phone': data.get('phone', ''),
        'country': data.get('country', '')
    }

    # Сохраняем в БД
    success = await db.save_ticket_request(ticket_data)

    if success:
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="ticket_request_submitted",
            details={"data": ticket_data}
        )

        await message_obj.answer(
            await t(message_obj.from_user.id, 'ticket_success', email=data.get('email')),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(message_obj.from_user.id, 'back'), callback_data="menu_event")],
                [InlineKeyboardButton(text=await t(message_obj.from_user.id, 'main_menu'), callback_data="menu_main")]
            ])
        )
    else:
        await message_obj.answer(
            "❌ **Ошибка при отправке заявки**\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

    await state.clear()


# Обработчики кнопок "Назад" для формы билета
@router.callback_query(F.data == "ticket_back_step2")
async def ticket_back_to_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EventTicketForm.waiting_for_full_name)
    await callback.message.edit_text(
        "Шаг 1 из 6\n\n✍️ Укажите ваши имя и фамилию (как в паспорте):",
        reply_markup=await get_back_next_keyboard(back_to="menu_event", next_disabled=True)
    )


@router.callback_query(F.data == "ticket_back_step3")
async def ticket_back_to_position(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EventTicketForm.waiting_for_position)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Шаг 2 из 6\n\n💼 Ваша должность:\n(текущее: {data.get('position', 'не указано')})",
        reply_markup=await get_back_next_keyboard(back_to="event_ticket")
    )


@router.callback_query(F.data == "ticket_back_step4")
async def ticket_back_to_company(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EventTicketForm.waiting_for_company)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Шаг 3 из 6\n\n🏢 Название партнерской программы:\n(текущее: {data.get('company', 'не указано')})",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step2")
    )


@router.callback_query(F.data == "ticket_back_step5")
async def ticket_back_to_email(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EventTicketForm.waiting_for_email)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Шаг 4 из 6\n\n📧 Ваш email:\n(текущий: {data.get('email', 'не указан')})",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step3")
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
    user_id = callback.from_user.id
    await state.set_state(EventCertificateForm.waiting_for_name)

    await callback.message.edit_text(
        f"{await t(user_id, 'event_certificate_form_title')}\n\n"
        f"1/6 {await t(user_id, 'event_certificate_step1')}",
        reply_markup=await get_back_next_keyboard(back_to="menu_event", next_disabled=True, user_id=user_id)
    )


@router.message(EventCertificateForm.waiting_for_name)
async def process_certificate_name(message: Message, state: FSMContext):
    """Обработка ФИО для справки"""
    await state.update_data(full_name=message.text)
    await state.set_state(EventCertificateForm.waiting_for_position)
    await message.answer(
        "Шаг 2 из 6\nУкажите должность:",
        reply_markup=await get_back_next_keyboard(back_to="certificate_step1")
    )


@router.message(EventCertificateForm.waiting_for_position)
async def process_certificate_position(message: Message, state: FSMContext):
    """Обработка должности"""
    await state.update_data(position=message.text)
    await state.set_state(EventCertificateForm.waiting_for_company)
    await message.answer(
        "Шаг 3 из 6\nНазвание компании:",
        reply_markup=await get_back_next_keyboard(back_to="certificate_step2")
    )


@router.message(EventCertificateForm.waiting_for_company)
async def process_certificate_company(message: Message, state: FSMContext):
    """Обработка компании"""
    await state.update_data(company=message.text)
    await state.set_state(EventCertificateForm.waiting_for_company_legal)
    await message.answer(
        "Шаг 4 из 6\nЮридические данные компании (ИНН, ОГРН и т.д.):",
        reply_markup=await get_back_next_keyboard(back_to="certificate_step3")
    )


@router.message(EventCertificateForm.waiting_for_company_legal)
async def process_certificate_legal(message: Message, state: FSMContext):
    """Обработка юр. данных"""
    await state.update_data(company_legal=message.text)
    await state.set_state(EventCertificateForm.waiting_for_addressee)
    await message.answer(
        "Шаг 5 из 6\nКому адресовать справку? (ФИО, должность):",
        reply_markup=await get_back_next_keyboard(back_to="certificate_step4")
    )


@router.message(EventCertificateForm.waiting_for_addressee)
async def process_certificate_addressee(message: Message, state: FSMContext):
    """Обработка адресата"""
    await state.update_data(addressee=message.text)
    await state.set_state(EventCertificateForm.waiting_for_dates)
    await message.answer(
        "Шаг 6 из 6\nДаты участия (например: 15.11.2024 - 17.11.2024):",
        reply_markup=await get_back_next_keyboard(back_to="certificate_step5")
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
    """Вопрос EVENT без категорий - сразу ввод текста"""
    await state.set_state(EventQuestionForm.waiting_for_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_event")]
    ])

    await callback.message.edit_text(
        "❓ **Вопрос к EVENT-менеджеру**\n\n"
        "Напишите ваш вопрос (максимум 500 символов):\n\n",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(EventQuestionForm.waiting_for_question, F.text.len() <= 500)
async def process_event_question(message: Message, state: FSMContext):
    """Обработка вопроса EVENT (без категорий)"""
    question_text = message.text

    event_question_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'category': 'general',
        'question': question_text
    }

    if await db.save_event_question(event_question_data):
        await send_question_to_manager(
            bot=message.bot,
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
        [InlineKeyboardButton(text="◀️ Назад в EVENT", callback_data="menu_event")]
    ])

    await message.answer(
        "✅ **Вопрос отправлен!**\n\n"
        "Благодарим за вопрос. Наша EVENT-команда свяжется с вами в ближайшее время.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data == "event_booth")
async def show_booth_info(callback: CallbackQuery):
    """Показать информацию о стенде"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в EVENT", callback_data="menu_event"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="menu_main")
    )

    text = (
        "ℹ️ Информация о стенде\n\n"
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.message(EventQuestionForm.waiting_for_question, F.text.len() > 500)
async def process_event_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    await message.answer("❌ Вопрос слишком длинный. Максимум 500 символов.")