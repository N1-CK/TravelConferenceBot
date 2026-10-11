import logging
import re
from uuid import uuid4
from datetime import datetime
from typing import Union
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.managers_chat import send_question_to_manager, get_manager_chat_id, send_request_notification_to_manager

from database import db
from utility.lang_utils import t


router = Router()
logger = logging.getLogger(__name__)


# ============================================
# СОСТОЯНИЯ
# ============================================

class TravelStates(StatesGroup):

    # Для Flight Request
    waiting_for_conference = State()
    waiting_for_visa_info = State()
    waiting_for_passport_consent = State()
    waiting_for_baggage = State()
    waiting_for_hotel_needed = State()
    waiting_for_flight_choice = State()

    # Для вопросов
    waiting_for_travel_question = State()

    # Для полной формы
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone = State()
    waiting_for_passport_number = State()
    waiting_for_birth_date = State()
    waiting_for_passport_country = State()
    waiting_for_issue_date = State()
    waiting_for_expiry_date = State()
    waiting_for_departure_from = State()
    waiting_for_return_to = State()

    # Для Daily allowance
    waiting_for_per_diem_payment_type = State()
    waiting_for_per_diem_card = State()
    waiting_for_per_diem_crypto_network = State()
    waiting_for_per_diem_crypto_address = State()
    waiting_for_per_diem_consent = State()


# ============================================
# КЛАВИАТУРЫ
# ============================================

async def get_form_back_keyboard(back_to: str, user_id: int = None) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для форм с локализацией"""
    builder = InlineKeyboardBuilder()

    back_text = await t(user_id, 'back') if user_id else '◀️ Назад'
    main_text = await t(user_id, 'main_menu') if user_id else '🏠 Главное меню'
    builder.row(
        InlineKeyboardButton(text=back_text, callback_data=back_to),
        InlineKeyboardButton(text=main_text, callback_data="menu_main")
    )
    return builder.as_markup()


# ============================================
# FLIGHT INFO (Информация о рейсах)
# ============================================

@router.callback_query(F.data == "travel_flight_info")
async def show_flight_info(callback: CallbackQuery):
    """Показать список конференций для информации о рейсах"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    if not username:
        await callback.message.edit_text(
            await t(user_id, 'error_no_username'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
            ])
        )
        return

    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            await t(user_id, 'error_no_conferences'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
            ])
        )
        return

    builder = InlineKeyboardBuilder()
    for conf in conferences:
        conf_name = conf.get('conference_name', '')
        safe_conf_name = conf_name.replace(' ', '_').replace('-', '_')
        display_text = f"📅 {conf_name}"
        if conf.get('city'):
            display_text += f" ({conf['city']})"
        builder.row(InlineKeyboardButton(
            text=display_text,
            callback_data=f"travel_conf_info_{safe_conf_name}"
        ))
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    await callback.message.edit_text(
        await t(user_id, 'select_conference_for_flight'),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("travel_conf_info_"))
