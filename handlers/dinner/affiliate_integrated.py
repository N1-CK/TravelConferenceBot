# handlers/dinner/affiliate_integrated.py - ПОЛНАЯ ЛОКАЛИЗАЦИЯ НА РУССКИЙ ЯЗЫК
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Union, Optional

import asyncio
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from keyboards import get_main_menu_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from database import db
from utility.lang_utils import t, get_user_lang, get_text_sync


router = Router()
logger = logging.getLogger(__name__)


# ============================================
# AUTH COMMANDS
# ============================================

class AffiliateAuthStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_company = State()


@router.message(Command("affiliate_start"))
async def affiliate_start_command(msg: Message, state: FSMContext):
    """Начало авторизации в модуле партнерских ужинов"""
    user_id = msg.from_user.id
    username = msg.from_user.username

    if not username:
        await msg.answer(await t(user_id, 'error_no_username'))
        return

    if await db.check_whitelist(username):
        await show_affiliate_main_menu(msg)
    else:
        await state.set_state(AffiliateAuthStates.waiting_for_password)
        await msg.answer(await t(user_id, 'affiliate_enter_password'))


@router.message(AffiliateAuthStates.waiting_for_password)
async def process_affiliate_password(msg: Message, state: FSMContext):
    """Обработка пароля"""
    user_id = msg.from_user.id
    password = os.getenv('AFFILIATE_PASSWORD', 'affil123')

    if msg.text == password:
        await msg.answer(await t(user_id, 'affiliate_password_correct'))
        await state.set_state(AffiliateAuthStates.waiting_for_company)
        await msg.answer(await t(user_id, 'affiliate_enter_company'))
    else:
        await msg.answer(await t(user_id, 'affiliate_wrong_password'))


@router.message(AffiliateAuthStates.waiting_for_company)
async def process_affiliate_company(msg: Message, state: FSMContext):
    """Обработка названия компании"""
    user_id = msg.from_user.id
    username = msg.from_user.username
    company_input = msg.text.strip()

    if not company_input:
        await msg.answer(await t(user_id, 'affiliate_company_empty'))
        return

    companies_list = os.getenv('COMPANIES_LIST', 'Betmen,ToTheMoon,ChinChin,FTD,Chilli').split(',')

    # Проверяем совпадение
    matches = [c for c in companies_list if company_input.lower() in c.lower()]

    if matches:
        builder = InlineKeyboardBuilder()
        for match in matches:
            builder.add(InlineKeyboardButton(
                text=match,
                callback_data=f"aff_company_{match}"
            ))
        builder.adjust(1)

        await msg.answer(
            await t(user_id, 'affiliate_matches_found'),
            reply_markup=builder.as_markup()
        )
        await state.set_state(AffiliateAuthStates.waiting_for_company)
    else:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text=await t(user_id, 'affiliate_submit_as', company=company_input),
            callback_data=f"aff_company_{company_input}"
        ))
        builder.add(InlineKeyboardButton(
            text=await t(user_id, 'affiliate_try_again'),
            callback_data="aff_retry_company"
        ))

        await msg.answer(
            await t(user_id, 'affiliate_no_matches', company=company_input),
            reply_markup=builder.as_markup()
        )
        await state.set_state(AffiliateAuthStates.waiting_for_company)


@router.callback_query(F.data == "aff_retry_company", AffiliateAuthStates.waiting_for_company)
async def retry_company_input(call: CallbackQuery, state: FSMContext):
    """Повторный ввод компании"""
    user_id = call.from_user.id
    await call.message.edit_text(await t(user_id, 'affiliate_enter_company_again'))


@router.callback_query(F.data.startswith("aff_company_"), AffiliateAuthStates.waiting_for_company)
async def process_affiliate_company_callback(call: CallbackQuery, state: FSMContext):
    """Обработка выбора компании"""
    user_id = call.from_user.id
    username = call.from_user.username
    company = call.data.split("_")[2]

    if await db.add_affiliate_user(username, company):
        await state.clear()
        await show_affiliate_main_menu(call)
    else:
        await call.answer(await t(user_id, 'affiliate_save_error'), show_alert=True)


# ============================================
# MAIN MENU
# ============================================

