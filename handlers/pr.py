from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_pr_menu_keyboard, get_back_next_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import os
from handlers.managers_chat import send_question_to_manager

PR_MANAGER_CHAT_ID = int(os.getenv("TG_PR_MANAGER_CHAT_ID", 0))

router = Router()


# Состояния для формы баннера
class PRBannerForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_language = State()
    waiting_for_photo_choice = State()
    waiting_for_photo = State()

class BusinessCardsForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_position_en = State()
    waiting_for_company = State()
    waiting_for_contacts = State()
    waiting_for_brand_style = State()

class PRQuestionForm(StatesGroup):
    waiting_for_category = State()
    waiting_for_question = State()

@router.callback_query(F.data == "pr_business_cards")
async def start_business_cards_form(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_name)
    await callback.message.edit_text(
        "📇 Заказ визиток\n\nШаг 1 из 5\nУкажите имя и фамилию для визитки:",
        reply_markup=get_back_next_keyboard(back_to="pr_menu", next_disabled=True)
    )

@router.callback_query(F.data == "pr_banner")
async def start_banner_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы для заказа баннера"""
    await state.set_state(PRBannerForm.waiting_for_name)

    await callback.message.edit_text(
        "🎨 Заказ баннера для соцсетей\n\n"
        "Шаг 1 из 6\n"
        "Укажите ваше имя и фамилию:",
        reply_markup=get_back_next_keyboard(back_to="pr_menu", next_disabled=True)
    )


@router.callback_query(F.data == "pr_dinner")
async def start_dinner_module(callback: CallbackQuery, state: FSMContext):
    """Start affiliate module - edit existing message"""
    from .dinner.affiliate_integrated import show_affiliate_main_menu
    await state.clear()
    await show_affiliate_main_menu(callback)


@router.message(PRBannerForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени"""
    await state.update_data(name=message.text)
    await state.set_state(PRBannerForm.waiting_for_position)

    await message.answer(
        "Шаг 2 из 6\n"
        "Напишите свою должность/роль:",
        reply_markup=get_back_next_keyboard(back_to="banner_step1")
    )


@router.message(PRBannerForm.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    """Обработка должности"""
    await state.update_data(position=message.text)
    await state.set_state(PRBannerForm.waiting_for_company)

    await message.answer(
        "Шаг 3 из 6\n"
        "Название компании/партнерской программы:",
        reply_markup=get_back_next_keyboard(back_to="banner_step2")
    )


@router.message(PRBannerForm.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    """Обработка компании"""
    await state.update_data(company=message.text)
    await state.set_state(PRBannerForm.waiting_for_language)

    # Клавиатура с выбором языка
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    from aiogram.utils.keyboard import ReplyKeyboardBuilder

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🇷🇺 Русский"))
    builder.row(KeyboardButton(text="🇬🇧 English"))
    builder.row(KeyboardButton(text="🇪🇸 Español"))

    await message.answer(
        "Шаг 4 из 6\n"
        "Выберите желаемый язык баннера:",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )


@router.message(PRBannerForm.waiting_for_language)
async def process_language(message: Message, state: FSMContext):
    """Обработка языка"""
    await state.update_data(language=message.text)
    await state.set_state(PRBannerForm.waiting_for_photo_choice)

    # Кнопки Да/Нет
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="banner_photo_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="banner_photo_no")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="banner_back_step4")]
    ])

    await message.answer(
        "Шаг 5 из 6\n"
        "Добавить фотографию в баннер?",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "banner_photo_yes", PRBannerForm.waiting_for_photo_choice)
async def process_photo_yes(callback: CallbackQuery, state: FSMContext):
    """Пользователь хочет добавить фото"""
    await state.set_state(PRBannerForm.waiting_for_photo)
    await callback.message.edit_text(
        "Шаг 6 из 6\n"
        "Пожалуйста, прикрепите изображение:",
        reply_markup=get_back_next_keyboard(back_to="banner_step5")
    )


