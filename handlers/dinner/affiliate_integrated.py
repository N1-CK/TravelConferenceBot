# handlers/dinner/affiliate_integrated.py - ПОЛНЫЙ ФАЙЛ С ПРАВКАМИ
import logging
import os
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Union, Optional

import asyncio
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from keyboards import get_main_menu_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from database import db


router = Router()
logger = logging.getLogger(__name__)


# ============================================
# DECORATORS AND AUTHORIZATION
# ============================================

def affiliate_auth_required(func):
    """Decorator for affiliate module access check"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        update = args[0]
        username = update.from_user.username

        if not username:
            if isinstance(update, Message):
                await update.answer("Please set username in Telegram")
            elif isinstance(update, CallbackQuery):
                await update.answer("Username required", show_alert=True)
            return

        if not await db.check_affiliate_auth(username):
            if isinstance(update, Message):
                await update.answer("For access to partner dinners, use /affiliate_start")
            elif isinstance(update, CallbackQuery):
                await update.answer("Authorization required /affiliate_start", show_alert=True)
            return

        return await func(*args, **kwargs)

    return wrapper


# ============================================
# AUTH COMMANDS
# ============================================

class AffiliateAuthStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_company = State()


@router.message(Command("affiliate_start"))
async def affiliate_start_command(msg: Message, state: FSMContext):
    """Start affiliate module authorization"""
    username = msg.from_user.username

    if not username:
        await msg.answer("Please set username in Telegram settings")
        return

    if await db.check_affiliate_auth(username):
        await show_affiliate_main_menu(msg)  # Оставляем как есть для Message
    else:
        await state.set_state(AffiliateAuthStates.waiting_for_password)
        await msg.answer("Enter password for partner dinners access:")


# В функции process_affiliate_password заменить клавиатуру на текстовый запрос:

@router.message(AffiliateAuthStates.waiting_for_password)
async def process_affiliate_password(msg: Message, state: FSMContext):
    """Process password"""
    password = os.getenv('AFFILIATE_PASSWORD', 'affil123')

    if msg.text == password:
        await msg.answer("Password correct! Enter your partner program name:")
        await state.set_state(AffiliateAuthStates.waiting_for_company)
    else:
        await msg.answer("Wrong password. Try again.")


@router.message(AffiliateAuthStates.waiting_for_company)
async def process_affiliate_company(msg: Message, state: FSMContext):
    """Process company selection - ТЕКСТОВЫЙ ВВОД как в оригинале"""
    username = msg.from_user.username
    company_input = msg.text.strip()

    if not company_input:
        await msg.answer("Company name cannot be empty. Please enter your partner program name:")
        return

    companies_list = os.getenv('COMPANIES_LIST', 'Betmen,ToTheMoon,ChinChin,FTD,Chilli').split(',')

    # Проверяем совпадение
    matches = [c for c in companies_list if company_input.lower() in c.lower()]

    if matches:
        # Совпадение найдено - показываем кнопки для подтверждения
        builder = InlineKeyboardBuilder()
        for match in matches:
            builder.add(InlineKeyboardButton(
                text=match,
                callback_data=f"aff_company_{match}"
            ))
        builder.adjust(1)

        await msg.answer(f"Found matching partner programs. Select one:", reply_markup=builder.as_markup())
        await state.set_state(AffiliateAuthStates.waiting_for_company)
    else:
        # Совпадений нет - предлагаем отправить как есть
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text=f"Submit as '{company_input}'",
            callback_data=f"aff_company_{company_input}"
        ))
        builder.add(InlineKeyboardButton(
            text="Try again",
            callback_data="aff_retry_company"
        ))

        await msg.answer(
            f"No exact matches found. Your partner program will be saved as '{company_input}'.\n\n"
            f"If this is correct, click Submit. Otherwise, try entering a different name.",
            reply_markup=builder.as_markup()
        )
        await state.set_state(AffiliateAuthStates.waiting_for_company)

@router.callback_query(F.data == "aff_retry_company", AffiliateAuthStates.waiting_for_company)
async def retry_company_input(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Please enter your partner program name again:")

@router.callback_query(F.data.startswith("aff_company_"), AffiliateAuthStates.waiting_for_company)
async def process_affiliate_company(call: CallbackQuery, state: FSMContext):
    """Process company selection"""
    username = call.from_user.username
    company = call.data.split("_")[2]

    if await db.add_affiliate_user(username, company):
        await state.clear()
        await show_affiliate_main_menu(call)
    else:
        await call.answer("Error saving", show_alert=True)


# ============================================
# MAIN MENU
# ============================================

# В функции get_affiliate_main_keyboard() исправить:

async def get_affiliate_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🍽 Restaurants", callback_data="aff_restaurants"),
        InlineKeyboardButton(text="📝 Expense Report", callback_data="aff_report")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Conference policy", callback_data="aff_rules"),
        InlineKeyboardButton(text="ℹ️ Spending Limits", callback_data="aff_limits")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="menu_pr"),  # Назад в меню PR
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")
    )

    return builder.as_markup()


async def show_affiliate_main_menu(update: Union[Message, CallbackQuery]):
    """Show main menu - now always edits if CallbackQuery"""
    keyboard = await get_affiliate_main_keyboard()
    text = "Hey! I'm AffilMeet Module.\nHow can I help you?"

    if isinstance(update, Message):
        await update.answer(text, reply_markup=keyboard)
    else:  # CallbackQuery
        try:
            await update.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            # Если не получается отредактировать (например, сообщение удалено)
            await update.message.answer(text, reply_markup=keyboard)
        await update.answer()


@router.callback_query(F.data == "aff_main")
@affiliate_auth_required
async def back_to_affiliate_main(call: CallbackQuery, state: FSMContext):
    """Back to main menu"""
    await state.clear()
    await show_affiliate_main_menu(call)



@router.callback_query(F.data == "menu_main")
async def main_menu_callback(call: CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await state.clear()

    try:
        await call.message.edit_text(
            "🏠 Main Menu",
            reply_markup=get_main_menu_keyboard()
        )
    except:
        await call.message.delete()
        await call.answer(
            "🏠 Main Menu",
            reply_markup=get_main_menu_keyboard()
        )


# ============================================
# RESTAURANTS MODULE
# ============================================

@router.callback_query(F.data == "aff_restaurants")
@affiliate_auth_required
async def show_restaurants_menu(call: CallbackQuery):
    """Restaurants menu - IDENTICAL TO ORIGINAL"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📅 Cities list", callback_data="aff_city_list"),
        InlineKeyboardButton(text="✅ My Bookings", callback_data="aff_my_bookings")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="aff_main"),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu_main")
    )

    await call.message.edit_text("Choose action:", reply_markup=builder.as_markup())