async def get_affiliate_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура главного меню с локализацией"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text=get_text_sync(await get_user_lang(user_id), 'affiliate_restaurants'),
                            callback_data="aff_restaurants"),
        InlineKeyboardButton(text=get_text_sync(await get_user_lang(user_id), 'affiliate_report'),
                            callback_data="aff_report")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(await get_user_lang(user_id), 'affiliate_rules'),
                            callback_data="aff_rules"),
        InlineKeyboardButton(text=get_text_sync(await get_user_lang(user_id), 'affiliate_limits'),
                            callback_data="aff_limits")
    )
    builder.row(
        InlineKeyboardButton(text=get_text_sync(await get_user_lang(user_id), 'back'),
                            callback_data="menu_pr"),
        InlineKeyboardButton(text=get_text_sync(await get_user_lang(user_id), 'main_menu'),
                            callback_data="menu_main")
    )

    return builder.as_markup()


async def show_affiliate_main_menu(update: Union[Message, CallbackQuery]):
    """Показать главное меню"""
    user_id = update.from_user.id
    keyboard = await get_affiliate_main_keyboard(user_id)
    text = await t(user_id, 'affiliate_welcome')

    if isinstance(update, Message):
        await update.answer(text, reply_markup=keyboard)
    else:
        try:
            await update.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await update.message.answer(text, reply_markup=keyboard)
        await update.answer()


@router.callback_query(F.data == "aff_main")
async def back_to_affiliate_main(call: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    try:
        await call.message.delete()
    except:
        pass
    await show_affiliate_main_menu(call)


@router.callback_query(F.data == "menu_main")
async def main_menu_callback(call: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    user_id = call.from_user.id

    try:
        await call.message.edit_text(
            await t(user_id, 'main_menu_title'),
            reply_markup=await get_main_menu_keyboard(user_id)
        )
    except Exception:
        await call.message.delete()
        await call.message.answer(
            await t(user_id, 'main_menu_title'),
            reply_markup=await get_main_menu_keyboard(user_id)
        )


# ============================================
# RESTAURANTS MODULE
# ============================================

@router.callback_query(F.data == "aff_restaurants")
async def show_restaurants_menu(call: CallbackQuery):
    """Меню ресторанов"""
    user_id = call.from_user.id
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'affiliate_cities_list'), callback_data="aff_city_list"),
        InlineKeyboardButton(text=await t(user_id, 'affiliate_my_bookings'), callback_data="aff_my_bookings")
    )
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_main"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    await call.message.edit_text(await t(user_id, 'affiliate_choose_action'), reply_markup=builder.as_markup())


@router.callback_query(F.data == "aff_city_list")
async def show_cities_list(call: CallbackQuery):
    """Показать список городов"""
    user_id = call.from_user.id
    cities = await db.get_cities_from_restaurants()
    cities_reversed = cities[::-1]

    if not cities_reversed:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="aff_main")
        )
        await call.message.edit_text(await t(user_id, 'affiliate_no_cities'), reply_markup=builder.as_markup())
        return

    builder = InlineKeyboardBuilder()
    for i, city in enumerate(cities_reversed):
        if i == 0:
            emoji = "🌆"
        else:
            emoji = "🏙"

        builder.add(InlineKeyboardButton(
            text=f"{emoji} {city}",
            callback_data=f"aff_city_{city}"
        ))
    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="aff_main")
    )

    await call.message.edit_text(
        await t(user_id, 'affiliate_select_city'),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("aff_city_"))
async def show_city_restaurants(call: CallbackQuery):
    """Показать рестораны города"""
    user_id = call.from_user.id
    city = call.data.split("_", 2)[2]

    restaurants = await db.get_restaurants_by_city(city)

    if not restaurants:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_city_list"),
            InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
        )
        await call.message.edit_text(
            await t(user_id, 'affiliate_no_restaurants', city=city),
            reply_markup=builder.as_markup()
        )
        return

    builder = InlineKeyboardBuilder()
    for rest in restaurants:
        builder.add(InlineKeyboardButton(
            text=rest['restaurant'],
            callback_data=f"aff_rest_{rest['id']}"
        ))
    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_city_list"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    await call.message.edit_text(
        await t(user_id, 'affiliate_restaurants_in_city', city=city),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(F.data.startswith("aff_rest_"))
