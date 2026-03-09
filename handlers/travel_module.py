import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from typing import List, Dict, Any
import re

import os
from handlers.managers_chat import send_question_to_manager

TRAVEL_MANAGER_CHAT_ID = int(os.getenv("TG_TRAVEL_MANAGER_CHAT_ID", 0))

router = Router()
logger = logging.getLogger(__name__)


# Состояния для Travel
class TravelStates(StatesGroup):
    english = State()  # Основное состояние для англоязычного интерфейса
    # Состояния для форм
    waiting_for_passport = State()
    waiting_for_city_from = State()
    waiting_for_city_to = State()
    waiting_for_baggage = State()
    waiting_for_preferences = State()
    waiting_for_visa_status = State()

    waiting_for_travel_question = State()

    waiting_for_flight_request = State()
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

    waiting_for_per_diem_payment = State()
    waiting_for_per_diem_currency = State()
    waiting_for_per_diem_comments = State()
    waiting_for_per_diem_consent = State()


def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)


# ============================================
# КЛАВИАТУРЫ (ТОЛЬКО АНГЛИЙСКИЕ)
# ============================================

def get_travel_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # 1. Самая большая кнопка
    builder.row(
        InlineKeyboardButton(text="✈️ Flight Request", callback_data="travel_flight_request")
    )
    # 2. Ряд из двух
    builder.row(
        InlineKeyboardButton(text="🛂 Visa Support", callback_data="travel_visa_support"),
        InlineKeyboardButton(text="ℹ️ Flight Info", callback_data="travel_flight_info")
    )
    # 3. Ряд из двух
    builder.row(
        InlineKeyboardButton(text="🏨 Hotel", callback_data="travel_hotel_info"),
        InlineKeyboardButton(text="💰 Daily allowance", callback_data="travel_per_diem")
    )
    # 4. Ряд из двух
    builder.row(
        InlineKeyboardButton(text="📋 My requests", callback_data="travel_my_requests"),
        InlineKeyboardButton(text="❓ Question", callback_data="travel_question")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="menu_main")
    )
    return builder.as_markup()