@router.callback_query(F.data == "aff_city_list")
@affiliate_auth_required
async def show_cities_list(call: CallbackQuery):
    """Show cities list - IDENTICAL TO ORIGINAL"""
    cities = await db.get_cities_from_restaurants()
    cities_reversed = cities[::-1]

    if not cities_reversed:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="aff_main")
        )
        await call.message.edit_text("📭 No cities available", reply_markup=builder.as_markup())
        return

    builder = InlineKeyboardBuilder()
    # Специальная логика эмодзи как в оригинале:
    # Первый город - светлый эмодзи 🌆, остальные - темный 🏙

    for i, city in enumerate(cities_reversed):
        if i == 0:
            emoji = "🌆"  # Light icon for first city
        else:
            emoji = "🏙"  # Dark icon for others

        builder.add(InlineKeyboardButton(
            text=f"{emoji} {city}",
            callback_data=f"aff_city_{city}"
        ))
    builder.adjust(2)  # 2 кнопки в ряд как в оригинале

    builder.row(
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="aff_main")
    )

    await call.message.edit_text(
        "🏙 **Select city:**",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("aff_city_"))
@affiliate_auth_required
async def show_city_restaurants(call: CallbackQuery):
    """Show city restaurants"""
    city = call.data.split("_", 2)[2]

    restaurants = await db.get_restaurants_by_city(city)

    if not restaurants:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="aff_city_list"),
            InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
        )
        await call.message.edit_text(f"🍽 No restaurants in {city}", reply_markup=builder.as_markup())
        return

    builder = InlineKeyboardBuilder()
    for rest in restaurants:
        builder.add(InlineKeyboardButton(
            text=rest['restaurant'],
            callback_data=f"aff_rest_{rest['id']}"
        ))
    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text="◀️ Back", callback_data="aff_city_list"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )

    await call.message.edit_text(
        f"🍽 **Restaurants in {city}:**",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("aff_rest_"))