@router.callback_query(F.data == "banner_photo_no", PRBannerForm.waiting_for_photo_choice)
async def process_photo_no(callback: CallbackQuery, state: FSMContext):
    """Пользователь НЕ хочет добавлять фото"""
    await state.update_data(photo_required=False)
    await submit_banner_request(callback, state)


@router.message(PRBannerForm.waiting_for_photo, F.photo)
async def process_photo_upload(message: Message, state: FSMContext):
    """Обработка загруженного фото"""
    # Сохраняем file_id фото
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id, photo_required=True)
    await submit_banner_request(message, state)


# В handlers/pr.py добавить:

@router.message(BusinessCardsForm.waiting_for_name)
async def process_business_cards_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_position_en)
    await message.answer(
        "Шаг 2 из 5\nНапишите свою должность/роль (на английском):",
        reply_markup=get_back_next_keyboard(back_to="pr_business_cards")
    )


@router.message(BusinessCardsForm.waiting_for_position_en)
async def process_business_cards_position(message: Message, state: FSMContext):
    await state.update_data(position_en=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_company)
    await message.answer(
        "Шаг 3 из 5\nНазвание компании/партнерской программы:",
        reply_markup=get_back_next_keyboard(back_to="business_cards_back_step2")
    )


@router.message(BusinessCardsForm.waiting_for_company)
async def process_business_cards_company(message: Message, state: FSMContext):
    await state.update_data(company=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_contacts)
    await message.answer(
        "Шаг 4 из 5\nУкажите контакты для связи (Telegram/email):",
        reply_markup=get_back_next_keyboard(back_to="business_cards_back_step3")
    )


@router.message(BusinessCardsForm.waiting_for_contacts)
async def process_business_cards_contacts(message: Message, state: FSMContext):
    await state.update_data(contacts=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_brand_style)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="brand_style_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="brand_style_no")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="business_cards_back_step4")]
    ])
    await message.answer(
        "Шаг 5 из 5\nНужно ли придерживаться фирменного стиля?",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("brand_style_"), BusinessCardsForm.waiting_for_brand_style)
async def process_business_cards_brand_style(callback: CallbackQuery, state: FSMContext):
    brand_style = callback.data == "brand_style_yes"
    data = await state.get_data()

    # Сохраняем в БД
    business_cards_data = {
        'username': callback.from_user.username,
        'user_id': callback.from_user.id,
        'full_name': data.get('name', ''),
        'position_en': data.get('position_en', ''),
        'company': data.get('company', ''),
        'contacts': data.get('contacts', ''),
        'brand_style': brand_style
    }

    if await db.save_business_cards_request(business_cards_data):
        await db.log_user_action(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            action="business_cards_request_submitted",
            details={"data": business_cards_data}
        )

    await callback.message.edit_text(
        "✅ Заявка на визитки отправлена!\n\n"
        "Благодарим за ответ, наша команда получила твой запрос. "
        "Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи."
    )
    await state.clear()


async def submit_banner_request(update, state: FSMContext):
    """Отправка заявки на баннер"""
    data = await state.get_data()

    if isinstance(update, Message):
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update
    else:  # CallbackQuery
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update.message

    banner_data = {
        'username': username,
        'user_id': user_id,
        'full_name': data.get('name', ''),
        'position': data.get('position', ''),
        'company': data.get('company', ''),
        'language': data.get('language', ''),
        'photo_required': data.get('photo_required', False),
        'photo_file_id': data.get('photo_id', '')
    }

    # Сохраняем в БД
    if await db.save_banner_request(banner_data):
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="banner_request_submitted",
            details={"request_id": "new", "data": banner_data}
        )

    # ВАЖНО: Добавить отправку сообщения пользователю
    await message_obj.answer(
        "✅ Заявка на баннер отправлена!\n\n"
        "Благодарим за ответ, наша команда получила твой запрос. "
        "Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи."
    )
    await state.clear()