async def get_conference_keyboard(conferences: List[str], has_data: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура выбора конференции"""
    builder = InlineKeyboardBuilder()

    for conf in conferences:
        builder.row(InlineKeyboardButton(text=f"{conf}", callback_data=f"travel_conf_{conf}"))

    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    return builder.as_markup()


def get_conference_back_keyboard(conference: str) -> InlineKeyboardMarkup:
    """Клавиатура после выбора конференции (только для рейсов)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_flight_info"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    return builder.as_markup()


def get_hotel_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора отеля"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    return builder.as_markup()


def get_hotel_back_keyboard(conference: str) -> InlineKeyboardMarkup:
    """Клавиатура для возврата из информации об отеле"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_hotel_info"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
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


def get_form_back_keyboard(back_to: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для форм"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data=back_to),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    return builder.as_markup()


# ============================================
# ТЕКСТОВЫЕ ШАБЛОНЫ (ТОЛЬКО АНГЛИЙСКИЕ)
# ============================================

TEXTS = {
    'welcome': "✈️ TRAVEL Section\n\nChoose an option:",
    'flight_choose': "Select the event you are going to:",
    'flight_no_data': "It seems that no information has been found about you 👀\n\nPlease contact travel manager for assistance.",
    'hotel_no_data': "Accommodation information not found for this conference.",
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
    'registration_info': '''📌 *Check-in*

You can check in for your flight *24 hours before departure* using this link:''',
    'registration_airline': '''*{airline}*: {checkin_url}
''',
    'final_text': '''If an *email* is requested: travel@conference.com

_I wish you a great flight and productive business trip!_ 🔥''',
    'visa_support': '''🛂 Visa Support

Choose your status:''',
    'visa_instructions': '''📋 Visa Application Instructions:

1. Prepare documents:
   • Passport (valid for at least 6 months)
   • 2 passport photos
   • Conference invitation
   • Employment certificate
   • Bank statement

2. Recommended agencies:
   • VisaMaster: +7 (999) 111-11-11
   • TravelDocs: +7 (999) 222-22-22

⚠️ Conference organizers are not responsible for agency services.

3. After receiving visa, update your status below:''',
    'per_diem': '''💰 Per Diem

Information about per diem payments will be available closer to the conference date.

For questions, contact: finance@conference.com''',
    'question': '''❓ Question to Travel Manager

✉️ Email: travel@conference.com
📱 Telegram: @travel_manager

We respond within 24 hours.''',
    'useful_info': '''🛩️ Useful Information

• Arrive at airport 3 hours before check-in
• Keep your passport and booking reference handy
• Download airline's mobile app for updates

Popular taxi services:
• Asia: Grab, Bolt, Gojek
• Europe: Uber, Bolt, Free Now
• USA: Uber, Lyft''',
    'flight_form': '''✈️ Flight Ticket Request

Step {step} of 5
{question}''',
    'form_complete': '''✅ Flight request submitted!

Thank you for your request. Our travel team will contact you within 24 hours to discuss details.''',
    'hotel_booking': '''🏨 Hotel Information

Hotel booking is managed by our travel team. You will receive confirmation 2 weeks before the conference.

For urgent inquiries, contact: hotels@conference.com'''
}


# ============================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ МЕНЮ
# ============================================

@router.callback_query(F.data == "menu_travel")
async def show_travel_menu(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню Travel"""
    await state.set_state(TravelStates.english)
    keyboard = get_travel_menu_keyboard()
    await callback.message.edit_text(
        TEXTS['welcome'],
        reply_markup=keyboard
    )


@router.callback_query(F.data == "travel_back_to_menu")
async def back_to_travel_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню Travel"""
    await state.set_state(TravelStates.english)
    keyboard = get_travel_menu_keyboard()
    await callback.message.edit_text(
        TEXTS['welcome'],
        reply_markup=keyboard
    )


# ============================================
# FLIGHT INFORMATION (информация о рейсах)
# ============================================

@router.callback_query(F.data == "travel_flight_info")
async def show_flight_info(callback: CallbackQuery):
    """Показать информацию о рейсах"""
    username = callback.from_user.username

    if not username:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
        ])
        await callback.message.edit_text(
            "Please set up your Telegram username first in Settings → Username",
            reply_markup=keyboard
        )
        return

    try:
        print(f"Fetching conferences for username: {username}")

        # Получаем конференции пользователя из whitelist
        conferences = await db.get_user_active_conferences(username)

        if not conferences:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
                 InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")]
            ])
            await callback.message.edit_text(
                "No conferences found for your account. Please contact your manager.",
                reply_markup=keyboard
            )
            return

        # Создаем клавиатуру с конференциями пользователя
        builder = InlineKeyboardBuilder()
        for conf in conferences:
            builder.row(InlineKeyboardButton(text=f"📅 {conf}", callback_data=f"travel_conf_{conf}"))

        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
            InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
        )

        await callback.message.edit_text(
            "Select the conference you are attending:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error getting flight info: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
             InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")]
        ])
        await callback.message.edit_text(
            "Error fetching conference data. Please try again later.",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("travel_conf_"))
async def show_conference_details(callback: CallbackQuery, state: FSMContext):
    """Показать детали рейсов для выбранной конференции"""
    conference = callback.data.split('travel_conf_')[1]
    username = callback.from_user.username

    try:
        # Получаем рейсы для конференции из схемы travel_bot
        flights = await db.get_flight_details_travel(username, conference)

        if not flights:
            text = TEXTS['flight_no_data']
        else:
            # Формируем текст с информацией о рейсах
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

            # Добавляем информацию о регистрации
            text += "\n" + TEXTS['registration_info'] + "\n\n"

            # Добавляем ссылки на авиакомпании
            airlines = set([f.get('airline') for f in flights if f.get('airline')])
            for airline in airlines:
                checkin_url = await db.get_airline_url_travel(airline)
                if not checkin_url:
                    checkin_url = "https://checkin.airline.com"

                airline_escaped = escape_markdown(airline or "Airline")
                url_escaped = escape_markdown(checkin_url)

                text += TEXTS['registration_airline'].format(
                    airline=airline_escaped,
                    checkin_url=url_escaped
                )

            text += "\n" + TEXTS['final_text']

        # Получаем клавиатуру
        keyboard = get_conference_back_keyboard(conference)

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

        # Сохраняем конференцию в состоянии для кнопки "Отель"
        await state.update_data(selected_conference=conference)

    except Exception as e:
        logger.error(f"Error showing conference flights: {e}")
        await callback.message.edit_text(
            "Error loading flight details. Please try again.",
            reply_markup=get_conference_back_keyboard(conference)
        )


# ============================================
# HOTEL INFORMATION (информация об отеле)
# ============================================

async def get_hotel_conference_keyboard(conferences: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура выбора конференции для отеля"""
    builder = InlineKeyboardBuilder()

    for conf in conferences:
        builder.row(InlineKeyboardButton(text=f"{conf}", callback_data=f"travel_hotel_{conf}"))

    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )
    return builder.as_markup()