@affiliate_auth_required
async def show_restaurant_info(call: CallbackQuery):
    """Show restaurant info"""
    rest_id = int(call.data.split("_", 2)[2])

    restaurant = await db.get_restaurant_by_id(rest_id)

    if not restaurant:
        await call.answer("❌ Restaurant not found", show_alert=True)
        return

    info_text = (
            "<b>Restaurant:</b> " + restaurant['restaurant'] + "\n\n"
                                                               "<i>City:</i> " + restaurant['city'] + "\n"
                                                                                                      "<i>Address:</i> " +
            restaurant['address'] + "\n"
                                    "<i>Average bill:</i>\n<b>" + (
                restaurant['cost'] if restaurant['cost'] else "Not specified") + "</b>\n\n"
                                                                                 "<i>Link:</i>\n" + (
                restaurant['link'] if restaurant['link'] else "Not specified") + "\n\n"
                                                                                 "<i>Info:</i> " + (
                restaurant['comment'] if restaurant['comment'] else "No additional info")
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Book here", callback_data=f"aff_book_rest_{rest_id}"),
        InlineKeyboardButton(text="◀️ Back to list", callback_data=f"aff_city_{restaurant['city']}")  # Новая кнопка
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to menu", callback_data="aff_restaurants"),
        InlineKeyboardButton(text="🏠 Main", callback_data="menu_main")
    )

    await call.message.edit_text(
        info_text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )


# ============================================
# BOOKING SYSTEM (State Machine)
# ============================================

class BookingStates(StatesGroup):
    waiting_for_manager = State()
    waiting_for_datetime = State()
    waiting_for_time = State()
    waiting_for_company = State()
    waiting_for_partner = State()
    waiting_for_partner_type = State()
    waiting_for_city = State()
    waiting_for_restaurant = State()
    waiting_for_payment = State()
    waiting_for_people = State()
    waiting_for_confirmation = State()


class BookingCalendar:
    @staticmethod
    async def start_calendar(year: int = datetime.now().year,
                             month: int = datetime.now().month) -> InlineKeyboardMarkup:
        """Calendar for date selection"""
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(text="<", callback_data=f"book_prev_{year}_{month}"),
            InlineKeyboardButton(text=f"{BookingCalendar.get_month_name(month)} {year}", callback_data="ignore"),
            InlineKeyboardButton(text=">", callback_data=f"book_next_{year}_{month}"),
        )

        week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days])

        month_days = BookingCalendar.get_month_days(year, month)
        for week in month_days:
            builder.row(*[
                InlineKeyboardButton(
                    text=" " if day == 0 else str(day),
                    callback_data="ignore" if day == 0 else f"book_day_{year}_{month}_{day}"
                ) for day in week
            ])

        return builder.as_markup()

    @staticmethod
    def get_month_name(month: int) -> str:
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        return months[month - 1]

    @staticmethod
    def get_month_days(year: int, month: int) -> list[list[int]]:
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1,
                                                                                                1) - timedelta(days=1)
        start_weekday = first_day.weekday()
        days = []
        current_day = 1

        for _ in range(6):
            week = []
            for day in range(7):
                if (len(days) == 0 and day < start_weekday) or current_day > last_day.day:
                    week.append(0)
                else:
                    week.append(current_day)
                    current_day += 1
            days.append(week)
            if current_day > last_day.day:
                break
        return days


@router.callback_query(F.data == "aff_bookings")
@affiliate_auth_required
async def start_booking_process(call: CallbackQuery, state: FSMContext):
    """Start booking process"""
    await call.message.edit_text("Enter your name (manager attending the meeting):")
    await state.set_state(BookingStates.waiting_for_manager)


@router.message(BookingStates.waiting_for_manager)
@affiliate_auth_required
async def process_manager_name(msg: Message, state: FSMContext):
    """Process manager name"""
    await state.update_data(manager=msg.text)
    await msg.answer("Select meeting date:", reply_markup=await BookingCalendar.start_calendar())
    await state.set_state(BookingStates.waiting_for_datetime)


@router.callback_query(F.data.startswith("book_prev_"), BookingStates.waiting_for_datetime)
async def booking_prev_month(callback: CallbackQuery):
    """Previous month in calendar"""
    _, year, month = callback.data.split("_")[1:]
    year = int(year)
    month = int(month) - 1
    if month < 1:
        month = 12
        year -= 1
    await callback.message.edit_reply_markup(reply_markup=await BookingCalendar.start_calendar(year, month))