async def show_restaurant_info(call: CallbackQuery):
    """Показать информацию о ресторане"""
    user_id = call.from_user.id
    rest_id = int(call.data.split("_", 2)[2])

    restaurant = await db.get_restaurant_by_id(rest_id)

    if not restaurant:
        await call.answer(await t(user_id, 'affiliate_restaurant_not_found'), show_alert=True)
        return

    info_text = (
        f"<b>{await t(user_id, 'affiliate_restaurant')}:</b> {restaurant['restaurant']}\n\n"
        f"<i>{await t(user_id, 'affiliate_city')}:</i> {restaurant['city']}\n"
        f"<i>{await t(user_id, 'affiliate_address')}:</i> {restaurant['address']}\n"
        f"<i>{await t(user_id, 'affiliate_average_bill')}:</i>\n<b>{restaurant['cost'] if restaurant['cost'] else await t(user_id, 'affiliate_not_specified')}</b>\n\n"
        f"<i>{await t(user_id, 'affiliate_link')}:</i>\n{restaurant['link'] if restaurant['link'] else await t(user_id, 'affiliate_not_specified')}\n\n"
        f"<i>{await t(user_id, 'affiliate_info')}:</i> {restaurant['comment'] if restaurant['comment'] else await t(user_id, 'affiliate_no_info')}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'affiliate_back_to_list'),
                             callback_data=f"aff_city_{restaurant['city']}")
    )
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
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
    async def start_calendar(user_id: int, year: int = datetime.now().year,
                             month: int = datetime.now().month) -> InlineKeyboardMarkup:
        """Календарь для выбора даты с локализацией"""
        builder = InlineKeyboardBuilder()

        months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                     "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

        builder.row(
            InlineKeyboardButton(text="<", callback_data=f"book_prev_{year}_{month}"),
            InlineKeyboardButton(text=f"{months_ru[month-1]} {year}", callback_data="ignore"),
            InlineKeyboardButton(text=">", callback_data=f"book_next_{year}_{month}"),
        )

        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
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
    def get_month_days(year: int, month: int) -> list[list[int]]:
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1, 1) - timedelta(days=1)
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
async def start_booking_process(call: CallbackQuery, state: FSMContext):
    """Начать процесс бронирования"""
    user_id = call.from_user.id
    await call.message.edit_text(await t(user_id, 'affiliate_enter_manager_name'))
    await state.set_state(BookingStates.waiting_for_manager)


@router.message(BookingStates.waiting_for_manager)
async def process_manager_name(msg: Message, state: FSMContext):
    """Обработка имени менеджера"""
    user_id = msg.from_user.id
    await state.update_data(manager=msg.text)
    await msg.answer(
        await t(user_id, 'affiliate_select_date'),
        reply_markup=await BookingCalendar.start_calendar(user_id)
    )
    await state.set_state(BookingStates.waiting_for_datetime)


@router.callback_query(F.data.startswith("book_prev_"), BookingStates.waiting_for_datetime)
async def booking_prev_month(callback: CallbackQuery):
    """Предыдущий месяц"""
    user_id = callback.from_user.id
    _, year, month = callback.data.split("_")[1:]
    year = int(year)
    month = int(month) - 1
    if month < 1:
        month = 12
        year -= 1
    await callback.message.edit_reply_markup(
        reply_markup=await BookingCalendar.start_calendar(user_id, year, month)
    )


@router.callback_query(F.data.startswith("book_next_"), BookingStates.waiting_for_datetime)
async def booking_next_month(callback: CallbackQuery):
    """Следующий месяц"""
    user_id = callback.from_user.id
    _, year, month = callback.data.split("_")[1:]
    year = int(year)
    month = int(month) + 1
    if month > 12:
        month = 1
        year += 1
    await callback.message.edit_reply_markup(
        reply_markup=await BookingCalendar.start_calendar(user_id, year, month)
    )