@router.callback_query(F.data == "travel_hotel_info")
async def show_hotel_menu(callback: CallbackQuery):
    """Показать меню выбора конференции для отеля"""
    username = callback.from_user.username

    if not username:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
        ])
        await callback.message.edit_text(
            "Please set up your Telegram username first in Settings → Username",
            reply_markup=keyboard
        )
        return

    try:
        # Получаем конференции пользователя из whitelist
        conferences = await db.get_user_active_conferences(username)

        if not conferences:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
                 InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")]
            ])
            await callback.message.edit_text(
                "No conferences found for your account.",
                reply_markup=keyboard
            )
            return

        # Создаем клавиатуру с конференциями
        builder = InlineKeyboardBuilder()
        for conf in conferences:
            builder.row(InlineKeyboardButton(text=f"🏨 {conf}", callback_data=f"travel_hotel_{conf}"))

        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu"),
            InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
        )

        await callback.message.edit_text(
            "🏨 Hotel Information\n\nSelect the conference:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error getting hotel conferences: {e}")
        await callback.message.edit_text(
            "Error loading hotel information.",
            reply_markup=get_hotel_menu_keyboard()
        )


@router.callback_query(F.data.startswith("travel_hotel_"))
async def show_hotel_details(callback: CallbackQuery):
    """Показать детали отеля для конференции"""
    conference = callback.data.split('travel_hotel_')[1]

    try:
        # Получаем информацию об отеле из схемы travel_bot
        hotel_data = await db.get_hotel_info_travel(conference)

        if hotel_data and hotel_data.get('hotel'):
            text = TEXTS['hotel_info'].format(
                hotel_name=hotel_data.get('hotel', 'Hotel'),
                hotel_address=hotel_data.get('address', 'Address not specified'),
                hotel_link=hotel_data.get('site', ''),
                conference=conference
            )
        else:
            text = TEXTS['hotel_no_data']

        keyboard = get_hotel_back_keyboard(conference)

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error showing hotel info: {e}")
        await callback.message.edit_text(
            "Error loading hotel information.",
            reply_markup=get_hotel_back_keyboard(conference)
        )


# ============================================
# VISA SUPPORT (визовая поддержка)
# ============================================

