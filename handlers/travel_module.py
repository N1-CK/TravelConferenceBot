import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Union
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
import os
from handlers.managers_chat import send_question_to_manager
from keyboards import get_travel_menu_keyboard
from utility.lang_utils import *

TRAVEL_MANAGER_CHAT_ID = int(os.getenv("TG_TRAVEL_MANAGER_CHAT_ID", 0))

router = Router()
logger = logging.getLogger(__name__)


# ============================================
# СОСТОЯНИЯ
# ============================================

class TravelStates(StatesGroup):
    english = State()

    # Для Flight Request
    waiting_for_visa_status = State()
    waiting_for_passport_consent = State()
    waiting_for_passport = State()
    waiting_for_city_from = State()
    waiting_for_city_to = State()
    waiting_for_baggage = State()
    waiting_for_preferences = State()
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
    waiting_for_visa_needed = State()
    waiting_for_visa_dates = State()

    # Для Daily allowance
    waiting_for_per_diem_payment_type = State()
    waiting_for_per_diem_card = State()
    waiting_for_per_diem_crypto_network = State()
    waiting_for_per_diem_crypto_address = State()
    waiting_for_per_diem_consent = State()


# ============================================
# КЛАВИАТУРЫ
# ============================================

async def get_selected_conference_text(user_id: int) -> str:
    """Получить текст с выбранной конференцией"""
    selected_conf = await db.get_selected_conference(user_id)
    if selected_conf:
        return f"\n\n📌 *Текущая конференция:* {selected_conf}"
    return ""


# def get_travel_menu_keyboard() -> InlineKeyboardMarkup:
#     """Главное меню Travel"""
#     builder = InlineKeyboardBuilder()
#     builder.row(
#         InlineKeyboardButton(text="✈️ Flight Request", callback_data="travel_flight_request")
#     )
#     builder.row(
#         InlineKeyboardButton(text="🛂 Visa Support", callback_data="travel_visa_support"),
#         InlineKeyboardButton(text="ℹ️ Flight Info", callback_data="travel_flight_info")
#     )
#     builder.row(
#         InlineKeyboardButton(text="🏨 Hotel", callback_data="travel_hotel_info"),
#         InlineKeyboardButton(text="💰 Daily allowance", callback_data="travel_per_diem")
#     )
#     builder.row(
#         InlineKeyboardButton(text="📋 My requests", callback_data="travel_my_requests"),
#         InlineKeyboardButton(text="❓ Question", callback_data="travel_question")
#     )
#     builder.row(
#         InlineKeyboardButton(text="◀️ Back", callback_data="menu_main")
#     )
#     return builder.as_markup()


def get_flight_choice_keyboard(flights: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора рейса"""
    builder = InlineKeyboardBuilder()

    for flight in flights:
        # Форматируем: 12.02.2026 13:50 DME - 12.02.2026 16:50 IST
        text = f"{flight.get('departure_date')} {flight.get('departure_time')} {flight.get('departure_from')} → {flight.get('arrival_time')} {flight.get('arrival_city')}"
        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"flight_choose_{flight.get('id')}"
        ))

    builder.row(InlineKeyboardButton(
        text="❌ Ни один из рейсов не подходит. Свяжитесь со мной",
        callback_data="flight_no_suitable"
    ))
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")
    )
    return builder.as_markup()


def get_form_back_keyboard(back_to: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для форм"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data=back_to),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    return builder.as_markup()


def get_baggage_keyboard(back_callback: str = "visa_back_step3") -> InlineKeyboardMarkup:
    """Клавиатура выбора багажа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes", callback_data="baggage_yes"),
        InlineKeyboardButton(text="❌ No", callback_data="baggage_no")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data=back_callback)
    )
    return builder.as_markup()


def get_visa_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для визовой поддержки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ I have a visa", callback_data="visa_have")
    )
    builder.row(
        InlineKeyboardButton(text="❌ I don't have a visa", callback_data="visa_not_have")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Special case", callback_data="visa_special")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")
    )
    return builder.as_markup()


# ============================================
# ТЕКСТЫ
# ============================================