@router.callback_query(F.data.startswith("book_day_"), BookingStates.waiting_for_datetime)
async def booking_select_day(callback: CallbackQuery, state: FSMContext):
    """Выбор дня в календаре"""
    user_id = callback.from_user.id
    _, year, month, day = callback.data.split("_")[1:]
    formatted_month = f"{int(month):02d}"
    formatted_day = f"{int(day):02d}"
    selected_date = f"{formatted_day}.{formatted_month}.{year}"

    await state.update_data(selected_date=selected_date)
    await callback.message.edit_text(
        await t(user_id, 'affiliate_date_selected', date=selected_date) + "\n\n" +
        await t(user_id, 'affiliate_enter_time')
    )
    await state.set_state(BookingStates.waiting_for_time)


@router.message(BookingStates.waiting_for_time)
async def process_booking_time(msg: Message, state: FSMContext):
    """Обработка времени встречи"""
    user_id = msg.from_user.id
    if not re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', msg.text):
        await msg.answer(await t(user_id, 'affiliate_wrong_time_format'))
        return

    data = await state.get_data()
    selected_date = data.get('selected_date')
    datetime_str = f"{selected_date} {msg.text}"

    try:
        datetime.strptime(datetime_str, '%d.%m.%Y %H:%M')
        await state.update_data(datetime=datetime_str)
        await msg.answer(await t(user_id, 'affiliate_enter_partner_company'))
        await state.set_state(BookingStates.waiting_for_company)
    except ValueError:
        await msg.answer(await t(user_id, 'affiliate_wrong_datetime_format'))


@router.message(BookingStates.waiting_for_company)
async def process_partner_company(msg: Message, state: FSMContext):
    """Обработка компании партнера"""
    user_id = msg.from_user.id
    await state.update_data(company=msg.text)
    await msg.answer(await t(user_id, 'affiliate_enter_partner_name'))
    await state.set_state(BookingStates.waiting_for_partner)


@router.message(BookingStates.waiting_for_partner)
async def process_partner_name(msg: Message, state: FSMContext):
    """Обработка имени партнера"""
    user_id = msg.from_user.id
    await state.update_data(partner=msg.text)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'affiliate_vip_partner'), callback_data="aff_partner_vip"),
        InlineKeyboardButton(text=await t(user_id, 'affiliate_regular_partner'), callback_data="aff_partner_regular")
    )

    await msg.answer(await t(user_id, 'affiliate_choose_partner_type'), reply_markup=builder.as_markup())
    await state.set_state(BookingStates.waiting_for_partner_type)


@router.callback_query(F.data.startswith("aff_partner_"), BookingStates.waiting_for_partner_type)
async def process_partner_type(call: CallbackQuery, state: FSMContext):
    """Обработка типа партнера"""
    user_id = call.from_user.id
    partner_type = "VIP" if "vip" in call.data else await t(user_id, 'affiliate_regular')
    await state.update_data(partnertype=partner_type)

    cities = await db.get_cities_from_restaurants()

    if not cities:
        await call.message.edit_text(await t(user_id, 'affiliate_no_cities'))
        return

    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.add(InlineKeyboardButton(
            text=f"🌆 {city}",
            callback_data=f"aff_book_city_{city}"
        ))
    builder.adjust(2)

    await call.message.edit_text(await t(user_id, 'affiliate_choose_city'), reply_markup=builder.as_markup())
    await state.set_state(BookingStates.waiting_for_city)


@router.callback_query(F.data.startswith("aff_book_city_"), BookingStates.waiting_for_city)
async def process_booking_city(call: CallbackQuery, state: FSMContext):
    """Обработка выбора города"""
    user_id = call.from_user.id
    city = call.data.split("_")[3]
    await state.update_data(city=city)

    restaurants = await db.get_restaurants_by_city(city)

    if not restaurants:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'affiliate_choose_other_city'), callback_data="aff_bookings_start_over"),
            InlineKeyboardButton(text=await t(user_id, 'cancel'), callback_data="aff_main")
        )
        await call.message.edit_text(
            await t(user_id, 'affiliate_no_restaurants_in_city', city=city),
            reply_markup=builder.as_markup()
        )
        return

    builder = InlineKeyboardBuilder()
    for rest in restaurants:
        builder.add(InlineKeyboardButton(
            text=rest['restaurant'],
            callback_data=f"aff_select_rest_{rest['id']}"
        ))
    builder.adjust(2)

    await call.message.edit_text(
        await t(user_id, 'affiliate_choose_restaurant_in_city', city=city),
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_restaurant)