async def show_conference_flights(callback: CallbackQuery):
    """Показать информацию о рейсах для выбранной конференции"""
    user_id = callback.from_user.id
    encoded_conf = callback.data.replace("travel_conf_info_", "")
    conference = encoded_conf.replace('_', ' ')
    username = callback.from_user.username

    flights = await db.get_flight_details_travel(username, conference)

    if not flights:
        text = await t(user_id, 'no_flights_found')
    else:
        text = ""
        for i, flight in enumerate(flights, 1):
            text += await t(user_id, 'flight_info_template',
                            fl_num=i,
                            flight_number=flight.get('flight_number', 'N/A'),
                            book_number=flight.get('book_number', 'N/A'),
                            departure_from=flight.get('departure_from', 'N/A'),
                            arrival_city=flight.get('arrival_city', 'N/A'),
                            departure_date=flight.get('departure_date', 'N/A'),
                            departure_time=flight.get('departure_time', 'N/A'),
                            arrival_time=flight.get('arrival_time', 'N/A'),
                            airline=flight.get('airline', 'N/A'),
                            carry_luggage=flight.get('carry_luggage', 'N/A'),
                            luggage=flight.get('luggage', 'N/A')
                            ) + "\n\n"

        text += "\n" + await t(user_id, 'registration_info') + "\n"
        airlines = set([f.get('airline') for f in flights if f.get('airline')])
        for airline in airlines:
            checkin_url = await db.get_airline_url_travel(airline) or "https://checkin.airline.com"
            text += await t(user_id, 'registration_airline', airline=airline, checkin_url=checkin_url)
        text += await t(user_id, 'final_text')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_flight_info")],
        [InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# ============================================
# HOTEL INFO (Информация об отеле)
# ============================================

@router.callback_query(F.data == "travel_hotel")
async def show_hotel_menu(callback: CallbackQuery):
    """Показать список конференций для информации об отеле"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    if not username:
        await callback.message.edit_text(
            await t(user_id, 'error_no_username'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
            ])
        )
        return

    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            await t(user_id, 'error_no_conferences'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
            ])
        )
        return

    builder = InlineKeyboardBuilder()
    for conf in conferences:
        conf_name = conf.get('conference_name', '')
        safe_conf_name = conf_name.replace(' ', '_').replace('-', '_')
        display_text = f"🏨 {conf_name}"
        if conf.get('city'):
            display_text += f" ({conf['city']})"
        builder.row(InlineKeyboardButton(
            text=display_text,
            callback_data=f"travel_hotel_{safe_conf_name}"
        ))

    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    await callback.message.edit_text(
        await t(user_id, 'select_conference_for_hotel'),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("travel_hotel_"))
async def show_hotel_details(callback: CallbackQuery):
    """Показать детали отеля для выбранной конференции"""
    user_id = callback.from_user.id
    encoded_conf = callback.data.replace("travel_hotel_", "")
    conference = encoded_conf.replace('_', ' ')

    hotel_data = await db.get_hotel_info_travel(conference)

    if hotel_data and hotel_data.get('hotel'):
        text = await t(user_id, 'hotel_info_template',
                       hotel_name=hotel_data.get('hotel', 'Hotel'),
                       hotel_address=hotel_data.get('address', 'Address not specified'),
                       hotel_link=hotel_data.get('site', ''),
                       conference=conference
                       )
    else:
        text = await t(user_id, 'no_hotel_found')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_hotel")],
        [InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# ============================================
# VISA SUPPORT (Визовая поддержка)
# ============================================

@router.callback_query(F.data == "travel_visa_support")
async def show_visa_support(callback: CallbackQuery, state: FSMContext):
    """Возврат к визовому вопросу; старые сообщения тоже ведут в новую форму."""
    data = await state.get_data()
    if not data.get('conference'):
        await start_flight_request(callback, state)
        return
    await state.set_state(TravelStates.waiting_for_visa_info)
    await callback.message.edit_text(
        await t(callback.from_user.id, 'flight_visa_question'),
        reply_markup=await get_form_back_keyboard("travel_flight_request", callback.from_user.id)
    )


@router.message(TravelStates.waiting_for_visa_info)
async def process_visa_info(message: Message, state: FSMContext):
    user_id = message.from_user.id
    visa_info = (message.text or '').strip()
    if not visa_info:
        await message.answer(await t(user_id, 'flight_visa_question'))
        return
    await state.update_data(
        visa_info=visa_info,
        visa_status="not_have" if visa_info.casefold() in {"нет", "no"} else "have"
    )
    await state.set_state(TravelStates.waiting_for_passport_consent)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'confirm_data_storage'), callback_data="passport_consent_yes")],
        [InlineKeyboardButton(text=await t(user_id, 'dont_store'), callback_data="passport_consent_no")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_visa_support")]
    ])
    await message.answer(
        await t(user_id, 'passport_consent'), reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("passport_consent_"), TravelStates.waiting_for_passport_consent)
async def process_passport_consent(callback: CallbackQuery, state: FSMContext):
    """Обработка согласия на хранение паспортных данных"""
    user_id = callback.from_user.id
    consent = callback.data == "passport_consent_yes"
    await state.update_data(store_passport_data=consent)

    stored_data = await db.get_stored_passport_data(user_id) if consent else None

    if stored_data and consent:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(user_id, 'use_saved_data'), callback_data="use_saved_passport")],
            [InlineKeyboardButton(text=await t(user_id, 'enter_new_data'), callback_data="enter_new_passport")],
            [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_visa_support")]
        ])

        await callback.message.edit_text(
            await t(user_id, 'saved_passport_found',
                    first_name=stored_data.get('first_name', ''),
                    last_name=stored_data.get('last_name', ''),
                    passport_number=stored_data.get('passport_number', '')
                    ),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await state.set_state(TravelStates.waiting_for_first_name)
        keyboard = await get_form_back_keyboard("travel_visa_support", user_id)
        await callback.message.edit_text(
            await t(user_id, 'passport_step1'),
            reply_markup=keyboard
        )


@router.callback_query(F.data == "use_saved_passport")
async def use_saved_passport(callback: CallbackQuery, state: FSMContext):
    """Использовать сохраненные паспортные данные"""
    user_id = callback.from_user.id
    stored_data = await db.get_stored_passport_data(user_id)

    if stored_data:
        await state.update_data(**stored_data)
        await ask_departure_city(callback, state)
    else:
        await state.set_state(TravelStates.waiting_for_first_name)
        await callback.message.edit_text(await t(user_id, 'passport_step1'))


@router.callback_query(F.data == "enter_new_passport")
async def enter_new_passport(callback: CallbackQuery, state: FSMContext):
    """Ввести новые паспортные данные"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_first_name)
    await callback.message.edit_text(await t(user_id, 'passport_step1'))


# ============================================
# FLIGHT REQUEST FORM (сбор данных паспорта)
# ============================================

async def ask_departure_city(update: Union[Message, CallbackQuery], state: FSMContext):
    """Спросить город вылета"""
    await state.set_state(TravelStates.waiting_for_departure_from)

    if isinstance(update, Message):
        user_id = update.from_user.id
        await update.answer(
            await t(user_id, 'passport_step9'),
            reply_markup=await get_form_back_keyboard("back_to_expiry_date", user_id)
        )
    else:
        user_id = update.from_user.id
        await update.message.edit_text(
            await t(user_id, 'passport_step9'),
            reply_markup=await get_form_back_keyboard("back_to_expiry_date", user_id)
        )


@router.message(TravelStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Обработка имени"""
    user_id = message.from_user.id
    await state.update_data(first_name=message.text)
    await state.set_state(TravelStates.waiting_for_last_name)
    await message.answer(
        await t(user_id, 'passport_step2'),
        reply_markup=await get_form_back_keyboard("back_to_first_name", user_id)
    )


@router.message(TravelStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обработка фамилии"""
    user_id = message.from_user.id
    await state.update_data(last_name=message.text)
    await state.set_state(TravelStates.waiting_for_phone)
    await message.answer(
        await t(user_id, 'passport_step3'),
        reply_markup=await get_form_back_keyboard("back_to_last_name", user_id)
    )


@router.message(TravelStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона"""
    user_id = message.from_user.id
    await state.update_data(phone=message.text)
    await state.set_state(TravelStates.waiting_for_passport_number)
    await message.answer(
        await t(user_id, 'passport_step4'),
        reply_markup=await get_form_back_keyboard("back_to_phone", user_id)
    )


@router.message(TravelStates.waiting_for_passport_number)
async def process_passport_number(message: Message, state: FSMContext):
    """Обработка номера паспорта"""
    user_id = message.from_user.id
    await state.update_data(passport_number=message.text)
    await state.set_state(TravelStates.waiting_for_birth_date)
    await message.answer(
        await t(user_id, 'passport_step5'),
        reply_markup=await get_form_back_keyboard("back_to_passport_number", user_id)
    )


@router.message(TravelStates.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    """Обработка даты рождения"""
    user_id = message.from_user.id
    # Валидация даты
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
        await state.update_data(birth_date=message.text)
        await state.set_state(TravelStates.waiting_for_passport_country)
        await message.answer(
            await t(user_id, 'passport_step6'),
            reply_markup=await get_form_back_keyboard("back_to_birth_date", user_id)
        )
    except ValueError:
        await message.answer(await t(user_id, 'error_wrong_date_format'))


@router.message(TravelStates.waiting_for_passport_country)
async def process_passport_country(message: Message, state: FSMContext):
    """Обработка страны выдачи паспорта"""
    user_id = message.from_user.id
    await state.update_data(passport_country=message.text)
    await state.set_state(TravelStates.waiting_for_issue_date)
    await message.answer(
        await t(user_id, 'passport_step7'),
        reply_markup=await get_form_back_keyboard("back_to_passport_country", user_id)
    )


@router.message(TravelStates.waiting_for_issue_date)
async def process_issue_date(message: Message, state: FSMContext):
    """Обработка даты выдачи паспорта"""
    user_id = message.from_user.id
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
        await state.update_data(issue_date=message.text)
        await state.set_state(TravelStates.waiting_for_expiry_date)
        await message.answer(
            await t(user_id, 'passport_step8'),
            reply_markup=await get_form_back_keyboard("back_to_issue_date", user_id)
        )
    except ValueError:
        await message.answer(await t(user_id, 'error_wrong_date_format'))


@router.message(TravelStates.waiting_for_expiry_date)
async def process_expiry_date(message: Message, state: FSMContext):
    """Обработка срока действия паспорта"""
    user_id = message.from_user.id
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
        await state.update_data(expiry_date=message.text)
        await ask_departure_city(message, state)
    except ValueError:
        await message.answer(await t(user_id, 'error_wrong_date_format'))


@router.message(TravelStates.waiting_for_departure_from)
async def process_departure_from(message: Message, state: FSMContext):
    """Обработка города вылета"""
    user_id = message.from_user.id
    await state.update_data(departure_from=message.text)
    await state.set_state(TravelStates.waiting_for_return_to)
    await message.answer(
        await t(user_id, 'passport_step10'),
        reply_markup=await get_form_back_keyboard("back_to_departure_from", user_id)
    )


@router.message(TravelStates.waiting_for_return_to)
async def process_return_to(message: Message, state: FSMContext):
    """Обработка города возврата"""
    user_id = message.from_user.id
    await state.update_data(return_to=message.text)
    await state.set_state(TravelStates.waiting_for_baggage)

    # Создаем клавиатуру с локализованными кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'baggage_yes'), callback_data="baggage_yes"),
         InlineKeyboardButton(text=await t(user_id, 'baggage_no'), callback_data="baggage_no")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_return_to")]
    ])

    await message.answer(
        await t(user_id, 'baggage_question'),
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("baggage_"), TravelStates.waiting_for_baggage)
async def process_baggage(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора багажа"""
    user_id = callback.from_user.id
    needs_baggage = callback.data == "baggage_yes"
    await state.update_data(needs_baggage=needs_baggage)
    await state.set_state(TravelStates.waiting_for_hotel_needed)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'hotel_needed_yes'), callback_data="hotel_needed_yes"),
         InlineKeyboardButton(text=await t(user_id, 'hotel_needed_no'), callback_data="hotel_needed_no")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_baggage")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'hotel_question'),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("hotel_needed_"), TravelStates.waiting_for_hotel_needed)
async def process_hotel_needed(callback: CallbackQuery, state: FSMContext):
    """Обработка необходимости отеля"""
    hotel_needed = callback.data == "hotel_needed_yes"
    await state.update_data(hotel_needed=hotel_needed)

    # Сохраняем паспортные данные, если пользователь дал согласие
    data = await state.get_data()
    if data.get('store_passport_data'):
        await db.save_passport_data(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            passport_data=data
        )

    # Суточные заполняются в той же заявке после вопроса об отеле.
    await start_per_diem_form(callback, state)


async def show_flight_choice(update: Union[Message, CallbackQuery], state: FSMContext, username: str):
    """Показать выбор рейсов"""
    user_id = update.from_user.id if hasattr(update, 'from_user') else update.message.from_user.id
    data = await state.get_data()

    flights = await db.get_available_flights(
        username, data.get('departure_from'), data.get('return_to'), data.get('conference')
    )

    if flights:
        await state.set_state(TravelStates.waiting_for_flight_choice)

        await state.update_data(available_flight_ids=[flight['id'] for flight in flights])
        # Создаем клавиатуру с локализованными кнопками
        builder = InlineKeyboardBuilder()
        for flight in flights:
            text = f"{flight.get('departure_date')} {flight.get('departure_time')} {flight.get('departure_from')} → {flight.get('arrival_time')} {flight.get('arrival_city')}"
            builder.row(InlineKeyboardButton(
                text=text[:60],
                callback_data=f"flight_choose_{flight.get('id')}"
            ))
        builder.row(InlineKeyboardButton(
            text=await t(user_id, 'flight_no_suitable'),
            callback_data="flight_no_suitable"
        ))
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")
        )

        if isinstance(update, Message):
            await update.answer(
                await t(user_id, 'flight_choice'),
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.edit_text(
                await t(user_id, 'flight_choice'),
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await send_request_to_manager(update, state)


async def send_request_to_manager(update: Union[Message, CallbackQuery], state: FSMContext):
    """Отправить запрос менеджеру на подбор рейсов"""
    user_id = update.from_user.id if hasattr(update, 'from_user') else update.message.from_user.id
    data = await state.get_data()
    username = update.from_user.username if hasattr(update, 'from_user') else update.message.from_user.username

    # Формируем строку паспортных данных из отдельных полей
    passport_data_str = (
        f"First Name: {data.get('first_name', '')}\n"
        f"Last Name: {data.get('last_name', '')}\n"
        f"Phone: {data.get('phone', '')}\n"
        f"Passport Number: {data.get('passport_number', '')}\n"
        f"Birth Date: {data.get('birth_date', '')}\n"
        f"Passport Country: {data.get('passport_country', '')}\n"
        f"Issue Date: {data.get('issue_date', '')}\n"
        f"Expiry Date: {data.get('expiry_date', '')}"
    )

    flight_data = {
        'username': username,
        'user_id': user_id,
        'conference': data.get('conference'),
        'visa_status': data.get('visa_status', 'not_have'),
        'visa_info': data.get('visa_info', ''),
        'hotel_needed': data.get('hotel_needed', False),
        'selected_flight_id': data.get('selected_flight_id'),
        'payment_type': data.get('payment_type'),
        'payment_details': data.get('payment_details'),
        'consent_given': data.get('consent_given', False),
        'passport_data': passport_data_str,
        'city_from': data.get('departure_from', ''),
        'city_to': data.get('return_to', ''),
        'needs_baggage': data.get('needs_baggage', False),
        'preferences': data.get('preferences', '')
    }

    if not await db.save_flight_request(flight_data):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(user_id, 'submit'), callback_data="flight_submit_retry")],
            [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
        ])
        await state.set_state(TravelStates.waiting_for_flight_choice)
        if isinstance(update, Message):
            await update.answer(await t(user_id, 'error_saving_request'), reply_markup=keyboard)
        else:
            await update.message.edit_text(await t(user_id, 'error_saving_request'), reply_markup=keyboard)
        return

    # Отправляем в Travel-чат
    bot_obj = update.bot if isinstance(update, Message) else update.message.bot
    await send_request_notification_to_manager(
        bot=bot_obj,
        department="travel",
        request_title="✈️ Заявка на билет",
        user_data={'user_id': user_id, 'username': username},
        details={
            "Конференция": flight_data.get('conference'),
            "Виза (ответ пользователя)": flight_data.get('visa_info'),
            "Суточные": flight_data.get('payment_type'),
            "Реквизиты": flight_data.get('payment_details'),
            "Выбранный рейс (ID)": flight_data.get('selected_flight_id') or "Подбор менеджером",
            "Откуда": flight_data.get('city_from'),
            "Куда": flight_data.get('city_to'),
            "Багаж": "Да" if flight_data.get('needs_baggage') else "Нет",
            "Статус визы": flight_data.get('visa_status'),
            "Отель нужен": "Да" if data.get('hotel_needed') else "Нет"
        }
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
    ])

    if isinstance(update, Message):
        await update.answer(
            await t(user_id, 'form_complete'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.edit_text(
            await t(user_id, 'form_complete'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    await state.clear()


@router.callback_query(F.data.startswith("flight_choose_"), TravelStates.waiting_for_flight_choice)
async def process_flight_choice(callback: CallbackQuery, state: FSMContext):
    """Пользователь выбрал рейс"""
    user_id = callback.from_user.id
    flight_id = int(callback.data.replace("flight_choose_", ""))
    data = await state.get_data()
    if flight_id not in data.get('available_flight_ids', []):
        await callback.answer()
        return
    await state.update_data(selected_flight_id=flight_id)
    await send_request_to_manager(callback, state)


@router.callback_query(F.data == "flight_submit_retry", TravelStates.waiting_for_flight_choice)
async def retry_flight_request(callback: CallbackQuery, state: FSMContext):
    await send_request_to_manager(callback, state)


@router.callback_query(F.data == "flight_no_suitable", TravelStates.waiting_for_flight_choice)
async def process_no_suitable_flight(callback: CallbackQuery, state: FSMContext):
    """Ни один рейс не подходит"""
    await state.update_data(no_suitable_flight=True, selected_flight_id=None)
    await send_request_to_manager(callback, state)


# ============================================
# FLIGHT REQUEST (основная кнопка)
# ============================================

@router.callback_query(F.data.in_({"travel_flight_request", "travel_per_diem",
                                  "visa_have", "visa_not_have", "visa_special",
                                  "visa_need_help", "visa_bought_myself"}))
async def start_flight_request(callback: CallbackQuery, state: FSMContext):
    """Выбрать доступную пользователю конференцию перед заполнением заявки."""
    user_id = callback.from_user.id
    await state.clear()
    if not callback.from_user.username:
        await callback.message.edit_text(
            await t(user_id, 'error_no_username'),
            reply_markup=await get_form_back_keyboard("travel_back_to_menu", user_id)
        )
        return
    conferences = await db.get_user_active_conferences(callback.from_user.username)
    names = list(dict.fromkeys(conf['conference_name'] for conf in conferences if conf.get('conference_name')))
    if not names:
        await callback.message.edit_text(
            await t(user_id, 'error_no_conferences'),
            reply_markup=await get_form_back_keyboard("travel_back_to_menu", user_id)
        )
        return
    token = uuid4().hex[:12]
    await state.update_data(flight_conferences=names, conference_token=token)
    await state.set_state(TravelStates.waiting_for_conference)
    builder = InlineKeyboardBuilder()
    for index, name in enumerate(names):
        builder.row(InlineKeyboardButton(text=name, callback_data=f"flight_conf_{token}_{index}"))
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )
    await callback.message.edit_text(
        await t(user_id, 'select_conference_for_flight_request'), reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("flight_conf_"), TravelStates.waiting_for_conference)
async def select_flight_conference(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    token, _, index = callback.data.removeprefix("flight_conf_").partition("_")
    names = data.get('flight_conferences', [])
    if token != data.get('conference_token') or not index.isdigit() or int(index) >= len(names):
        await callback.answer()
        return
    conference = names[int(index)]
    conferences = await db.get_user_active_conferences(callback.from_user.username)
    if not any(conf.get('conference_name') == conference for conf in conferences):
        await start_flight_request(callback, state)
        return
    await state.update_data(conference=conference)
    await show_visa_support(callback, state)


# ============================================
# Daily allowance (Суточные)
# ============================================

async def start_per_diem_form(callback: CallbackQuery, state: FSMContext):
    """Блок суточных в заявке на билет; вопросы и проверки сохранены."""
    data = await state.get_data()
    if 'hotel_needed' not in data:
        await start_flight_request(callback, state)
        return
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_per_diem_payment_type)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'per_diem_card'), callback_data="per_diem_card")],
        [InlineKeyboardButton(text=await t(user_id, 'per_diem_crypto'), callback_data="per_diem_crypto")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_hotel_needed")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'per_diem_question'),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "per_diem_card", TravelStates.waiting_for_per_diem_payment_type)
async def per_diem_card_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрана оплата на карту"""
    user_id = callback.from_user.id
    await state.update_data(payment_type="card")
    await state.set_state(TravelStates.waiting_for_per_diem_card)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_per_diem_type")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'enter_card_number'),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "per_diem_crypto", TravelStates.waiting_for_per_diem_payment_type)
async def per_diem_crypto_selected(callback: CallbackQuery, state: FSMContext):
    """Выбрана оплата на криптокошелек"""
    user_id = callback.from_user.id
    await state.update_data(payment_type="crypto")
    await state.set_state(TravelStates.waiting_for_per_diem_crypto_network)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'network_trc20'), callback_data="crypto_trc20")],
        [InlineKeyboardButton(text=await t(user_id, 'network_erc20'), callback_data="crypto_erc20")],
        [InlineKeyboardButton(text=await t(user_id, 'network_bep20'), callback_data="crypto_bep20")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_per_diem_type")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'per_diem_question'),
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("crypto_"), TravelStates.waiting_for_per_diem_crypto_network)
async def per_diem_crypto_network(callback: CallbackQuery, state: FSMContext):
    """Выбрана сеть криптокошелька"""
    user_id = callback.from_user.id
    network = callback.data.replace("crypto_", "").upper()
    await state.update_data(crypto_network=network)
    await state.set_state(TravelStates.waiting_for_per_diem_crypto_address)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_per_diem_network")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'enter_crypto_address', network=network),
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_per_diem_card, F.text)
async def process_per_diem_card(message: Message, state: FSMContext):
    """Обработка номера карты"""
    user_id = message.from_user.id
    card_number = message.text.strip()
    digits = re.sub(r'\D', '', card_number)

    if len(digits) < 16:
        await message.answer(await t(user_id, 'error_invalid_card'))
        return

    await state.update_data(payment_details=card_number)
    await show_per_diem_consent(message, state)


@router.message(TravelStates.waiting_for_per_diem_crypto_address, F.text)
async def process_per_diem_crypto_address(message: Message, state: FSMContext):
    """Обработка адреса криптокошелька"""
    user_id = message.from_user.id
    address = message.text.strip()

    if len(address) < 10:
        await message.answer(await t(user_id, 'error_invalid_address'))
        return

    data = await state.get_data()
    payment_details = f"{data.get('crypto_network')}: {address}"
    await state.update_data(payment_details=payment_details)
    await show_per_diem_consent(message, state)


async def show_per_diem_consent(update: Union[Message, CallbackQuery], state: FSMContext):
    """Показать согласие на обработку данных"""
    user_id = update.from_user.id if hasattr(update, 'from_user') else update.message.from_user.id
    await state.set_state(TravelStates.waiting_for_per_diem_consent)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'confirm'), callback_data="per_diem_consent")],
        [InlineKeyboardButton(text=await t(user_id, 'cancel'), callback_data="travel_back_to_menu")]
    ])

    if isinstance(update, Message):
        await update.answer(
            await t(user_id, 'per_diem_consent'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.edit_text(
            await t(user_id, 'per_diem_consent'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )


@router.callback_query(F.data == "per_diem_consent", TravelStates.waiting_for_per_diem_consent)
async def process_per_diem_consent(callback: CallbackQuery, state: FSMContext):
    """После согласия завершить выбор рейса и сохранить одну общую заявку."""
    await state.update_data(consent_given=True)
    await show_flight_choice(callback, state, callback.from_user.username)


# ============================================
# MY REQUESTS (Мои заявки)
# ============================================

@router.callback_query(F.data == "travel_my_requests")
async def show_my_requests(callback: CallbackQuery):
    """Показать мои заявки"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    try:
        visa_status = await db.get_travel_request_status(username, "visa")
        flight_status = await db.get_travel_request_status(username, "flight")
        per_diem_status = await db.get_travel_request_status(username, "per_diem")

        status_text = await t(user_id, 'my_requests_title')

        if visa_status.get("status") == "pending":
            status_text += await t(user_id, 'visa_status_pending', submitted=visa_status.get('submitted', ''))
        elif visa_status.get("status") == "no_requests":
            status_text += await t(user_id, 'visa_status_no')

        if flight_status.get("status") == "pending":
            status_text += await t(user_id, 'flight_status_pending', submitted=flight_status.get('submitted', ''))
        elif flight_status.get("status") == "no_requests":
            status_text += await t(user_id, 'flight_status_no')

        if per_diem_status.get("status") == "pending":
            status_text += await t(user_id, 'per_diem_status_pending', submitted=per_diem_status.get('submitted', ''))
        elif per_diem_status.get("status") == "no_requests":
            status_text += await t(user_id, 'per_diem_status_no')

        status_text += await t(user_id, 'status_footer')

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(user_id, 'check_again'), callback_data="travel_my_requests")],
            [InlineKeyboardButton(text=await t(user_id, 'new_request'), callback_data="travel_visa_support")],
            [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
        ])

        await callback.message.edit_text(
            status_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error showing requests: {e}")
        await callback.message.edit_text(
            await t(user_id, 'error_loading_requests'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
            ])
        )