TEXTS = {
    'welcome': "✈️ TRAVEL Section\n\nChoose an option:",
    'visa_support': "🛂 Visa Support\n\nChoose your status:",
    'visa_instructions': '''📋 *Visa Application Instructions* ...''',
    'flight_form': "✈️ Flight Ticket Request\n\nStep {step}\n{question}",
    'passport_consent': "📋 **Data Storage Consent**\n\nDo you allow us to store your passport data for future bookings within 6 months?",
    'hotel_question': "🏨 **Hotel needed?**\n\nWill you need a hotel for this conference?\n\n*Note:* Company does not reimburse independent bookings or +1 accompanying persons.",
    'flight_choice': "✈️ **Choose your flight**\n\nPlease select the most convenient flight:",
    'form_complete': '''✅ **Request submitted successfully!**

📋 *Next steps:*
• Check Telegram notifications for updates
• If visa needed: start document collection
• Monitor email for ticket confirmations
• Click 'My Requests' to check status

⏰ *Expected timeline:*
• Flight tickets: 1-3 business days
• Visa processing: 5-10 business days
• Hotel booking: 2-4 business days

_Our travel team will contact you soon._''',
    'per_diem_consent': "📝 Confirmation\n\nI consent to the processing of personal data",
    'per_diem_success': '''✅ **Daily allowance request submitted!**

Thank you for your request. Our finance team will process your payment details and contact you if additional information is needed.

For questions, contact our travel team via bot.''',
    'hotel_info': '''🏨 *{hotel_name}*

📍 _{hotel_address}_

{hotel_link}

Booked for conference: *{conference}*''',
    'flight_info': '''*Flight {fl_num}*

Flight number: {flight_number}
Booking number: *{book_number}*

📍 *Route*
{departure_from} → {arrival_city}

🏷 *Date & Time*
Date: {departure_date}
Departure: {departure_time}
Arrival: {arrival_time}

🧳 *Luggage*
Carry-on: {carry_luggage} kg
Checked: {luggage} kg

🛩️ Airline: *{airline}*

''',
    'registration_info': "📌 *Check-in*\n\nYou can check in for your flight *24 hours before departure* using this link:\n",
    'registration_airline': "*{airline}*: {checkin_url}\n",
    'final_text': "\n_Wish you a great flight!_ 🔥",
}


# ============================================
# ГЛАВНОЕ МЕНЮ
# ============================================

@router.callback_query(F.data == "menu_travel")
async def show_travel_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.english)
    await callback.message.edit_text(
        await t(callback.from_user.id, 'travel_welcome'),
        reply_markup=await get_travel_menu_keyboard(callback.from_user.id)
    )


@router.callback_query(F.data == "travel_back_to_menu")
async def back_to_travel_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.english)
    await callback.message.edit_text(
        await t(callback.from_user.id, 'travel_welcome'),
        reply_markup=await get_travel_menu_keyboard(callback.from_user.id)
    )


# ============================================
# FLIGHT INFO (Информация о рейсах)
# ============================================