@router.callback_query(F.data.startswith("aff_select_rest_"), BookingStates.waiting_for_restaurant)
async def process_booking_restaurant(call: CallbackQuery, state: FSMContext):
    """Обработка выбора ресторана"""
    user_id = call.from_user.id
    rest_id = int(call.data.split("_")[3])
    restaurant = await db.get_restaurant_by_id(rest_id)

    if restaurant:
        await state.update_data(restaurant=restaurant['restaurant'])

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'affiliate_payment_card'), callback_data="aff_payment_card"),
            InlineKeyboardButton(text=await t(user_id, 'affiliate_payment_cash'), callback_data="aff_payment_cash")
        )

        await call.message.edit_text(await t(user_id, 'affiliate_choose_payment'), reply_markup=builder.as_markup())
        await state.set_state(BookingStates.waiting_for_payment)


@router.callback_query(F.data.startswith("aff_payment_"), BookingStates.waiting_for_payment)
async def process_booking_payment(call: CallbackQuery, state: FSMContext):
    """Обработка способа оплаты"""
    user_id = call.from_user.id
    payment = await t(user_id, 'affiliate_payment_card_type') if "card" in call.data else await t(user_id, 'affiliate_payment_cash_type')
    await state.update_data(payment=payment)
    await call.message.edit_text(await t(user_id, 'affiliate_enter_people_count'))
    await state.set_state(BookingStates.waiting_for_people)


@router.message(BookingStates.waiting_for_people)
async def process_booking_people(msg: Message, state: FSMContext):
    """Обработка количества человек"""
    user_id = msg.from_user.id
    if not msg.text.isdigit() or int(msg.text) < 1:
        await msg.answer(await t(user_id, 'affiliate_enter_correct_people'))
        return

    await state.update_data(people=msg.text)
    await show_booking_confirmation(msg, state)


async def show_booking_confirmation(msg: Union[Message, CallbackQuery], state: FSMContext):
    """Показать подтверждение бронирования"""
    data = await state.get_data()
    user_id = msg.from_user.id if hasattr(msg, 'from_user') else msg.message.from_user.id

    confirmation_text = (
        f"📝 {await t(user_id, 'affiliate_booking_confirmation')}\n\n"
        f"👨‍💼 {await t(user_id, 'affiliate_manager')}: {data.get('manager', await t(user_id, 'affiliate_not_specified'))}\n"
        f"📅 {await t(user_id, 'affiliate_datetime')}: {data.get('datetime', await t(user_id, 'affiliate_not_specified'))}\n"
        f"🏢 {await t(user_id, 'affiliate_partner_company')}: {data.get('company', await t(user_id, 'affiliate_not_specified'))}\n"
        f"🤝 {await t(user_id, 'affiliate_partner')}: {data.get('partner', await t(user_id, 'affiliate_not_specified'))}\n"
        f"🔹 {await t(user_id, 'affiliate_partner_type')}: {data.get('partnertype', await t(user_id, 'affiliate_not_specified'))}\n"
        f"🍽 {await t(user_id, 'affiliate_restaurant')}: {data.get('restaurant', await t(user_id, 'affiliate_not_specified'))}\n"
        f"👥 {await t(user_id, 'affiliate_people')}: {data.get('people', await t(user_id, 'affiliate_not_specified'))}\n"
        f"💳 {await t(user_id, 'affiliate_payment')}: {data.get('payment', await t(user_id, 'affiliate_not_specified'))}\n\n"
        f"{await t(user_id, 'affiliate_is_correct')}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'affiliate_confirm_yes'), callback_data="aff_booking_confirm"),
        InlineKeyboardButton(text=await t(user_id, 'affiliate_confirm_no'), callback_data="aff_main")
    )

    if isinstance(msg, Message):
        await msg.answer(confirmation_text, reply_markup=builder.as_markup())
    else:
        await msg.message.edit_text(confirmation_text, reply_markup=builder.as_markup())

    await state.set_state(BookingStates.waiting_for_confirmation)