# Обработка кнопки "Назад" в формах
@router.callback_query(F.data.startswith("banner_back_"))
async def handle_banner_back(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки Назад в форме баннера"""
    step = callback.data.split("_")[-1]

    if step == "step1":
        await state.set_state(PRBannerForm.waiting_for_name)
        await callback.message.edit_text(
            "Шаг 1 из 6\nУкажите ваше имя и фамилию:",
            reply_markup=get_back_next_keyboard(back_to="pr_menu", next_disabled=True)
        )
    elif step == "step2":
        await state.set_state(PRBannerForm.waiting_for_position)
        await callback.message.edit_text(
            "Шаг 2 из 6\nНапишите свою должность/роль:",
            reply_markup=get_back_next_keyboard(back_to="banner_step1")
        )


@router.callback_query(F.data == "pr_menu")
async def back_to_pr_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню PR"""
    await state.clear()
    await callback.message.edit_text(
        "📢 Раздел PR\n\nВыберите опцию:",
        reply_markup=get_pr_menu_keyboard()
    )


@router.callback_query(F.data == "pr_question")
async def start_pr_question(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PRQuestionForm.waiting_for_category)

    # Клавиатура с категориями
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Баннеры", callback_data="cat_banner")],
        [InlineKeyboardButton(text="Визитки", callback_data="cat_business_cards")],
        [InlineKeyboardButton(text="Ужин", callback_data="cat_dinner")],
        [InlineKeyboardButton(text="Другое", callback_data="cat_other")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="pr_menu")]
    ])

    await callback.message.edit_text(
        "❓ Вопрос к PR\n\nВыберите категорию вопроса:",
        reply_markup=keyboard
    )


# После существующих обработчиков в pr.py добавить:

@router.callback_query(F.data.startswith("cat_"), PRQuestionForm.waiting_for_category)
async def process_pr_question_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории вопроса PR"""
    category = callback.data.replace("cat_", "")
    await state.update_data(category=category)
    await state.set_state(PRQuestionForm.waiting_for_question)

    await callback.message.edit_text(
        f"📝 Категория: {category}\n\n"
        "Введите ваш вопрос (максимум 500 символов):",
        reply_markup=get_back_next_keyboard(back_to="pr_question", next_disabled=True)
    )


@router.message(PRQuestionForm.waiting_for_question, F.text.len() <= 500)
async def process_pr_question(message: Message, state: FSMContext):
    """Обработка вопроса PR"""
    question_text = message.text
    data = await state.get_data()

    pr_question_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'category': data.get('category', ''),
        'question': question_text
    }

    if await db.save_pr_question(pr_question_data):
        # Отправляем в чат PR-менеджера
        await send_question_to_manager(
            bot=message.bot,  # Используем message.bot
            manager_chat_id=PR_MANAGER_CHAT_ID,
            user_data=pr_question_data,
            question_text=question_text,
            question_type="pr"
        )

        await db.log_user_action(
            user_id=message.from_user.id,
            username=message.from_user.username,
            action="pr_question_submitted",
            details={"data": pr_question_data}
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to PR Menu", callback_data="menu_pr")]
    ])

    await message.answer(
        "✅ Question sent!\n\n"
        "Thank you for your question. Our PR team will contact you soon.",
        reply_markup=keyboard
    )
    await state.clear()


@router.message(PRQuestionForm.waiting_for_question, F.text.len() > 500)
async def process_pr_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    await message.answer("❌ Вопрос слишком длинный. Максимум 500 символов.")


@router.callback_query(F.data == "cancel_form")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    """Отмена заполнения формы"""
    await state.clear()

    # Пытаемся отредактировать, если не получается - отправляем новое
    try:
        await callback.message.edit_text(
            "❌ Cancelled.\n\nBack to PR menu:",
            reply_markup=get_pr_menu_keyboard()
        )
    except:
        await callback.message.answer(
            "❌ Cancelled.\n\nBack to PR menu:",
            reply_markup=get_pr_menu_keyboard()
        )
    await callback.answer()