@router.callback_query(F.data == "travel_flight_info")
async def show_flight_info(callback: CallbackQuery):
    username = callback.from_user.username

    if not username:
        await callback.message.edit_text(
            "Please set your Telegram username first.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
            ])
        )
        return

    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            "No conferences found for your account.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
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
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )

    await callback.message.edit_text("Select the conference:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("travel_conf_info_"))
async def show_conference_flights(callback: CallbackQuery):
    # Декодируем название конференции
    encoded_conf = callback.data.replace("travel_conf_info_", "")
    conference = encoded_conf.replace('_', ' ')
    username = callback.from_user.username

    flights = await db.get_flight_details_travel(username, conference)

    if not flights:
        text = "No flight information found for this conference."
    else:
        text = ""
        for i, flight in enumerate(flights, 1):
            text += TEXTS['flight_info'].format(
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
            )

        text += "\n" + TEXTS['registration_info'] + "\n"
        airlines = set([f.get('airline') for f in flights if f.get('airline')])
        for airline in airlines:
            checkin_url = await db.get_airline_url_travel(airline) or "https://checkin.airline.com"
            text += TEXTS['registration_airline'].format(airline=airline, checkin_url=checkin_url)
        text += TEXTS['final_text']

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="travel_flight_info")],
        [InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ============================================
# HOTEL INFO (Информация об отеле)
# ============================================

@router.callback_query(F.data == "travel_hotel_info")
async def show_hotel_menu(callback: CallbackQuery):
    username = callback.from_user.username

    if not username:
        await callback.message.edit_text(
            "Please set your Telegram username first.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
            ])
        )
        return

    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            "No conferences found.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
            ])
        )
        return

    builder = InlineKeyboardBuilder()
    for conf in conferences:
        # Используем conference_name для отображения, но для callback используем ID или кодируем название
        conf_name = conf.get('conference_name', '')
        if conf.get('city'):
            display_text = f"🏨 {conf_name} ({conf['city']})"
        else:
            display_text = f"🏨 {conf_name}"

        # Кодируем название для callback (заменяем пробелы и спецсимволы)
        safe_conf_name = conf_name.replace(' ', '_').replace('-', '_')
        builder.row(InlineKeyboardButton(
            text=display_text,
            callback_data=f"travel_hotel_{safe_conf_name}"
        ))

    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )

    await callback.message.edit_text("🏨 Hotel Information\n\nSelect the conference:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("travel_hotel_"))
async def show_hotel_details(callback: CallbackQuery):
    # Декодируем название конференции
    encoded_conf = callback.data.replace("travel_hotel_", "")
    conference = encoded_conf.replace('_', ' ')

    hotel_data = await db.get_hotel_info_travel(conference)

    if hotel_data and hotel_data.get('hotel'):
        text = TEXTS['hotel_info'].format(
            hotel_name=hotel_data.get('hotel', 'Hotel'),
            hotel_address=hotel_data.get('address', 'Address not specified'),
            hotel_link=hotel_data.get('site', ''),
            conference=conference
        )
    else:
        text = "Accommodation information not found for this conference."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="travel_hotel_info")],
        [InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ============================================
# VISA SUPPORT (Визовая поддержка)
# ============================================

@router.callback_query(F.data == "travel_visa_support")
async def show_visa_support(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'visa_support_title'),
        reply_markup=get_visa_keyboard()
    )


@router.callback_query(F.data.startswith("visa_"))
async def process_visa_status(callback: CallbackQuery, state: FSMContext):
    visa_status = callback.data.replace("visa_", "")

    if visa_status == "not_have":
        # Вопрос о помощи с билетами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, нужна помощь", callback_data="visa_need_help")],
            [InlineKeyboardButton(text="🛒 Я купил всё сам", callback_data="visa_bought_myself")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="travel_visa_support")]
        ])

        await callback.message.edit_text(
            "🛂 Visa Support\n\nDo you need help from travel manager with ticket purchase or hotel booking?",
            reply_markup=keyboard
        )
    elif visa_status == "have":
        await state.update_data(visa_status="have")
        await state.set_state(TravelStates.waiting_for_passport_consent)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm data storage", callback_data="passport_consent_yes")],
            [InlineKeyboardButton(text="❌ Don't store", callback_data="passport_consent_no")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_visa_support")]
        ])

        await callback.message.edit_text(
            TEXTS['passport_consent'],
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback.message.edit_text("Special case processing...",
                                         reply_markup=get_form_back_keyboard("travel_visa_support"))


@router.callback_query(F.data == "visa_need_help")
async def visa_need_help(callback: CallbackQuery, state: FSMContext):
    await state.update_data(visa_status="not_have", needs_help=True)
    await state.set_state(TravelStates.waiting_for_passport_consent)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm data storage", callback_data="passport_consent_yes")],
        [InlineKeyboardButton(text="❌ Don't store", callback_data="passport_consent_no")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="travel_visa_support")]
    ])

    await callback.message.edit_text(
        TEXTS['passport_consent'],
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "visa_bought_myself")
async def visa_bought_myself(callback: CallbackQuery, state: FSMContext):
    await state.update_data(visa_status="not_have", needs_help=False)

    visa_data = {
        'username': callback.from_user.username,
        'user_id': callback.from_user.id,
        'visa_status': "not_have",
        'needs_help': False,
        'passport_data': '-',
        'city_from': '-',
        'city_to': '-',
        'needs_baggage': False,
        'preferences': 'User booked independently'
    }
    await db.save_visa_request(visa_data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Travel", callback_data="travel_back_to_menu")]
    ])

    await callback.message.edit_text(
        "✅ Thank you for the information!\n\n"
        "Great that you've organized your travel independently.\n"
        "If you have questions, contact travel team.",
        reply_markup=keyboard
    )
    await state.clear()