@router.callback_query(F.data.startswith("book_next_"), BookingStates.waiting_for_datetime)
async def booking_next_month(callback: CallbackQuery):
    """Next month in calendar"""
    _, year, month = callback.data.split("_")[1:]
    year = int(year)
    month = int(month) + 1
    if month > 12:
        month = 1
        year += 1
    await callback.message.edit_reply_markup(reply_markup=await BookingCalendar.start_calendar(year, month))


@router.callback_query(F.data.startswith("book_day_"), BookingStates.waiting_for_datetime)
async def booking_select_day(callback: CallbackQuery, state: FSMContext):
    """Select day in calendar"""
    _, year, month, day = callback.data.split("_")[1:]
    formatted_month = f"{int(month):02d}"
    formatted_day = f"{int(day):02d}"
    selected_date = f"{formatted_day}.{formatted_month}.{year}"

    await state.update_data(selected_date=selected_date)
    await callback.message.edit_text(
        f"Date selected: {selected_date}\n\nEnter meeting time (HH:MM, e.g. 14:30):"
    )
    await state.set_state(BookingStates.waiting_for_time)


@router.message(BookingStates.waiting_for_time)
@affiliate_auth_required
async def process_booking_time(msg: Message, state: FSMContext):
    """Process booking time"""
    if not re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', msg.text):
        await msg.answer("Wrong time format. Use HH:MM (e.g., 14:30)")
        return

    data = await state.get_data()
    selected_date = data.get('selected_date')
    datetime_str = f"{selected_date} {msg.text}"

    try:
        datetime.strptime(datetime_str, '%d.%m.%Y %H:%M')
        await state.update_data(datetime=datetime_str)
        await msg.answer("Enter partner company name:")
        await state.set_state(BookingStates.waiting_for_company)
    except ValueError:
        await msg.answer("Wrong date/time format")


@router.message(BookingStates.waiting_for_company)
@affiliate_auth_required
async def process_partner_company(msg: Message, state: FSMContext):
    """Process partner company"""
    await state.update_data(company=msg.text)
    await msg.answer("Enter partner name:")
    await state.set_state(BookingStates.waiting_for_partner)


