import re
import os
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_back_next_keyboard, get_event_menu_keyboard
from database import db
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
    waiting_for_question = State()


class EventTicketForm(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_country = State()


# ============================================
# ПРАВИЛА КОНФЕРЕНЦИИ
# ============================================

@router.callback_query(F.data == "event_rules_pdf")
async def show_event_rules_pdf(callback: CallbackQuery):
    """Отправка PDF с правилами поведения в зависимости от компании"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Получаем компанию пользователя
    user_data = await db.get_user_data(user_id)
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
            await t(user_id, 'rules_text'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'accept_rules'), callback_data="accept_rules")],
                [InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event")]
            ]),
            parse_mode="Markdown"
        )
        return

    # Клавиатура для подтверждения после PDF
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'accept_rules'), callback_data="accept_rules")],
        [InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event")]
    ])

    # Отправляем PDF
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer_document(
        document=file_to_send,
        caption=await t(user_id, 'rules_pdf_caption'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "accept_rules")
async def accept_rules(callback: CallbackQuery):
    """Логирование согласия с правилами"""
    user_id = callback.from_user.id
    try:
        await db.log_user_action(
            user_id=user_id,
            username=callback.from_user.username,
            action="rules_accepted",
            details={"version": "1.0"}
        )
        await callback.answer(await t(user_id, 'rules_accepted'))

        # Пробуем отредактировать, если не получается - отправляем новое сообщение
        try:
            await callback.message.edit_text(
                f"{await t(user_id, 'rules_accepted')}\n\n{await t(user_id, 'event_title')}:",
                reply_markup=await get_event_menu_keyboard(user_id)
            )
        except:
            await callback.message.answer(
                f"{await t(user_id, 'rules_accepted')}\n\n{await t(user_id, 'event_title')}:",
                reply_markup=await get_event_menu_keyboard(user_id)
            )

    except Exception as e:
        logger.error(f"Error in accept_rules: {e}")
        await callback.answer("❌ Error occurred", show_alert=True)


# ============================================
# ИНФОРМАЦИЯ О КОНФЕРЕНЦИИ
# ============================================

@router.callback_query(F.data == "event_info")
async def show_event_info(callback: CallbackQuery):
    """Общая информация о мероприятии - из БД"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Получаем конференции пользователя
    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            await t(user_id, 'no_conference_info'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event")],
                [InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")]
            ])
        )
        return

    # Берем первую конференцию (или можно показать список)
    conference = conferences[0]

    # Формируем текст из данных БД
    info_text = (
        f"{await t(user_id, 'conference_info_title')}\n\n"
        f"<b>{await t(user_id, 'conference_name')}:</b> {conference.get('conference_name', await t(user_id, 'not_specified_info'))}\n"
        f"<b>{await t(user_id, 'conference_city')}:</b> {conference.get('city', await t(user_id, 'not_specified_info'))}\n"
        f"<b>{await t(user_id, 'conference_dates')}:</b> {conference.get('conference_start_date', await t(user_id, 'not_specified_info'))} - {conference.get('conference_end_date', await t(user_id, 'not_specified_info'))}\n"
        f"<b>{await t(user_id, 'trip_dates')}:</b> {conference.get('trip_start_date', await t(user_id, 'not_specified_info'))} - {conference.get('trip_end_date', await t(user_id, 'not_specified_info'))}\n"
        f"<b>{await t(user_id, 'bot_link')}:</b> {conference.get('bot_link', await t(user_id, 'not_specified_info'))}\n\n"
        f"<b>{await t(user_id, 'additional_info')}:</b> {conference.get('additional_info', await t(user_id, 'not_specified_info'))}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event")],
        [InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")]
    ])

    await callback.message.edit_text(info_text, reply_markup=keyboard, parse_mode="HTML")


# ============================================
# ФОРМА ЗАКАЗА БИЛЕТА
# ============================================