@router.callback_query(F.data.startswith("passport_consent_"))
async def process_passport_consent(callback: CallbackQuery, state: FSMContext):
    consent = callback.data == "passport_consent_yes"
    await state.update_data(store_passport_data=consent)

    # Проверяем, есть ли сохраненные данные пользователя
    user_id = callback.from_user.id
    stored_data = await db.get_stored_passport_data(user_id) if consent else None

    if stored_data and consent:
        # Предлагаем использовать сохраненные данные
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Use saved data", callback_data="use_saved_passport")],
            [InlineKeyboardButton(text="✏️ Enter new data", callback_data="enter_new_passport")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_visa_support")]
        ])

        await callback.message.edit_text(
            "📋 **Saved passport data found**\n\n"
            f"Name: {stored_data.get('first_name')} {stored_data.get('last_name')}\n"
            f"Passport: {stored_data.get('passport_number')}\n\n"
            "Use saved data?",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await state.set_state(TravelStates.waiting_for_first_name)
        keyboard = get_form_back_keyboard("travel_visa_support")
        await callback.message.edit_text(
            "Step 1 of 12\nYour first name as in passport:",
            reply_markup=keyboard
        )


@router.callback_query(F.data == "use_saved_passport")
async def use_saved_passport(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    stored_data = await db.get_stored_passport_data(user_id)

    if stored_data:
        await state.update_data(**stored_data)
        await ask_departure_city(callback.message, state)
    else:
        await state.set_state(TravelStates.waiting_for_first_name)
        await callback.message.edit_text("Step 1 of 12\nYour first name as in passport:")


@router.callback_query(F.data == "enter_new_passport")
async def enter_new_passport(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_first_name)
    await callback.message.edit_text("Step 1 of 12\nYour first name as in passport:")


async def ask_departure_city(update: Union[Message, CallbackQuery], state: FSMContext):
    await state.set_state(TravelStates.waiting_for_departure_from)
    keyboard = get_form_back_keyboard("travel_visa_support")

    if isinstance(update, Message):
        await update.answer("Where are you planning to fly from?", reply_markup=keyboard)
    else:
        await update.message.edit_text(
            "Where are you planning to fly from? / Откуда планируете вылетать?",
            reply_markup=keyboard
        )


# ============================================
# FLIGHT REQUEST FORM (сбор данных паспорта)
# ============================================

@router.message(TravelStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await state.set_state(TravelStates.waiting_for_last_name)
    await message.answer(
        "Step 2 of 12\nYour last name as in passport:",
        reply_markup=get_form_back_keyboard("travel_visa_support")
    )


@router.message(TravelStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await state.set_state(TravelStates.waiting_for_phone)
    await message.answer(
        "Step 3 of 12\nYour phone number:",
        reply_markup=get_form_back_keyboard("back_to_first_name")
    )


@router.message(TravelStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(TravelStates.waiting_for_passport_number)
    await message.answer(
        "Step 4 of 12\nPassport number:",
        reply_markup=get_form_back_keyboard("back_to_last_name")
    )


@router.message(TravelStates.waiting_for_passport_number)
async def process_passport_number(message: Message, state: FSMContext):
    await state.update_data(passport_number=message.text)
    await state.set_state(TravelStates.waiting_for_birth_date)
    await message.answer(
        "Step 5 of 12\nDate of birth (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_phone")
    )


@router.message(TravelStates.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    await state.update_data(birth_date=message.text)
    await state.set_state(TravelStates.waiting_for_passport_country)
    await message.answer(
        "Step 6 of 12\nCountry of passport issuance:",
        reply_markup=get_form_back_keyboard("back_to_passport_number")
    )


@router.message(TravelStates.waiting_for_passport_country)
async def process_passport_country(message: Message, state: FSMContext):
    await state.update_data(passport_country=message.text)
    await state.set_state(TravelStates.waiting_for_issue_date)
    await message.answer(
        "Step 7 of 12\nPassport issue date (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_birth_date")
    )


@router.message(TravelStates.waiting_for_issue_date)
async def process_issue_date(message: Message, state: FSMContext):
    await state.update_data(issue_date=message.text)
    await state.set_state(TravelStates.waiting_for_expiry_date)
    await message.answer(
        "Step 8 of 12\nPassport expiration date (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_passport_country")
    )


@router.message(TravelStates.waiting_for_expiry_date)
async def process_expiry_date(message: Message, state: FSMContext):
    await state.update_data(expiry_date=message.text)
    await ask_departure_city(message, state)


@router.message(TravelStates.waiting_for_departure_from)
async def process_departure_from(message: Message, state: FSMContext):
    await state.update_data(departure_from=message.text)
    await state.set_state(TravelStates.waiting_for_return_to)
    await message.answer(
        "Step 10 of 12\nWhere are you planning to return to?",
        reply_markup=get_form_back_keyboard("back_to_departure_from")
    )


@router.message(TravelStates.waiting_for_return_to)
async def process_return_to(message: Message, state: FSMContext):
    await state.update_data(return_to=message.text)
    await state.set_state(TravelStates.waiting_for_baggage)

    keyboard = get_baggage_keyboard("back_to_return_to")
    await message.answer(
        "Step 11 of 12\nDo you need checked baggage?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("baggage_"), TravelStates.waiting_for_baggage)
async def process_baggage(callback: CallbackQuery, state: FSMContext):
    needs_baggage = callback.data == "baggage_yes"
    await state.update_data(needs_baggage=needs_baggage)
    await state.set_state(TravelStates.waiting_for_hotel_needed)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes", callback_data="hotel_needed_yes")],
        [InlineKeyboardButton(text="❌ No", callback_data="hotel_needed_no")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_baggage")]
    ])

    await callback.message.edit_text(
        TEXTS['hotel_question'],
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("hotel_needed_"), TravelStates.waiting_for_hotel_needed)
async def process_hotel_needed(callback: CallbackQuery, state: FSMContext):
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

    # Показываем выбор рейсов
    await show_flight_choice(callback.message, state, callback.from_user.username)


async def show_flight_choice(update: Union[Message, CallbackQuery], state: FSMContext, username: str):
    """Показать выбор рейсов"""
    data = await state.get_data()
    conference = data.get('selected_conference')

    # Получаем доступные рейсы для пользователя
    flights = await db.get_available_flights(username, data.get('departure_from'), data.get('return_to'))

    if flights:
        await state.set_state(TravelStates.waiting_for_flight_choice)
        keyboard = get_flight_choice_keyboard(flights)

        if isinstance(update, Message):
            await update.answer(TEXTS['flight_choice'], reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.edit_text(TEXTS['flight_choice'], reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        # Нет доступных рейсов - отправляем запрос менеджеру
        await send_request_to_manager(update, state)


async def send_request_to_manager(update: Union[Message, CallbackQuery], state: FSMContext):
    """Отправить запрос менеджеру на подбор рейсов"""
    data = await state.get_data()
    username = update.from_user.username if hasattr(update, 'from_user') else update.message.from_user.username

    # Сохраняем заявку
    flight_data = {
        'username': username,
        'user_id': update.from_user.id if hasattr(update, 'from_user') else update.message.from_user.id,
        'visa_status': data.get('visa_status'),
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'phone': data.get('phone'),
        'passport_number': data.get('passport_number'),
        'birth_date': data.get('birth_date'),
        'passport_country': data.get('passport_country'),
        'issue_date': data.get('issue_date'),
        'expiry_date': data.get('expiry_date'),
        'departure_from': data.get('departure_from'),
        'return_to': data.get('return_to'),
        'needs_baggage': data.get('needs_baggage', False),
        'hotel_needed': data.get('hotel_needed', False),
        'preferences': data.get('preferences', '')
    }

    await db.save_flight_request(flight_data)

    # Отправляем менеджеру
    await send_question_to_manager(
        bot=update.bot if hasattr(update, 'bot') else update.message.bot,
        manager_chat_id=TRAVEL_MANAGER_CHAT_ID,
        user_data=flight_data,
        question_text=f"New flight request from {username}\nFrom: {data.get('departure_from')}\nTo: {data.get('return_to')}",
        question_type="travel_flight"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Travel", callback_data="travel_back_to_menu")]
    ])

    if isinstance(update, Message):
        await update.answer(TEXTS['form_complete'], reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.edit_text(TEXTS['form_complete'], reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    await state.clear()


@router.callback_query(F.data.startswith("flight_choose_"), TravelStates.waiting_for_flight_choice)
async def process_flight_choice(callback: CallbackQuery, state: FSMContext):
    """Пользователь выбрал рейс - спрашиваем про отель"""
    flight_id = int(callback.data.replace("flight_choose_", ""))
    await state.update_data(selected_flight_id=flight_id)

    # Спрашиваем про отель
    user_id = callback.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes", callback_data="hotel_after_flight_yes"),
         InlineKeyboardButton(text="❌ No", callback_data="hotel_after_flight_no")]
    ])

    await callback.message.edit_text(
        "🏨 **Will you need a hotel for this conference?**\n\n"
        "The company does not reimburse expenses for independently booked hotels or bookings for accompanying persons.",
        reply_markup=keyboard
    )
    await state.set_state(TravelStates.waiting_for_hotel_needed)

@router.callback_query(F.data.startswith("hotel_after_flight_"), TravelStates.waiting_for_hotel_needed)
async def process_hotel_after_flight(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа об отеле после выбора рейса"""
    hotel_needed = callback.data == "hotel_after_flight_yes"
    await state.update_data(hotel_needed=hotel_needed)
    await send_request_to_manager(callback, state)


@router.callback_query(F.data == "flight_no_suitable", TravelStates.waiting_for_flight_choice)
async def process_no_suitable_flight(callback: CallbackQuery, state: FSMContext):
    """Ни один рейс не подходит"""
    await state.update_data(no_suitable_flight=True)
    await send_request_to_manager(callback, state)


# ============================================
# FLIGHT REQUEST (основная кнопка)
# ============================================

@router.callback_query(F.data == "travel_flight_request")
async def start_flight_request(callback: CallbackQuery, state: FSMContext):
    """Начало формы запроса билета"""
    await show_visa_support(callback)


# ============================================
# Daily allowance (Суточные)
# ============================================

@router.callback_query(F.data == "travel_per_diem")
async def start_per_diem_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы суточных"""
    await state.set_state(TravelStates.waiting_for_per_diem_payment_type)

    lang = await get_user_lang(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text_sync(lang, 'per_diem_card'), callback_data="per_diem_card")],
        [InlineKeyboardButton(text=get_text_sync(lang, 'per_diem_crypto'), callback_data="per_diem_crypto")],
        [InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="travel_back_to_menu")]
    ])
    await callback.message.edit_text(
        await t(callback.from_user.id, 'per_diem_question'),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "per_diem_card", TravelStates.waiting_for_per_diem_payment_type)