@router.callback_query(F.data == "aff_booking_confirm", BookingStates.waiting_for_confirmation)
async def confirm_booking(call: CallbackQuery, state: FSMContext):
    """Подтверждение бронирования"""
    data = await state.get_data()
    user_id = call.from_user.id
    username = call.from_user.username

    if await db.check_duplicate_booking(username, data.get('datetime', ''), data.get('partner', '')):
        await call.answer(await t(user_id, 'affiliate_duplicate_booking'), show_alert=True)
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
        'payment_method': data.get('payment', await t(user_id, 'affiliate_payment_card_type')),
        'partnertype': data.get('partnertype', await t(user_id, 'affiliate_regular'))
    }

    if await db.save_booking(booking_data):
        await call.message.edit_text(
            await t(user_id, 'affiliate_booking_saved') + "\n\n"
        )

        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="booking_created",
            details=booking_data
        )
    else:
        await call.message.edit_text(await t(user_id, 'affiliate_booking_error'))

    await state.clear()

    keyboard = await get_affiliate_main_keyboard(user_id)
    await call.message.edit_text(
        await t(user_id, 'affiliate_booking_saved_whats_next'),
        reply_markup=keyboard
    )


# ============================================
# MY BOOKINGS
# ============================================

@router.callback_query(F.data == "aff_my_bookings")
async def show_my_bookings(call: CallbackQuery):
    """Показать бронирования пользователя"""
    user_id = call.from_user.id
    username = call.from_user.username
    bookings = await db.get_user_bookings(username)

    if not bookings:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'affiliate_create_booking'), callback_data="aff_bookings"),
            InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_main")
        )
        await call.message.edit_text(await t(user_id, 'affiliate_no_bookings'), reply_markup=builder.as_markup())
        return

    response = f"📋 {await t(user_id, 'affiliate_your_bookings')}:\n\n"
    for i, booking in enumerate(bookings, 1):
        response += (
            f"{i}. {booking['restaurant']}\n"
            f"   📅 {booking['datetime']}\n"
            f"   📅 {booking['datetime']}\n"
            f"   🤝 {booking['partner']} ({booking['company']})\n"
            f"   👥 {booking['people']} {await t(user_id, 'affiliate_people_lower')} | 💳 {booking['payment_method']}\n\n"
        )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'affiliate_new_booking'), callback_data="aff_bookings"),
        InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_main")
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
async def start_report(call: CallbackQuery, state: FSMContext):
    """Начать отчет"""
    user_id = call.from_user.id
    await call.message.edit_text(await t(user_id, 'affiliate_enter_manager_name_report'))
    await state.set_state(ReportStates.waiting_for_manager)


@router.message(ReportStates.waiting_for_manager)
async def process_report_manager(msg: Message, state: FSMContext):
    """Обработка менеджера в отчете"""
    user_id = msg.from_user.id
    await state.update_data(manager=msg.text)
    await msg.answer(await t(user_id, 'affiliate_enter_meeting_date'))
    await state.set_state(ReportStates.waiting_for_date)


@router.message(ReportStates.waiting_for_date)
async def process_report_date(msg: Message, state: FSMContext):
    """Обработка даты в отчете"""
    user_id = msg.from_user.id
    try:
        datetime.strptime(msg.text, '%d.%m.%Y')
        await state.update_data(meeting_date=msg.text)
        await msg.answer(await t(user_id, 'affiliate_enter_partner_name_report'))
        await state.set_state(ReportStates.waiting_for_partner)
    except ValueError:
        await msg.answer(await t(user_id, 'affiliate_wrong_date_format'))


@router.message(ReportStates.waiting_for_partner)
async def process_report_partner(msg: Message, state: FSMContext):
    """Обработка партнера в отчете"""
    user_id = msg.from_user.id
    await state.update_data(partner=msg.text)
    await msg.answer(await t(user_id, 'affiliate_describe_results'))
    await state.set_state(ReportStates.waiting_for_result)


@router.message(ReportStates.waiting_for_result)
async def process_report_result(msg: Message, state: FSMContext):
    """Обработка результатов в отчете"""
    user_id = msg.from_user.id
    await state.update_data(result=msg.text)
    await msg.answer(await t(user_id, 'affiliate_enter_budget'))
    await state.set_state(ReportStates.waiting_for_budget)