@router.callback_query(F.data == "event_ticket")
async def start_ticket_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы заказа билета"""
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_full_name)

    step_text = await t(user_id, 'ticket_step', step=1, total=6)
    question_text = await t(user_id, 'ticket_full_name')
    start_event_text = await t(user_id, 'start_event_text')

    await callback.message.edit_text(
        f"{await t(user_id, 'event_ticket')}\n\n{start_event_text}\n{step_text}\n\n{question_text}",
        reply_markup=await get_back_next_keyboard(back_to="menu_event", next_disabled=True, user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_full_name)
async def process_ticket_full_name(message: Message, state: FSMContext):
    """Шаг 1: ФИО"""
    user_id = message.from_user.id
    if len(message.text.strip()) < 3:
        await message.answer(await t(user_id, 'error_invalid_name'))
        return

    await state.update_data(full_name=message.text.strip())
    await state.set_state(EventTicketForm.waiting_for_position)

    await message.answer(
        await t(user_id, 'ticket_step', step=2, total=6) + "\n\n" + await t(user_id, 'ticket_position'),
        reply_markup=await get_back_next_keyboard(back_to="event_ticket", user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_position)
async def process_ticket_position(message: Message, state: FSMContext):
    """Шаг 2: Должность"""
    user_id = message.from_user.id
    if len(message.text.strip()) < 2:
        await message.answer(await t(user_id, 'error_invalid_position'))
        return

    await state.update_data(position=message.text.strip())
    await state.set_state(EventTicketForm.waiting_for_company)

    await message.answer(
        await t(user_id, 'ticket_step', step=3, total=6) + "\n\n" + await t(user_id, 'ticket_company'),
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step2", user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_company)
async def process_ticket_company(message: Message, state: FSMContext):
    """Шаг 3: Компания"""
    user_id = message.from_user.id
    if len(message.text.strip()) < 2:
        await message.answer(await t(user_id, 'error_invalid_company'))
        return

    await state.update_data(company=message.text.strip())
    await state.set_state(EventTicketForm.waiting_for_email)

    await message.answer(
        await t(user_id, 'ticket_step', step=4, total=6) + "\n\n" + await t(user_id, 'ticket_email'),
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step3", user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_email)
async def process_ticket_email(message: Message, state: FSMContext):
    """Шаг 4: Email с валидацией"""
    user_id = message.from_user.id
    email = message.text.strip()

    # Простая валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        await message.answer(await t(user_id, 'error_invalid_email'))
        return

    await state.update_data(email=email)
    await state.set_state(EventTicketForm.waiting_for_phone)

    await message.answer(
        await t(user_id, 'ticket_step', step=5, total=6) + "\n\n" + await t(user_id, 'ticket_phone'),
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step4", user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_phone)
async def process_ticket_phone(message: Message, state: FSMContext):
    """Шаг 5: Телефон"""
    user_id = message.from_user.id
    phone = message.text.strip()

    # Простая валидация телефона
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 4:
        await message.answer(await t(user_id, 'error_invalid_phone'))
        return

    await state.update_data(phone=phone)
    await state.set_state(EventTicketForm.waiting_for_country)

    await message.answer(
        await t(user_id, 'ticket_step', step=6, total=6) + "\n\n" + await t(user_id, 'ticket_country_prompt'),
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step5", user_id=user_id)
    )


@router.message(EventTicketForm.waiting_for_country)
async def process_ticket_country(message: Message, state: FSMContext):
    """Шаг 6: Страна (текстовый ввод)"""
    user_id = message.from_user.id
    country = message.text.strip()

    if len(country) < 2:
        await message.answer(await t(user_id, 'error_invalid_country'))
        return

    await state.update_data(country=country)
    await save_ticket_request(message, state)


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
            await t(user_id, 'ticket_success', email=data.get('email')),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event")],
                [InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")]
            ])
        )
    else:
        await message_obj.answer(
            await t(user_id, 'error_saving_request')
        )

    await state.clear()


# Обработчики кнопок "Назад" для формы билета
@router.callback_query(F.data == "ticket_back_step2")
async def ticket_back_to_name(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_full_name)
    await callback.message.edit_text(
        await t(user_id, 'ticket_step', step=1, total=6) + "\n\n" + await t(user_id, 'ticket_full_name'),
        reply_markup=await get_back_next_keyboard(back_to="menu_event", next_disabled=True, user_id=user_id)
    )


@router.callback_query(F.data == "ticket_back_step3")
async def ticket_back_to_position(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_position)
    data = await state.get_data()
    current = data.get('position', await t(user_id, 'not_specified'))
    await callback.message.edit_text(
        await t(user_id, 'ticket_step', step=2, total=6) + "\n\n" + await t(user_id, 'ticket_position') + f"\n(текущее: {current})",
        reply_markup=await get_back_next_keyboard(back_to="event_ticket", user_id=user_id)
    )


@router.callback_query(F.data == "ticket_back_step4")
async def ticket_back_to_company(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_company)
    data = await state.get_data()
    current = data.get('company', await t(user_id, 'not_specified'))
    await callback.message.edit_text(
        await t(user_id, 'ticket_step', step=3, total=6) + "\n\n" + await t(user_id, 'ticket_company') + f"\n(текущее: {current})",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step2", user_id=user_id)
    )


@router.callback_query(F.data == "ticket_back_step5")
async def ticket_back_to_email(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_email)
    data = await state.get_data()
    current = data.get('email', await t(user_id, 'not_specified'))
    await callback.message.edit_text(
        await t(user_id, 'ticket_step', step=4, total=6) + "\n\n" + await t(user_id, 'ticket_email') + f"\n(текущий: {current})",
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step3", user_id=user_id)
    )


@router.callback_query(F.data == "ticket_back_step6")
async def ticket_back_to_phone(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(EventTicketForm.waiting_for_phone)
    await callback.message.edit_text(
        await t(user_id, 'ticket_step', step=5, total=6) + "\n\n" + await t(user_id, 'ticket_phone'),
        reply_markup=await get_back_next_keyboard(back_to="ticket_back_step4", user_id=user_id)
    )


# ============================================
# ВОПРОС К EVENT-МЕНЕДЖЕРУ
# ============================================

@router.callback_query(F.data == "event_question")
async def start_event_question(callback: CallbackQuery, state: FSMContext):
    """Вопрос EVENT без категорий - сразу ввод текста"""
    user_id = callback.from_user.id
    await state.set_state(EventQuestionForm.waiting_for_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'cancel_button'), callback_data="menu_event")]
    ])

    await callback.message.edit_text(
        f"*{await t(user_id, 'event_question')}*\n\n"
        f"{await t(user_id, 'event_question_prompt')}\n\n",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(EventQuestionForm.waiting_for_question, F.text.len() <= 500)
async def process_event_question(message: Message, state: FSMContext):
    """Обработка вопроса EVENT"""
    user_id = message.from_user.id
    question_text = message.text

    event_question_data = {
        'username': message.from_user.username,
        'user_id': user_id,
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
            user_id=user_id,
            username=message.from_user.username,
            action="event_question_submitted",
            details={"data": event_question_data}
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event")]
    ])

    await message.answer(
        await t(user_id, 'question_sent'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.clear()


@router.message(EventQuestionForm.waiting_for_question, F.text.len() > 500)
async def process_event_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    user_id = message.from_user.id
    await message.answer(await t(user_id, 'question_too_long'))


# ============================================
# ИНФОРМАЦИЯ О СТЕНДЕ
# ============================================

@router.callback_query(F.data == "event_booth")
async def show_booth_info(callback: CallbackQuery):
    """Показать информацию о стенде для конкретной компании и конференции"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Получаем компанию пользователя
    user_data = await db.get_user_data(user_id)
    company = user_data.get('company')

    # Получаем выбранную конференцию
    conference = await db.get_selected_conference(user_id)
    if not conference:
        confs = await db.get_user_active_conferences(username)
        if confs:
            conference = confs[0].get('conference_name')

    # Запрашиваем информацию о стенде
    stand_info = None
    if company and conference:
        stand_info = await db.get_event_stand(company, conference)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back_to_event'), callback_data="menu_event"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    # Используем HTML разметку вместо Markdown для защиты от спецсимволов в названиях
    if stand_info:
        text = (
            f"ℹ️ <b>Информация о вашем стенде на {conference}</b>\n\n"
            f"🏢 <b>Компания:</b> {company}\n"
            f"🎨 <b>Стиль стенда:</b> {stand_info.get('stand_style', 'Не указан')}\n"
            f"🔢 <b>Номер стенда:</b> {stand_info.get('stand_number', 'Не указан')}\n"
            f"🕐 <b>Время работы:</b> {stand_info.get('working_hours', 'Не указано')}\n"
            f"👔 <b>Дресс-код:</b> {stand_info.get('dress_code', 'Не указан')}"
        )
    else:
        text = f"К сожалению, у вашей компании (<b>{company or 'не указана'}</b>) нет стенда на конференцию «<b>{conference or 'не выбрана'}</b>»."

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")