async def per_diem_card_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_type="card")
    await state.set_state(TravelStates.waiting_for_per_diem_card)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_type")]
    ])

    await callback.message.edit_text("💳 Enter your card number:", reply_markup=keyboard)


@router.callback_query(F.data == "per_diem_crypto", TravelStates.waiting_for_per_diem_payment_type)
async def per_diem_crypto_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_type="crypto")
    await state.set_state(TravelStates.waiting_for_per_diem_crypto_network)

    lang = await get_user_lang(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text_sync(lang, 'network_trc20'), callback_data="crypto_trc20")],
        [InlineKeyboardButton(text=get_text_sync(lang, 'network_erc20'), callback_data="crypto_erc20")],
        [InlineKeyboardButton(text=get_text_sync(lang, 'network_bep20'), callback_data="crypto_bep20")],
        [InlineKeyboardButton(text=get_text_sync(lang, 'back'), callback_data="back_to_per_diem_type")]
    ])

    await callback.message.edit_text("🪙 Select your wallet network:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("crypto_"), TravelStates.waiting_for_per_diem_crypto_network)
async def per_diem_crypto_network(callback: CallbackQuery, state: FSMContext):
    network = callback.data.replace("crypto_", "").upper()
    await state.update_data(crypto_network=network)
    await state.set_state(TravelStates.waiting_for_per_diem_crypto_address)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_network")]
    ])

    await callback.message.edit_text(f"🪙 Enter your wallet address ({network}):", reply_markup=keyboard)