@router.message(ReportStates.waiting_for_budget)
async def process_report_budget(msg: Message, state: FSMContext):
    """Обработка бюджета в отчете"""
    user_id = msg.from_user.id
    await state.update_data(budget=msg.text)

    data = await state.get_data()
    username = msg.from_user.username
    company = await db.get_user_company(user_id)

    report_text = (
        f"📝 {await t(user_id, 'affiliate_meeting_report')}\n\n"
        f"📅 {await t(user_id, 'affiliate_date')}: {data.get('meeting_date', await t(user_id, 'affiliate_not_specified'))}\n"
        f"👨‍💼 {await t(user_id, 'affiliate_manager')}: {data.get('manager', await t(user_id, 'affiliate_not_specified'))}\n"
        f"🏢 {await t(user_id, 'affiliate_company')}: {company}\n"
        f"🤝 {await t(user_id, 'affiliate_partner')}: {data.get('partner', await t(user_id, 'affiliate_not_specified'))}\n"
        f"📌 {await t(user_id, 'affiliate_results')}: {data.get('result', await t(user_id, 'affiliate_not_specified'))}\n"
        f"💰 {await t(user_id, 'affiliate_budget')}: {data.get('budget', await t(user_id, 'affiliate_not_specified'))}\n\n"
        f"{await t(user_id, 'affiliate_is_correct')}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'affiliate_send'), callback_data="aff_report_confirm"),
        InlineKeyboardButton(text=await t(user_id, 'cancel'), callback_data="aff_main")
    )

    await msg.answer(report_text, reply_markup=builder.as_markup())
    await state.set_state(ReportStates.waiting_for_confirmation)


@router.callback_query(F.data == "aff_report_confirm", ReportStates.waiting_for_confirmation)
async def confirm_report(call: CallbackQuery, state: FSMContext):
    """Подтверждение отчета"""
    data = await state.get_data()
    user_id = call.from_user.id
    username = call.from_user.username
    company = await db.get_user_company(user_id)

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
            await t(user_id, 'affiliate_report_saved') + "\n\n"
        )

        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="report_submitted",
            details=report_data
        )
    else:
        await call.message.edit_text(await t(user_id, 'affiliate_report_error'))

    await state.clear()

    keyboard = await get_affiliate_main_keyboard(user_id)
    await call.message.edit_text(
        await t(user_id, 'affiliate_report_saved_whats_next'),
        reply_markup=keyboard
    )


# ============================================
# RULES AND LIMITS
# ============================================

@router.callback_query(F.data == "aff_rules")
async def show_affiliate_rules(call: CallbackQuery):
    """Показать правила"""
    user_id = call.from_user.id
    try:
        username = call.from_user.username
        company = await db.get_user_company(user_id)

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
            file_to_send = FSInputFile('./instructions/conferences/123.pdf')

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_main")
        )
        keyboard = builder.as_markup()

        try:
            await call.message.delete()
        except:
            pass

        await call.message.answer_document(
            document=file_to_send,
            caption=await t(user_id, 'affiliate_conference_policy'),
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error sending rules: {e}")
        await show_affiliate_main_menu(call)


@router.callback_query(F.data == "aff_limits")
async def show_affiliate_limits(call: CallbackQuery):
    """Показать лимиты"""
    user_id = call.from_user.id
    try:
        username = call.from_user.username
        company = await db.get_user_company(user_id)

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

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="aff_main")
        )
        keyboard = builder.as_markup()

        try:
            await call.message.delete()
        except:
            pass

        await call.message.answer_document(
            document=file_to_send,
            caption=await t(user_id, 'affiliate_spending_limits'),
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
    """Запуск модуля партнерских ужинов из PR раздела"""
    user_id = call.from_user.id
    username = call.from_user.username

    if not username:
        await call.answer(await t(user_id, 'error_no_username'), show_alert=True)
        return

    if not await db.check_whitelist(username):
        await call.answer(await t(user_id, 'affiliate_no_access'), show_alert=True)
        return

    await show_affiliate_main_menu(call)