@router.callback_query(F.data == "travel_visa_support")
async def show_visa_support(callback: CallbackQuery):
    """Показать меню визовой поддержки"""
    keyboard = get_visa_keyboard()

    await callback.message.edit_text(
        TEXTS['visa_support'],
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("visa_"))
async def process_visa_status(callback: CallbackQuery, state: FSMContext):
    """Обработать выбор статуса визы"""
    visa_status = callback.data.replace("visa_", "")

    if visa_status == "not_have":
        # ИНСТРУКЦИИ ПО ПОЛУЧЕНИЮ ВИЗЫ (ПОЛНАЯ ВЕРСИЯ)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить статус визы", callback_data="visa_update_status")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_visa_support")]
        ])

        visa_instructions = '''📋 *Visa Application Instructions*

    1️⃣ *Required documents:*
       • Passport (valid at least 6 months)
       • 2 passport-size photos (3.5x4.5 cm, white background)
       • Conference invitation (we'll provide)
       • Employment certificate with salary
       • Bank statement (last 3 months, min $1000 balance)
       • Hotel booking confirmation
       • Flight itinerary
       • Medical insurance ($50,000+ coverage)
       • Visa application form

    2️⃣ *Checklist before submission:*
       ☐ All documents translated to English
       ☐ Copies of passport pages (1-3, last page)
       ☐ Photos meet requirements
       ☐ Bank statement stamped
       ☐ Hotel booking matches conference dates

    3️⃣ *Recommended agencies:*
       • VisaMaster: +7 (999) 111-11-11 (5-7 business days)
       • TravelDocs: +7 (999) 222-22-22 (express service available)
       • QuickVisa: +7 (999) 333-33-33 (premium service)

    ⚠️ *Disclaimer:*
    Conference organizers are not responsible for:
    • Agency service quality/timing
    • Visa approval/rejection decisions
    • Additional fees charged by agencies

    4️⃣ *After receiving visa:*
    • Check visa dates match your travel
    • Ensure name spelling is correct
    • Click "Update visa status" below'''

        await callback.message.edit_text(
            visa_instructions,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Начинаем форму запроса билета
        await state.set_state(TravelStates.waiting_for_passport)
        await state.update_data(visa_status=visa_status)

        keyboard = get_form_back_keyboard("travel_visa_support")

        await callback.message.edit_text(
            TEXTS['flight_form'].format(
                step=1,
                question="Please provide passport details for ticket booking:"
            ),
            reply_markup=keyboard
        )

@router.callback_query(F.data == "visa_update_status")
async def update_visa_status_form(callback: CallbackQuery, state: FSMContext):
    """Форма обновления статуса визы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Visa received", callback_data="visa_received")],
        [InlineKeyboardButton(text="⏳ Still waiting", callback_data="visa_waiting")],
        [InlineKeyboardButton(text="❌ Visa rejected", callback_data="visa_rejected")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="travel_visa_support")]
    ])

    await callback.message.edit_text(
        "🔄 *Update Visa Status*\n\n"
        "Please select your current visa status:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("visa_"))
async def process_visa_update(callback: CallbackQuery):
    """Обработка обновления статуса визы"""
    status_map = {
        "visa_received": "✅ Visa received",
        "visa_waiting": "⏳ Still waiting",
        "visa_rejected": "❌ Visa rejected"
    }

    status_text = status_map.get(callback.data, "Unknown")

    # Сохраняем в БД
    await db.log_user_action(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        action="visa_status_updated",
        details={"new_status": callback.data.replace("visa_", "")}
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Continue with flight request", callback_data="travel_visa_support")],
        [InlineKeyboardButton(text="◀️ Back to Travel", callback_data="travel_back_to_menu")]
    ])

    await callback.message.edit_text(
        f"✅ *Status updated:* {status_text}\n\n"
        f"Thank you for updating your visa status. "
        f"This information helps our travel team assist you better.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data == "travel_my_requests")
async def show_my_travel_requests(callback: CallbackQuery):
    """Показать статусы заявок пользователя"""
    username = callback.from_user.username

    try:
        # Получаем статусы
        visa_status = await db.get_travel_request_status(username, "visa")
        flight_status = await db.get_travel_request_status(username, "flight")

        status_text = "📋 *Your Travel Requests*\n\n"

        # Visa request
        if visa_status["status"] == "pending":
            status_text += f"🛂 *Visa Support:* ⏳ Processing\n"
            status_text += f"   Submitted: {visa_status['submitted']}\n\n"
        elif visa_status["status"] == "no_requests":
            status_text += f"🛂 *Visa Support:* 📝 No requests yet\n\n"

        # Flight request
        if flight_status["status"] == "pending":
            status_text += f"✈️ *Flight Request:* ⏳ Processing\n"
            status_text += f"   Submitted: {flight_status['submitted']}\n\n"
        elif flight_status["status"] == "no_requests":
            status_text += f"✈️ *Flight Request:* 📝 No requests yet\n\n"

        status_text += "\n_You will receive notifications when status changes._"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Check again", callback_data="travel_my_requests")],
            [InlineKeyboardButton(text="📝 New request", callback_data="travel_visa_support")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
        ])

        await callback.message.edit_text(
            status_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error showing travel requests: {e}")
        await callback.message.edit_text(
            "❌ Error loading your requests. Please try again.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
            ])
        )

# ============================================
# FLIGHT REQUEST FORM (форма запроса билета)
# ============================================

@router.message(TravelStates.waiting_for_passport)
async def process_passport(message: Message, state: FSMContext):
    """Обработать паспортные данные"""
    await state.update_data(passport_data=message.text)
    await state.set_state(TravelStates.waiting_for_city_from)

    keyboard = get_form_back_keyboard("travel_visa_support")

    await message.answer(
        TEXTS['flight_form'].format(
            step=2,
            question="Departure city:"
        ),
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_city_from)
async def process_city_from(message: Message, state: FSMContext):
    """Обработать город отправления"""
    await state.update_data(city_from=message.text)
    await state.set_state(TravelStates.waiting_for_city_to)

    keyboard = get_form_back_keyboard("visa_back_step2")

    await message.answer(
        TEXTS['flight_form'].format(
            step=3,
            question="Destination city:"
        ),
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_city_to)
async def process_city_to(message: Message, state: FSMContext):
    """Обработать город назначения"""
    await state.update_data(city_to=message.text)
    await state.set_state(TravelStates.waiting_for_baggage)

    keyboard = get_baggage_keyboard("visa_back_step3")

    await message.answer(
        TEXTS['flight_form'].format(
            step=4,
            question="Do you need checked baggage?"
        ),
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("baggage_"), TravelStates.waiting_for_baggage)
async def process_baggage(callback: CallbackQuery, state: FSMContext):
    """Обработать выбор багажа"""
    needs_baggage = callback.data == "baggage_yes"
    await state.update_data(needs_baggage=needs_baggage)
    await state.set_state(TravelStates.waiting_for_preferences)

    keyboard = get_form_back_keyboard("visa_back_step4")

    await callback.message.edit_text(
        TEXTS['flight_form'].format(
            step=5,
            question="Any preferences (dates, times, airlines, etc.):"
        ),
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_preferences)
async def process_preferences(message: Message, state: FSMContext):
    """Обработка предпочтений и сохранение заявки"""
    await state.update_data(preferences=message.text)
    data = await state.get_data()

    # Сохраняем в БД
    flight_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'visa_status': data.get('visa_status'),
        'passport_data': data.get('passport_data'),
        'city_from': data.get('city_from'),
        'city_to': data.get('city_to'),
        'needs_baggage': data.get('needs_baggage', False),
        'preferences': data.get('preferences')
    }

    if await db.save_visa_request(flight_data):
        # ОТПРАВЛЯЕМ ЧЕК-ЛИСТ ПОСЛЕ ОТПРАВКИ
        checklist = (
            "✅ *Request submitted successfully!*\n\n"
            "📋 *Next steps checklist:*\n"
            "1. Check your Telegram notifications for updates\n"
            "2. If you need visa: start document collection\n"
            "3. Monitor email for ticket confirmations\n"
            "4. Click 'My Requests' to check status\n\n"
            "⏰ *Expected timeline:*\n"
            "• Flight tickets: 1-3 business days\n"
            "• Visa processing: 5-10 business days\n"
            "• Hotel booking: 2-4 business days\n\n"
            "_Our travel team will contact you soon._"
        )

        await message.answer(
            checklist,
            parse_mode=ParseMode.MARKDOWN
        )

        # Логируем действие
        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="flight_request_submitted",
            details={"conference": "flight_request"}
        )
    else:
        await message.answer("❌ Error saving request. Please try again later.")

    await state.clear()


# ============================================
# PER DIEM (суточные)
# ============================================

@router.callback_query(F.data == "travel_per_diem")
async def start_per_diem_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы суточных по ТЗ"""
    await state.set_state(TravelStates.waiting_for_per_diem_payment)
    keyboard = get_form_back_keyboard("travel_back_to_menu")

    await callback.message.edit_text(
        "💰 Per Diem Form\n\n"
        "Step 1 of 4\n"
        "Specify payment details (IBAN/card number/method) / "
        "Укажи реквизиты для выплаты (IBAN/номер карты/способ):",
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_per_diem_payment)
async def process_per_diem_payment(message: Message, state: FSMContext):
    """Шаг 1: Реквизиты для выплаты"""
    await state.update_data(payment_details=message.text)
    await state.set_state(TravelStates.waiting_for_per_diem_currency)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="USD", callback_data="currency_usd")],
        [InlineKeyboardButton(text="EUR", callback_data="currency_eur")],
        [InlineKeyboardButton(text="RUB", callback_data="currency_rub")],
        [InlineKeyboardButton(text="AED", callback_data="currency_aed")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_start")]
    ])

    await message.answer(
        "Step 2 of 4\n"
        "Specify required currency / Укажи необходимую валюту:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("currency_"), TravelStates.waiting_for_per_diem_currency)
async def process_per_diem_currency(callback: CallbackQuery, state: FSMContext):
    """Шаг 2: Выбор валюты"""
    currency = callback.data.replace("currency_", "").upper()
    await state.update_data(currency=currency)
    await state.set_state(TravelStates.waiting_for_per_diem_comments)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Skip / Пропустить", callback_data="skip_comments")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_payment")]
    ])

    await callback.message.edit_text(
        "Step 3 of 4\n"
        "Additional comments / Дополнительные комментарии "
        "(or click 'Skip'):",
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_per_diem_comments)
async def process_per_diem_comments(message: Message, state: FSMContext):
    """Шаг 3: Комментарии"""
    await state.update_data(comments=message.text)
    await state.set_state(TravelStates.waiting_for_per_diem_consent)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I consent / Даю согласие", callback_data="per_diem_consent")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_currency")]
    ])

    await message.answer(
        "Step 4 of 4\n\n"
        "✅ I consent to the processing of personal data / "
        "✅ Даю согласие на обработку персональных данных\n\n"
        "Please confirm your consent:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "skip_comments")
async def skip_per_diem_comments(callback: CallbackQuery, state: FSMContext):
    """Пропустить комментарии"""
    await state.update_data(comments="-")
    await state.set_state(TravelStates.waiting_for_per_diem_consent)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I consent / Даю согласие", callback_data="per_diem_consent")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_currency")]
    ])

    await callback.message.edit_text(
        "Step 4 of 4\n\n"
        "✅ I consent to the processing of personal data / "
        "✅ Даю согласие на обработку персональных данных\n\n"
        "Please confirm your consent:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "per_diem_consent")
async def process_per_diem_consent(callback: CallbackQuery, state: FSMContext):
    """Шаг 4: Подтверждение согласия и сохранение"""
    data = await state.get_data()

    # Сохраняем в БД
    per_diem_data = {
        'username': callback.from_user.username,
        'user_id': callback.from_user.id,
        'payment_details': data.get('payment_details'),
        'currency': data.get('currency'),
        'comments': data.get('comments', '-'),
        'consent_given': True
    }

    # TODO: Вызов метода save_per_diem_request (нужно создать в database.py)
    # if await db.save_per_diem_request(per_diem_data):

    await callback.message.edit_text(
        "✅ Per diem request submitted!\n\n"
        "Thank you for your request. Our finance team will process your payment details "
        "and contact you if additional information is needed.\n\n"
        "For questions, contact: finance@conference.com"
    )

    # Логируем действие
    await db.log_user_action(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        action="per_diem_request_submitted",
        details={"currency": data.get('currency')}
    )

    await state.clear()


@router.callback_query(F.data == "back_to_per_diem_start")
async def back_to_per_diem_start(callback: CallbackQuery, state: FSMContext):
    """Назад к началу формы"""
    await start_per_diem_form(callback, state)


@router.callback_query(F.data == "back_to_per_diem_payment")
async def back_to_per_diem_payment(callback: CallbackQuery, state: FSMContext):
    """Назад к шагу 1 (реквизиты)"""
    await state.set_state(TravelStates.waiting_for_per_diem_payment)
    keyboard = get_form_back_keyboard("travel_back_to_menu")

    await callback.message.edit_text(
        "Step 1 of 4\n"
        "Specify payment details (IBAN/card number/method) / "
        "Укажи реквизиты для выплаты (IBAN/номер карты/способ):",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "back_to_per_diem_currency")
async def back_to_per_diem_currency(callback: CallbackQuery, state: FSMContext):
    """Назад к шагу 2 (валюта)"""
    data = await state.get_data()
    await state.set_state(TravelStates.waiting_for_per_diem_currency)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="USD", callback_data="currency_usd")],
        [InlineKeyboardButton(text="EUR", callback_data="currency_eur")],
        [InlineKeyboardButton(text="RUB", callback_data="currency_rub")],
        [InlineKeyboardButton(text="AED", callback_data="currency_aed")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_per_diem_payment")]
    ])

    await callback.message.edit_text(
        "Step 2 of 4\n"
        f"Current selection: {data.get('currency', 'Not selected')}\n"
        "Specify required currency / Укажи необходимую валюту:",
        reply_markup=keyboard
    )


