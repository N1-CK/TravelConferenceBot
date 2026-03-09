from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_back_next_keyboard, get_travel_menu_keyboard
from database import db

router = Router()


class VisaForm(StatesGroup):
    waiting_for_visa_status = State()
    waiting_for_passport = State()
    waiting_for_city_from = State()
    waiting_for_city_to = State()
    waiting_for_baggage = State()
    waiting_for_preferences = State()


class FlightForm(StatesGroup):
    waiting_for_passport = State()
    waiting_for_city_from = State()
    waiting_for_city_to = State()
    waiting_for_baggage = State()
    waiting_for_preferences = State()


class PerDiemForm(StatesGroup):
    waiting_for_payment_details = State()
    waiting_for_currency = State()
    waiting_for_comments = State()
    waiting_for_consent = State()


class TravelQuestionForm(StatesGroup):
    waiting_for_category = State()
    waiting_for_question = State()


@router.callback_query(F.data == "travel_visa")
async def start_visa_support(callback: CallbackQuery, state: FSMContext):
    """Визовая поддержка"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ У меня есть виза", callback_data="visa_have")],
        [InlineKeyboardButton(text="❌ У меня нет визы", callback_data="visa_not_have")],
        [InlineKeyboardButton(text="🔄 Особый случай", callback_data="visa_special")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_travel")]
    ])

    await callback.message.edit_text(
        "🛂 Визовая поддержка\n\nВыберите ваш статус:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("visa_"))
async def process_visa_status(callback: CallbackQuery, state: FSMContext):
    """Обработка статуса визы"""
    visa_status = callback.data.replace("visa_", "")

    if visa_status == "not_have":
        # Памятка по получению визы
        await callback.message.edit_text(
            "📋 Памятка по получению визы:\n\n"
            "1. Соберите документы:\n"
            "   - Загранпаспорт\n"
            "   - Фотографии\n"
            "   - Приглашение\n"
            "   - Справка с работы\n\n"
            "2. Обратитесь в агентства:\n"
            "   - Agency A: +7 (999) 111-11-11\n"
            "   - Agency B: +7 (999) 222-22-22\n\n"
            "⚠️ Организаторы не несут ответственности за услуги агентств.\n\n"
            "3. После получения визы нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить статус визы", callback_data="visa_update_status")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="travel_visa")]
            ])
        )
    else:
        # Начинаем форму для тех, у кого есть виза
        await state.set_state(VisaForm.waiting_for_passport)
        await state.update_data(visa_status=visa_status)
        await callback.message.edit_text(
            "Шаг 1 из 5\nУкажите паспортные данные для покупки билета:",
            reply_markup=get_back_next_keyboard(back_to="travel_visa", next_disabled=True)
        )


# Добавить после process_visa_status

@router.message(VisaForm.waiting_for_passport)
async def process_visa_passport(message: Message, state: FSMContext):
    """Обработка паспортных данных"""
    await state.update_data(passport_data=message.text)
    await state.set_state(VisaForm.waiting_for_city_from)
    await message.answer(
        "Шаг 2 из 5\nГород отправления:",
        reply_markup=get_back_next_keyboard(back_to="travel_visa")
    )


@router.message(VisaForm.waiting_for_city_from)
async def process_visa_city_from(message: Message, state: FSMContext):
    """Обработка города отправления"""
    await state.update_data(city_from=message.text)
    await state.set_state(VisaForm.waiting_for_city_to)
    await message.answer(
        "Шаг 3 из 5\nМесто назначения:",
        reply_markup=get_back_next_keyboard(back_to="visa_back_step2")
    )


@router.message(VisaForm.waiting_for_city_to)
async def process_visa_city_to(message: Message, state: FSMContext):
    """Обработка места назначения"""
    await state.update_data(city_to=message.text)
    await state.set_state(VisaForm.waiting_for_baggage)

    # Кнопки Да/Нет для багажа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="baggage_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="baggage_no")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="visa_back_step3")]
    ])
    await message.answer(
        "Шаг 4 из 5\nУкажите, нужен ли багаж:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("baggage_"), VisaForm.waiting_for_baggage)
async def process_visa_baggage(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора багажа"""
    needs_baggage = callback.data == "baggage_yes"
    await state.update_data(needs_baggage=needs_baggage)
    await state.set_state(VisaForm.waiting_for_preferences)
    await callback.message.edit_text(
        "Шаг 5 из 5\nНапишите предпочтения по билетам (время, дата, авиалинии и т.д.):",
        reply_markup=get_back_next_keyboard(back_to="visa_back_step4", next_disabled=True)
    )