# ============================================
# QUESTION TO MANAGER (Вопрос менеджеру)
# ============================================

@router.callback_query(F.data == "travel_question")
async def show_question(callback: CallbackQuery, state: FSMContext):
    """Показать форму вопроса"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_travel_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'question_to_manager'),
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_travel_question, F.text.len() <= 500)
async def process_travel_question(message: Message, state: FSMContext):
    """Обработка вопроса"""
    user_id = message.from_user.id
    question_text = message.text

    travel_question_data = {
        'username': message.from_user.username,
        'user_id': user_id,
        'category': 'travel_general',
        'question': question_text
    }

    if await db.save_travel_question(travel_question_data):
        await db.log_user_action(
            user_id=user_id,
            username=message.from_user.username,
            action="travel_question_submitted",
            details={"data": travel_question_data}
        )

        await send_question_to_manager(
            bot=message.bot,
            manager_chat_id=get_manager_chat_id('travel'),
            user_data=travel_question_data,
            question_text=question_text,
            question_type="travel"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="travel_back_to_menu")]
        ])

        await message.answer(
            await t(user_id, 'question_sent'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(await t(user_id, 'error_saving_request'))

    await state.clear()


@router.message(TravelStates.waiting_for_travel_question, F.text.len() > 500)
async def process_travel_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    user_id = message.from_user.id
    await message.answer(await t(user_id, 'question_too_long'))


# ============================================
# BACK BUTTON HANDLERS
# ============================================

@router.callback_query(F.data == "back_to_first_name")
async def back_to_first_name(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу имени"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_first_name)
    await callback.message.edit_text(
        await t(user_id, 'passport_step1'),
        reply_markup=await get_form_back_keyboard("travel_visa_support", user_id)
    )


@router.callback_query(F.data == "back_to_last_name")
async def back_to_last_name(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу фамилии"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_last_name)
    await callback.message.edit_text(
        await t(user_id, 'passport_step2'),
        reply_markup=await get_form_back_keyboard("back_to_first_name", user_id)
    )


@router.callback_query(F.data == "back_to_phone")
async def back_to_phone(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу телефона"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_phone)
    await callback.message.edit_text(
        await t(user_id, 'passport_step3'),
        reply_markup=await get_form_back_keyboard("back_to_last_name", user_id)
    )


@router.callback_query(F.data == "back_to_passport_number")
async def back_to_passport_number(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу номера паспорта"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_passport_number)
    await callback.message.edit_text(
        await t(user_id, 'passport_step4'),
        reply_markup=await get_form_back_keyboard("back_to_phone", user_id)
    )


@router.callback_query(F.data == "back_to_birth_date")
async def back_to_birth_date(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу даты рождения"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_birth_date)
    await callback.message.edit_text(
        await t(user_id, 'passport_step5'),
        reply_markup=await get_form_back_keyboard("back_to_passport_number", user_id)
    )


@router.callback_query(F.data == "back_to_passport_country")
async def back_to_passport_country(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу страны"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_passport_country)
    await callback.message.edit_text(
        await t(user_id, 'passport_step6'),
        reply_markup=await get_form_back_keyboard("back_to_birth_date", user_id)
    )


@router.callback_query(F.data == "back_to_issue_date")
async def back_to_issue_date(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу даты выдачи"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_issue_date)
    await callback.message.edit_text(
        await t(user_id, 'passport_step7'),
        reply_markup=await get_form_back_keyboard("back_to_passport_country", user_id)
    )


@router.callback_query(F.data == "back_to_expiry_date")
async def back_to_expiry_date(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу срока действия"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_expiry_date)
    await callback.message.edit_text(
        await t(user_id, 'passport_step8'),
        reply_markup=await get_form_back_keyboard("back_to_issue_date", user_id)
    )


@router.callback_query(F.data == "back_to_departure_from")
async def back_to_departure_from(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу города вылета"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_departure_from)
    await callback.message.edit_text(
        await t(user_id, 'passport_step9'),
        reply_markup=await get_form_back_keyboard("back_to_expiry_date", user_id)
    )


@router.callback_query(F.data == "back_to_return_to")
async def back_to_return_to(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу города возврата"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_return_to)
    await callback.message.edit_text(
        await t(user_id, 'passport_step10'),
        reply_markup=await get_form_back_keyboard("back_to_departure_from", user_id)
    )


@router.callback_query(F.data == "back_to_hotel_needed")
async def back_to_hotel_needed(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_hotel_needed)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'hotel_question'),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(user_id, 'hotel_needed_yes'), callback_data="hotel_needed_yes"),
             InlineKeyboardButton(text=await t(user_id, 'hotel_needed_no'), callback_data="hotel_needed_no")],
            [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_baggage")]
        ]), parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "back_to_baggage")
async def back_to_baggage(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору багажа"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_baggage)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'baggage_yes'), callback_data="baggage_yes"),
         InlineKeyboardButton(text=await t(user_id, 'baggage_no'), callback_data="baggage_no")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_return_to")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'baggage_question'),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "travel_compensation")
async def travel_compensation_handler(callback: CallbackQuery):
    user_id = callback.from_user.id

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="menu_travel"))

    text = await t(user_id, 'stub_compensation')
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "back_to_per_diem_type")
async def back_to_per_diem_type(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору типа выплаты суточных"""
    await start_per_diem_form(callback, state)


@router.callback_query(F.data == "back_to_per_diem_network")
async def back_to_per_diem_network(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору сети криптокошелька"""
    user_id = callback.from_user.id
    await state.set_state(TravelStates.waiting_for_per_diem_crypto_network)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'network_trc20'), callback_data="crypto_trc20")],
        [InlineKeyboardButton(text=await t(user_id, 'network_erc20'), callback_data="crypto_erc20")],
        [InlineKeyboardButton(text=await t(user_id, 'network_bep20'), callback_data="crypto_bep20")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="back_to_per_diem_type")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'per_diem_question'),
        reply_markup=keyboard
    )