# ============================================
# QUESTION TO MANAGER (вопрос менеджеру)
# ============================================

@router.callback_query(F.data == "travel_question")
async def show_question(callback: CallbackQuery, state: FSMContext):
    """Показать форму вопроса к travel-менеджеру"""
    await state.set_state(TravelStates.waiting_for_travel_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="travel_back_to_menu")]
    ])

    await callback.message.edit_text(
        "❓ Question to Travel Manager\n\n"
        "Please write your question (max 500 characters):",
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_travel_question, F.text.len() <= 500)
async def process_travel_question(message: Message, state: FSMContext):
    """Обработка вопроса к travel-менеджеру"""
    question_text = message.text
    username = message.from_user.username
    user_id = message.from_user.id

    travel_question_data = {
        'username': username,
        'user_id': user_id,
        'category': 'travel_general',
        'question': question_text
    }

    # Сохраняем в БД
    if await db.save_travel_question(travel_question_data):
        # Отправляем в чат travel-менеджера
        await send_question_to_manager(
            bot=message.bot,  # Используем message.bot
            manager_chat_id=TRAVEL_MANAGER_CHAT_ID,
            user_data=travel_question_data,
            question_text=question_text,
            question_type="travel"
        )

        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="travel_question_submitted",
            details={"data": travel_question_data}
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Travel Menu", callback_data="travel_back_to_menu")]
        ])

        await message.answer(
            "✅ Question sent!\n\n"
            "Thank you for your question. Our travel team will contact you soon.",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Travel Menu", callback_data="travel_back_to_menu")]
        ])
        await message.answer(
            "❌ Error saving question. Please try again later.",
            reply_markup=keyboard
        )

    await state.clear()