@router.message(TravelStates.waiting_for_per_diem_card)
async def process_per_diem_card(message: Message, state: FSMContext):
    card_number = message.text.strip()
    digits = re.sub(r'\D', '', card_number)

    if len(digits) < 16:
        await message.answer("❌ Invalid card number. Try again:")
        return

    await state.update_data(payment_details=card_number)
    await show_per_diem_consent(message, state)


@router.message(TravelStates.waiting_for_per_diem_crypto_address)
async def process_per_diem_crypto_address(message: Message, state: FSMContext):
    address = message.text.strip()

    if len(address) < 10:
        await message.answer("❌ Address too short. Try again:")
        return

    data = await state.get_data()
    payment_details = f"{data.get('crypto_network')}: {address}"
    await state.update_data(payment_details=payment_details)
    await show_per_diem_consent(message, state)


async def show_per_diem_consent(update: Union[Message, CallbackQuery], state: FSMContext):
    await state.set_state(TravelStates.waiting_for_per_diem_consent)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I consent", callback_data="per_diem_consent")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="travel_back_to_menu")]
    ])

    if isinstance(update, Message):
        await update.answer(TEXTS['per_diem_consent'], reply_markup=keyboard)
    else:
        await update.message.edit_text(TEXTS['per_diem_consent'], reply_markup=keyboard)