@router.message(VisaForm.waiting_for_preferences)
async def process_visa_preferences(message: Message, state: FSMContext):
    """Обработка предпочтений и сохранение заявки"""
    await state.update_data(preferences=message.text)
    data = await state.get_data()

    # Сохраняем в БД
    visa_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'visa_status': data.get('visa_status'),
        'passport_data': data.get('passport_data'),
        'city_from': data.get('city_from'),
        'city_to': data.get('city_to'),
        'needs_baggage': data.get('needs_baggage', False),
        'preferences': data.get('preferences')
    }

    if await db.save_visa_request(visa_data):
        await message.answer(
            "✅ Заявка на визовую поддержку отправлена!\n\n"
            "Благодарим за ответ, наша команда скоро свяжется с тобой для обсуждения деталей."
        )
    else:
        await message.answer("❌ Ошибка сохранения заявки. Попробуйте позже.")

    await state.clear()

@router.callback_query(F.data == "travel_flight")
async def start_flight_form(callback: CallbackQuery, state: FSMContext):
    """Форма заказа билета"""
    await state.set_state(FlightForm.waiting_for_passport)
    await callback.message.edit_text(
        "✈️ Билет на самолёт\n\nШаг 1 из 5\nУкажите паспортные данные:",
        reply_markup=get_back_next_keyboard(back_to="menu_travel", next_disabled=True)
    )


@router.callback_query(F.data == "travel_hotel")
async def show_hotel_info(callback: CallbackQuery):
    """Информация об отеле"""
    await callback.message.edit_text(
        "🏨 Информация по отелю:\n\n"
        "Название: Grand Hotel\n"
        "Адрес: ул. Примерная, д. 1, Москва\n"
        "Время заезда: 14:00\n"
        "Время выезда: 12:00\n"
        "Контакты: +7 (999) 333-33-33\n\n"
        "Вы получите уведомление, когда администратор забронирует отель.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ С информацией ознакомился", callback_data="hotel_acknowledge")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_travel")]
        ])
    )


@router.callback_query(F.data == "travel_per_diem")
async def start_per_diem_form(callback: CallbackQuery, state: FSMContext):
    """Форма суточных"""
    await state.set_state(PerDiemForm.waiting_for_payment_details)
    await callback.message.edit_text(
        "💰 Суточные\n\nШаг 1 из 4\nУкажите реквизиты для выплаты (IBAN/номер карты/способ):",
        reply_markup=get_back_next_keyboard(back_to="menu_travel", next_disabled=True)
    )


@router.callback_query(F.data == "travel_question")
async def start_travel_question(callback: CallbackQuery, state: FSMContext):
    """Вопрос к тревел-менеджеру"""
    await state.set_state(TravelQuestionForm.waiting_for_category)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Виза", callback_data="cat_visa")],
        [InlineKeyboardButton(text="Билеты", callback_data="cat_flight")],
        [InlineKeyboardButton(text="Отель", callback_data="cat_hotel")],
        [InlineKeyboardButton(text="Суточные", callback_data="cat_per_diem")],
        [InlineKeyboardButton(text="Другое", callback_data="cat_other")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_travel")]
    ])

    await callback.message.edit_text(
        "❓ Вопрос к тревел-менеджеру\n\nВыберите категорию вопроса:",
        reply_markup=keyboard
    )

@router.message(FlightForm.waiting_for_passport)
async def process_flight_passport(message: Message, state: FSMContext):
    await message.answer("Форма билетов в разработке...")
    await state.clear()

@router.message(PerDiemForm.waiting_for_payment_details)
async def process_payment_details(message: Message, state: FSMContext):
    await message.answer("Форма суточных в разработке...")
    await state.clear()