@router.message(TravelStates.waiting_for_travel_question, F.text.len() > 500)
async def process_travel_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    await message.answer("❌ Question is too long. Maximum 500 characters.")


# ============================================
# BACK BUTTON HANDLERS (обработчики кнопок назад)
# ============================================

@router.callback_query(F.data == "visa_back_step2")
async def back_to_step2(callback: CallbackQuery, state: FSMContext):
    """Назад к шагу 2"""
    await state.set_state(TravelStates.waiting_for_passport)
    keyboard = get_form_back_keyboard("travel_visa_support")

    await callback.message.edit_text(
        TEXTS['flight_form'].format(
            step=1,
            question="Please provide passport details for ticket booking:"
        ),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "visa_back_step3")
async def back_to_step3(callback: CallbackQuery, state: FSMContext):
    """Назад к шагу 3"""
    await state.set_state(TravelStates.waiting_for_city_from)
    keyboard = get_form_back_keyboard("travel_visa_support")

    await callback.message.edit_text(
        TEXTS['flight_form'].format(
            step=2,
            question="Departure city:"
        ),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "visa_back_step4")
async def back_to_step4(callback: CallbackQuery, state: FSMContext):
    """Назад к шагу 4"""
    await state.set_state(TravelStates.waiting_for_city_to)
    keyboard = get_form_back_keyboard("visa_back_step2")

    await callback.message.edit_text(
        TEXTS['flight_form'].format(
            step=3,
            question="Destination city:"
        ),
        reply_markup=keyboard
    )