@router.callback_query(F.data == "per_diem_consent", TravelStates.waiting_for_per_diem_consent)
async def process_per_diem_consent(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    per_diem_data = {
        'username': callback.from_user.username,
        'user_id': callback.from_user.id,
        'payment_type': data.get('payment_type'),
        'payment_details': data.get('payment_details'),
        'consent_given': True
    }

    await db.save_per_diem_request(per_diem_data)

    await db.log_user_action(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        action="per_diem_request_submitted",
        details={"payment_type": data.get('payment_type')}
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Travel", callback_data="travel_back_to_menu")],
        [InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        TEXTS['per_diem_success'],
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await state.clear()


# ============================================
# MY REQUESTS (Мои заявки)
# ============================================

@router.callback_query(F.data == "travel_my_requests")
async def show_my_requests(callback: CallbackQuery):
    username = callback.from_user.username

    try:
        visa_status = await db.get_travel_request_status(username, "visa")
        flight_status = await db.get_travel_request_status(username, "flight")
        per_diem_status = await db.get_travel_request_status(username, "per_diem")

        status_text = "📋 *Your Travel Requests*\n\n"

        if visa_status.get("status") == "pending":
            status_text += f"🛂 *Visa Support:* ⏳ Processing\n   Submitted: {visa_status.get('submitted')}\n\n"
        elif visa_status.get("status") == "no_requests":
            status_text += f"🛂 *Visa Support:* 📝 No requests yet\n\n"

        if flight_status.get("status") == "pending":
            status_text += f"✈️ *Flight Request:* ⏳ Processing\n   Submitted: {flight_status.get('submitted')}\n\n"
        elif flight_status.get("status") == "no_requests":
            status_text += f"✈️ *Flight Request:* 📝 No requests yet\n\n"

        if per_diem_status.get("status") == "pending":
            status_text += f"💰 *Daily allowance:* ⏳ Processing\n   Submitted: {per_diem_status.get('submitted')}\n\n"
        elif per_diem_status.get("status") == "no_requests":
            status_text += f"💰 *Daily allowance:* 📝 No requests yet\n\n"

        status_text += "_You will receive notifications when status changes._"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Check again", callback_data="travel_my_requests")],
            [InlineKeyboardButton(text="📝 New request", callback_data="travel_visa_support")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
        ])

        await callback.message.edit_text(status_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error showing requests: {e}")
        await callback.message.edit_text(
            "❌ Error loading your requests.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
            ])
        )


# ============================================
# QUESTION TO MANAGER (Вопрос менеджеру)
# ============================================

@router.callback_query(F.data == "travel_question")
async def show_question(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_travel_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
    ])

    await callback.message.edit_text(
        "❓ Question to Travel Manager\n\nPlease write your question (max 500 characters):",
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_travel_question, F.text.len() <= 500)
async def process_travel_question(message: Message, state: FSMContext):
    question_text = message.text

    travel_question_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'category': 'travel_general',
        'question': question_text
    }

    if await db.save_travel_question(travel_question_data):
        await send_question_to_manager(
            bot=message.bot,
            manager_chat_id=TRAVEL_MANAGER_CHAT_ID,
            user_data=travel_question_data,
            question_text=question_text,
            question_type="travel"
        )

        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="travel_question_submitted",
            details={"data": travel_question_data}
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Travel Menu", callback_data="travel_back_to_menu")]
        ])

        await message.answer(
            "✅ Question sent!\n\nThank you for your question. Our travel team will contact you soon.",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Error saving question. Please try again later.")

    await state.clear()


@router.message(TravelStates.waiting_for_travel_question, F.text.len() > 500)
async def process_travel_question_too_long(message: Message):
    await message.answer("❌ Question is too long. Maximum 500 characters.")


# ============================================
# BACK BUTTON HANDLERS
# ============================================

@router.callback_query(F.data == "back_to_first_name")
async def back_to_first_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_first_name)
    await callback.message.edit_text(
        "Step 1 of 12\nYour first name as in passport:",
        reply_markup=get_form_back_keyboard("travel_back_to_menu")
    )