@router.message(BookingStates.waiting_for_partner)
@affiliate_auth_required
async def process_partner_name(msg: Message, state: FSMContext):
    """Process partner name"""
    await state.update_data(partner=msg.text)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="VIP Partner", callback_data="aff_partner_vip"),
        InlineKeyboardButton(text="Regular Partner", callback_data="aff_partner_regular")
    )

    await msg.answer("Choose partner type:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.waiting_for_partner_type)


@router.callback_query(F.data.startswith("aff_partner_"), BookingStates.waiting_for_partner_type)
async def process_partner_type(call: CallbackQuery, state: FSMContext):
    """Process partner type"""
    partner_type = "VIP" if "vip" in call.data else "Regular"
    await state.update_data(partnertype=partner_type)

    # Get cities list
    cities = await db.get_cities_from_restaurants()

    if not cities:
        await call.message.edit_text("No cities available")
        return

    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.add(InlineKeyboardButton(
            text=f"🌆 {city}",
            callback_data=f"aff_book_city_{city}"
        ))
    builder.adjust(2)

    await call.message.edit_text("Choose meeting city:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.waiting_for_city)


@router.callback_query(F.data.startswith("aff_book_city_"), BookingStates.waiting_for_city)
async def process_booking_city(call: CallbackQuery, state: FSMContext):
    """Process city selection"""
    city = call.data.split("_")[3]
    await state.update_data(city=city)

    restaurants = await db.get_restaurants_by_city(city)

    if not restaurants:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Choose other city", callback_data="aff_bookings_start_over"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="aff_main")
        )
        await call.message.edit_text(f"No restaurants in {city}", reply_markup=builder.as_markup())
        return

    builder = InlineKeyboardBuilder()
    for rest in restaurants:
        builder.add(InlineKeyboardButton(
            text=rest['restaurant'],
            callback_data=f"aff_select_rest_{rest['id']}"
        ))
    builder.adjust(2)

    await call.message.edit_text(f"Choose restaurant in {city}:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.waiting_for_restaurant)


@router.callback_query(F.data.startswith("aff_select_rest_"), BookingStates.waiting_for_restaurant)
async def process_booking_restaurant(call: CallbackQuery, state: FSMContext):
    """Process restaurant selection"""
    rest_id = int(call.data.split("_")[3])
    restaurant = await db.get_restaurant_by_id(rest_id)

    if restaurant:
        await state.update_data(restaurant=restaurant['restaurant'])

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💳 Card", callback_data="aff_payment_card"),
            InlineKeyboardButton(text="💵 Cash", callback_data="aff_payment_cash")
        )

        await call.message.edit_text("Choose payment method:", reply_markup=builder.as_markup())
        await state.set_state(BookingStates.waiting_for_payment)


@router.callback_query(F.data.startswith("aff_payment_"), BookingStates.waiting_for_payment)
async def process_booking_payment(call: CallbackQuery, state: FSMContext):
    """Process payment method"""
    payment = "Card" if "card" in call.data else "Cash"
    await state.update_data(payment=payment)
    await call.message.edit_text("Enter number of people (including you):")
    await state.set_state(BookingStates.waiting_for_people)


@router.message(BookingStates.waiting_for_people)
@affiliate_auth_required
async def process_booking_people(msg: Message, state: FSMContext):
    """Process people count"""
    if not msg.text.isdigit() or int(msg.text) < 1:
        await msg.answer("Enter correct number (minimum 1)")
        return

    await state.update_data(people=msg.text)
    await show_booking_confirmation(msg, state)


async def show_booking_confirmation(msg: Union[Message, CallbackQuery], state: FSMContext):
    """Show booking confirmation"""
    data = await state.get_data()

    confirmation_text = (
        "📝 **Booking Confirmation**\n\n"
        f"👨‍💼 Manager: {data.get('manager', 'Not specified')}\n"
        f"📅 Date & Time: {data.get('datetime', 'Not specified')}\n"
        f"🏢 Partner Company: {data.get('company', 'Not specified')}\n"
        f"🤝 Partner: {data.get('partner', 'Not specified')}\n"
        f"🔹 Partner Type: {data.get('partnertype', 'Not specified')}\n"
        f"🍽 Restaurant: {data.get('restaurant', 'Not specified')}\n"
        f"👥 People: {data.get('people', 'Not specified')}\n"
        f"💳 Payment: {data.get('payment', 'Not specified')}\n\n"
        "Is everything correct?"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, confirm", callback_data="aff_booking_confirm"),
        InlineKeyboardButton(text="❌ No, cancel", callback_data="aff_main")
    )

    if isinstance(msg, Message):
        await msg.answer(confirmation_text, reply_markup=builder.as_markup())
    else:
        await msg.message.edit_text(confirmation_text, reply_markup=builder.as_markup())

    await state.set_state(BookingStates.waiting_for_confirmation)


@router.callback_query(F.data == "aff_booking_confirm", BookingStates.waiting_for_confirmation)
async def confirm_booking(call: CallbackQuery, state: FSMContext):
    """Confirm booking"""
    data = await state.get_data()
    username = call.from_user.username
    user_id = call.from_user.id

    # Проверка на дубликат
    if await db.check_duplicate_booking(username, data.get('datetime', ''), data.get('partner', '')):
        await call.answer("❌ Duplicate booking found! You already have a booking at this time with this partner.",
                          show_alert=True)
        await state.clear()
        return

    booking_data = {
        'username': username,
        'user_id': user_id,
        'manager': data.get('manager', ''),
        'datetime': data.get('datetime', ''),
        'company': data.get('company', ''),
        'partner': data.get('partner', ''),
        'restaurant': data.get('restaurant', ''),
        'people': data.get('people', '1'),
        'payment_method': data.get('payment', 'Card'),
        'partnertype': data.get('partnertype', 'Regular')
    }

    if await db.save_booking(booking_data):
        await call.message.edit_text(
            "✅ Booking saved successfully!\n\n"
            f"Restaurant: {data.get('restaurant', '')}\n"
            f"Date: {data.get('datetime', '')}\n"
            f"With {data.get('partner', '')} from {data.get('company', '')}"
        )

        # Log action
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="booking_created",
            details=booking_data
        )
    else:
        await call.message.edit_text("❌ Error saving booking")

    await state.clear()

    # Show menu
    keyboard = await get_affiliate_main_keyboard()
    await call.message.edit_text(
        "✅ Booking saved!\n\nWhat's next?",
        reply_markup=keyboard
    )


# ============================================
# MY BOOKINGS
# ============================================