# ============================================
# FLIGHT REQUEST FORM (полная форма)
# ============================================

@router.callback_query(F.data == "travel_flight_request")
async def start_flight_request(callback: CallbackQuery, state: FSMContext):
    """Начало формы запроса билета"""
    await state.set_state(TravelStates.waiting_for_first_name)
    keyboard = get_form_back_keyboard("travel_back_to_menu")

    await callback.message.edit_text(
        "✈️ Flight Request Form\n\n"
        "Step 1 of 13\n"
        "Your first name as in your passport / Ваше имя как в загранпаспорте:",
        reply_markup=keyboard
    )


@router.message(TravelStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await state.set_state(TravelStates.waiting_for_last_name)
    await message.answer(
        "Step 2 of 13\n"
        "Your last name as in your passport / Ваша фамилия как в загранпаспорте:",
        reply_markup=get_form_back_keyboard("travel_flight_request")
    )


@router.message(TravelStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await state.set_state(TravelStates.waiting_for_phone)
    await message.answer(
        "Step 3 of 13\n"
        "Your phone number / Ваш номер телефона:",
        reply_markup=get_form_back_keyboard("back_to_first_name")
    )


@router.message(TravelStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(TravelStates.waiting_for_passport_number)
    await message.answer(
        "Step 4 of 13\n"
        "Passport number / Номер загранпаспорта:",
        reply_markup=get_form_back_keyboard("back_to_last_name")
    )


@router.message(TravelStates.waiting_for_passport_number)
async def process_passport_number(message: Message, state: FSMContext):
    await state.update_data(passport_number=message.text)
    await state.set_state(TravelStates.waiting_for_birth_date)
    await message.answer(
        "Step 5 of 13\n"
        "Date of birth / Дата рождения (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_phone")
    )


@router.message(TravelStates.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    await state.update_data(birth_date=message.text)
    await state.set_state(TravelStates.waiting_for_passport_country)
    await message.answer(
        "Step 6 of 13\n"
        "Country of passport issuance / Страна выдачи загранпаспорта:",
        reply_markup=get_form_back_keyboard("back_to_passport_number")
    )


@router.message(TravelStates.waiting_for_passport_country)
async def process_passport_country(message: Message, state: FSMContext):
    await state.update_data(passport_country=message.text)
    await state.set_state(TravelStates.waiting_for_issue_date)
    await message.answer(
        "Step 7 of 13\n"
        "Passport issue date / Дата выдачи загранпаспорта (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_birth_date")
    )


@router.message(TravelStates.waiting_for_issue_date)
async def process_issue_date(message: Message, state: FSMContext):
    await state.update_data(issue_date=message.text)
    await state.set_state(TravelStates.waiting_for_expiry_date)
    await message.answer(
        "Step 8 of 13\n"
        "Passport expiration date / Дата окончания срока действия загранпаспорта (DD.MM.YYYY):",
        reply_markup=get_form_back_keyboard("back_to_passport_country")
    )


@router.message(TravelStates.waiting_for_expiry_date)
async def process_expiry_date(message: Message, state: FSMContext):
    await state.update_data(expiry_date=message.text)
    await state.set_state(TravelStates.waiting_for_departure_from)
    await message.answer(
        "Step 9 of 13\n"
        "Where are you planning to fly to Dubai from? / Откуда планируете вылетать в Дубай?:",
        reply_markup=get_form_back_keyboard("back_to_issue_date")
    )


@router.message(TravelStates.waiting_for_departure_from)
async def process_departure_from(message: Message, state: FSMContext):
    await state.update_data(departure_from=message.text)
    await state.set_state(TravelStates.waiting_for_return_to)
    await message.answer(
        "Step 10 of 13\n"
        "Where are you planning to return from Dubai? / Куда планируете возвращаться из Дубай?:",
        reply_markup=get_form_back_keyboard("back_to_expiry_date")
    )


@router.message(TravelStates.waiting_for_return_to)
async def process_return_to(message: Message, state: FSMContext):
    await state.update_data(return_to=message.text)
    await state.set_state(TravelStates.waiting_for_visa_needed)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes", callback_data="visa_yes")],
        [InlineKeyboardButton(text="❌ No", callback_data="visa_no")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_departure_from")]
    ])

    await message.answer(
        "Step 11 of 13\n"
        "Do you need a visa to visit UAE? / Нужна ли вам виза для посещения ОАЭ?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("visa_"), TravelStates.waiting_for_visa_needed)
async def process_visa_needed(callback: CallbackQuery, state: FSMContext):
    needs_visa = callback.data == "visa_yes"
    await state.update_data(needs_visa=needs_visa)

    await state.set_state(TravelStates.waiting_for_visa_dates)
    await callback.message.edit_text(
        "Step 12 of 13\n"
        "If you have already received a visa, please indicate its start and end dates / "
        "Если вы уже получили визу, пожалуйста, напишите дату ее начала и окончания "
        "(или '-' если не применимо):",
        reply_markup=get_form_back_keyboard("back_to_visa_question")
    )
    # else:
    #     # Пропускаем вопрос о датах визы
    #     await state.update_data(visa_dates="-")
    #     await save_flight_request_data(callback.message, state)


async def save_flight_request_data(message: Message, state: FSMContext):
    """Сохранение данных формы Flight Request"""
    data = await state.get_data()

    # Сохраняем в БД
    flight_request_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
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
        'needs_visa': data.get('needs_visa', False),
        'visa_dates': data.get('visa_dates', '-')
    }

    # TODO: Создать метод save_flight_request в database.py
    # if await db.save_flight_request(flight_request_data):

    await message.answer(
        "✅ Flight request submitted!\n\n"
        "Thank you for your detailed information. "
        "Our travel team will contact you within 24 hours to discuss flight options."
    )

    # Логируем действие
    await db.log_user_action(
        user_id=message.from_user.id,
        username=message.from_user.username,
        action="flight_request_submitted",
        details={"form": "full_flight_request"}
    )

    await state.clear()


@router.message(TravelStates.waiting_for_visa_dates)
async def process_visa_dates(message: Message, state: FSMContext):
    await state.update_data(visa_dates=message.text)
    await save_flight_request_data(message, state)


# ============================================
# BACK BUTTONS FOR FLIGHT REQUEST
# ============================================

@router.callback_query(F.data == "back_to_first_name")
async def back_to_first_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TravelStates.waiting_for_first_name)
    keyboard = get_form_back_keyboard("travel_back_to_menu")

    await callback.message.edit_text(
        "Step 1 of 13\n"
        "Your first name as in your passport / Ваше имя как в загранпаспорте:",
        reply_markup=keyboard
    )


# Добавьте аналогичные обработчики для остальных back кнопок:
# back_to_last_name, back_to_phone, back_to_passport_number, и т.д.

# ============================================
# УТИЛИТЫ
# ============================================

@router.callback_query(F.data == "visa_update_status")
async def update_visa_status(callback: CallbackQuery):
    """Обновить статус визы"""
    await show_visa_support(callback)