@router.callback_query(F.data == "back_to_last_name")
async def back_to_last_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_last_name)
    await callback.message.edit_text(
        "Step 2 of 12\nYour last name as in passport:",
        reply_markup=get_form_back_keyboard("back_to_first_name")
    )


@router.callback_query(F.data == "back_to_phone")
async def back_to_phone(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_phone)
    await callback.message.edit_text(
        "Step 3 of 12\nYour phone number:",
        reply_markup=get_form_back_keyboard("back_to_last_name")
    )


@router.callback_query(F.data == "back_to_passport_number")
async def back_to_passport_number(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_passport_number)
    await callback.message.edit_text(
        "Step 4 of 12\nPassport number:",
        reply_markup=get_form_back_keyboard("back_to_phone")
    )


@router.callback_query(F.data == "back_to_birth_date")
async def back_to_birth_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_birth_date)
    await callback.message.edit_text(
        "Step 5 of 12\nDate of birth (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_passport_number")
    )


@router.callback_query(F.data == "back_to_passport_country")
async def back_to_passport_country(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_passport_country)
    await callback.message.edit_text(
        "Step 6 of 12\nCountry of passport issuance:",
        reply_markup=get_form_back_keyboard("back_to_birth_date")
    )


@router.callback_query(F.data == "back_to_issue_date")
async def back_to_issue_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_issue_date)
    await callback.message.edit_text(
        "Step 7 of 12\nPassport issue date (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_passport_country")
    )


@router.callback_query(F.data == "back_to_expiry_date")
async def back_to_expiry_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_expiry_date)
    await callback.message.edit_text(
        "Step 8 of 12\nPassport expiration date (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_issue_date")
    )


@router.callback_query(F.data == "back_to_departure_from")
async def back_to_departure_from(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_departure_from)
    await callback.message.edit_text(
        "Step 9 of 12\nWhere are you planning to fly from?",
        reply_markup=get_form_back_keyboard("back_to_expiry_date")
    )


@router.callback_query(F.data == "back_to_return_to")
async def back_to_return_to(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_return_to)
    await callback.message.edit_text(
        "Step 10 of 12\nWhere are you planning to return to?",
        reply_markup=get_form_back_keyboard("back_to_departure_from")
    )


@router.callback_query(F.data == "back_to_baggage")
async def back_to_baggage(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_baggage)
    keyboard = get_baggage_keyboard("back_to_return_to")
    await callback.message.edit_text(
        "Step 11 of 12\nDo you need checked baggage?",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "back_to_per_diem_type")
async def back_to_per_diem_type(callback: CallbackQuery, state: FSMContext):
    await start_per_diem_form(callback, state)


@router.callback_query(F.data == "back_to_per_diem_network")
async def back_to_per_diem_network(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_per_diem_crypto_network)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TRC20", callback_data="crypto_trc20")],
        [InlineKeyboardButton(text="ERC20", callback_data="crypto_erc20")],
        [InlineKeyboardButton(text="BEP20", callback_data="crypto_bep20")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_type")]
    ])
    await callback.message.edit_text("🪙 Select your wallet network:", reply_markup=keyboard)