@router.callback_query(F.data == "aff_my_bookings")
@affiliate_auth_required
async def show_my_bookings(call: CallbackQuery):
    """Show user bookings"""
    username = call.from_user.username
    bookings = await db.get_user_bookings(username)

    if not bookings:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📅 Create booking", callback_data="aff_bookings"),
            InlineKeyboardButton(text="◀️ Back", callback_data="aff_main")
        )
        await call.message.edit_text("No bookings yet", reply_markup=builder.as_markup())
        return

    response = "📋 **Your bookings:**\n\n"
    for i, booking in enumerate(bookings, 1):
        response += (
            f"{i}. {booking['restaurant']}\n"
            f"   📅 {booking['datetime']}\n"
            f"   🤝 {booking['partner']} ({booking['company']})\n"
            f"   👥 {booking['people']} people | 💳 {booking['payment_method']}\n\n"
        )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 New booking", callback_data="aff_bookings"),
        InlineKeyboardButton(text="◀️ Back", callback_data="aff_main")
    )

    await call.message.edit_text(response, reply_markup=builder.as_markup())


# ============================================
# REPORT SYSTEM
# ============================================

class ReportStates(StatesGroup):
    waiting_for_manager = State()
    waiting_for_date = State()
    waiting_for_partner = State()
    waiting_for_result = State()
    waiting_for_budget = State()
    waiting_for_confirmation = State()


@router.callback_query(F.data == "aff_report")
@affiliate_auth_required
async def start_report(call: CallbackQuery, state: FSMContext):
    """Start report"""
    await call.message.edit_text("Enter manager name who attended the meeting:")
    await state.set_state(ReportStates.waiting_for_manager)


@router.message(ReportStates.waiting_for_manager)
@affiliate_auth_required
async def process_report_manager(msg: Message, state: FSMContext):
    """Process manager in report"""
    await state.update_data(manager=msg.text)
    await msg.answer("Enter meeting date (DD.MM.YYYY):")
    await state.set_state(ReportStates.waiting_for_date)


@router.message(ReportStates.waiting_for_date)
@affiliate_auth_required
async def process_report_date(msg: Message, state: FSMContext):
    """Process date in report"""
    try:
        datetime.strptime(msg.text, '%d.%m.%Y')
        await state.update_data(meeting_date=msg.text)
        await msg.answer("Enter partner name:")
        await state.set_state(ReportStates.waiting_for_partner)
    except ValueError:
        await msg.answer("Wrong date format. Use DD.MM.YYYY")


@router.message(ReportStates.waiting_for_partner)
@affiliate_auth_required
async def process_report_partner(msg: Message, state: FSMContext):
    """Process partner in report"""
    await state.update_data(partner=msg.text)
    await msg.answer("Describe meeting results:")
    await state.set_state(ReportStates.waiting_for_result)


@router.message(ReportStates.waiting_for_result)
@affiliate_auth_required
async def process_report_result(msg: Message, state: FSMContext):
    """Process results in report"""
    await state.update_data(result=msg.text)
    await msg.answer("Enter meeting budget (if any):")
    await state.set_state(ReportStates.waiting_for_budget)


@router.message(ReportStates.waiting_for_budget)
@affiliate_auth_required
async def process_report_budget(msg: Message, state: FSMContext):
    """Process budget in report"""
    await state.update_data(budget=msg.text)

    # Show confirmation
    data = await state.get_data()
    username = msg.from_user.username
    company = await db.get_user_company(username)

    report_text = (
        "📝 **Meeting Report**\n\n"
        f"📅 Date: {data.get('meeting_date', 'Not specified')}\n"
        f"👨‍💼 Manager: {data.get('manager', 'Not specified')}\n"
        f"🏢 Company: {company}\n"
        f"🤝 Partner: {data.get('partner', 'Not specified')}\n"
        f"📌 Results: {data.get('result', 'Not specified')}\n"
        f"💰 Budget: {data.get('budget', 'Not specified')}\n\n"
        "Is everything correct?"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, send", callback_data="aff_report_confirm"),
        InlineKeyboardButton(text="❌ No, cancel", callback_data="aff_main")
    )

    await msg.answer(report_text, reply_markup=builder.as_markup())
    await state.set_state(ReportStates.waiting_for_confirmation)


@router.callback_query(F.data == "aff_report_confirm", ReportStates.waiting_for_confirmation)
async def confirm_report(call: CallbackQuery, state: FSMContext):
    """Confirm report"""
    data = await state.get_data()
    username = call.from_user.username
    company = await db.get_user_company(username)

    report_data = {
        'username': username,
        'company': company,
        'meeting_date': data.get('meeting_date', ''),
        'manager': data.get('manager', ''),
        'partner': data.get('partner', ''),
        'result': data.get('result', ''),
        'budget': data.get('budget', '0')
    }

    if await db.save_report(report_data):
        await call.message.edit_text(
            "✅ Report saved successfully!\n\n"
            f"Date: {data.get('meeting_date', '')}\n"
            f"With partner: {data.get('partner', '')}\n"
            f"Results: {data.get('result', '')[:100]}..."
        )

        # Log action
        await db.log_user_action(
            user_id=call.from_user.id,
            username=username,
            action="report_submitted",
            details=report_data
        )
    else:
        await call.message.edit_text("❌ Error saving report")

    await state.clear()

    # Show menu
    keyboard = await get_affiliate_main_keyboard()
    await call.message.edit_text(  # Изменено: edit_text вместо answer
        "✅ Report saved!\n\nWhat's next?",
        reply_markup=keyboard
    )


# ============================================
# RULES AND LIMITS
# ============================================

@router.callback_query(F.data == "aff_rules")
@affiliate_auth_required
async def show_affiliate_rules(call: CallbackQuery):
    """Show rules - with working back button"""
    try:
        username = call.from_user.username
        company = await db.get_user_company(username)

        # Пути к файлам
        base_path = './instructions/conferences/'
        company_file = f'{company} - Conference Rules.pdf'
        base_file = 'Conference Rules.pdf'

        file_to_send = None
        for filename in [company_file, base_file]:
            try:
                file_path = os.path.join(base_path, filename)
                if os.path.exists(file_path):
                    file_to_send = FSInputFile(file_path)
                    break
            except Exception:
                continue

        if not file_to_send:
            # Fallback
            file_to_send = FSInputFile('./instructions/conferences/123.pdf')

        # Создаем клавиатуру с callback_data, а не URL
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="menu_main")
        )
        builder.row(
            InlineKeyboardButton(text="🏠 Main", callback_data="aff_main")
        )
        keyboard = builder.as_markup()

        # Удаляем старое сообщение с кнопками
        try:
            await call.message.delete()
        except:
            pass

        # Отправляем документ
        await call.message.answer_document(
            document=file_to_send,
            caption="📄 Conference Policy",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error sending rules: {e}")
        await show_affiliate_main_menu(call)


@router.callback_query(F.data == "aff_limits")
@affiliate_auth_required
async def show_affiliate_limits(call: CallbackQuery):
    """Show limits - with working back button"""
    try:
        username = call.from_user.username
        company = await db.get_user_company(username)

        base_path = './instructions/limits/'
        company_file = f'{company} - Policy Limits.pdf'
        base_file = 'Policy Limits.pdf'

        file_to_send = None
        for filename in [company_file, base_file]:
            try:
                file_path = os.path.join(base_path, filename)
                if os.path.exists(file_path):
                    file_to_send = FSInputFile(file_path)
                    break
            except Exception:
                continue

        if not file_to_send:
            file_to_send = FSInputFile('./instructions/limits/123.pdf')

        # Клавиатура с callback_data
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="menu_main")
        )
        builder.row(
            InlineKeyboardButton(text="🏠 Main", callback_data="aff_main")
        )
        keyboard = builder.as_markup()

        try:
            await call.message.delete()
        except:
            pass

        await call.message.answer_document(
            document=file_to_send,
            caption="💰 Spending Limits",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error sending limits: {e}")
        await show_affiliate_main_menu(call)


# ============================================
# INTEGRATION WITH MAIN MENU
# ============================================

@router.callback_query(F.data == "pr_dinner")
async def start_affiliate_from_pr(call: CallbackQuery, state: FSMContext):
    """Start Affiliate module from PR section"""
    username = call.from_user.username

    if not username:
        await call.answer("Username required", show_alert=True)
        return

    if await db.check_affiliate_auth(username):
        await show_affiliate_main_menu(call)  # Изменено: call вместо call.message
    else:
        await call.message.edit_text(
            "🍽 **Partner Dinners**\n\n"
            "Authorization required for partner dinners module.\n\n"
            "Send command /affiliate_start",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔐 Authorize", callback_data="start_auth")],
                [InlineKeyboardButton(text="◀️ Back", callback_data="pr_menu")]
            ])
        )