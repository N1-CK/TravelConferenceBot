from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_pr_menu_keyboard, get_back_next_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import os
from handlers.managers_chat import send_question_to_manager
from utility.lang_utils import *

PR_MANAGER_CHAT_ID = int(os.getenv("TG_PR_MANAGER_CHAT_ID", 0))

router = Router()


class PRBannerForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_language = State()
    waiting_for_photo_choice = State()
    waiting_for_photo = State()
    waiting_for_comments = State()

class BusinessCardsForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_position_en = State()
    waiting_for_company = State()
    waiting_for_contacts = State()
    waiting_for_brand_style = State()
    waiting_for_comments = State()

class PRQuestionForm(StatesGroup):
    waiting_for_category = State()
    waiting_for_question = State()

async def get_selected_conference_text(user_id: int) -> str:
    """Получить текст с выбранной конференцией"""
    selected_conf = await db.get_selected_conference(user_id)
    if selected_conf:
        return f"\n\n📌 *Текущая конференция:* {selected_conf}"
    return ""

async def submit_business_cards_request(update, state: FSMContext):
    """Отправка заявки на визитки с комментариями"""
    data = await state.get_data()

    if isinstance(update, Message):
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update
    else:
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update.message

    business_cards_data = {
        'username': username,
        'user_id': user_id,
        'full_name': data.get('name', ''),
        'position_en': data.get('position_en', ''),
        'company': data.get('company', ''),
        'contacts': data.get('contacts', ''),
        'brand_style': data.get('brand_style', False),
        'comments': data.get('comments', '')  # НОВОЕ ПОЛЕ
    }

    if await db.save_business_cards_request(business_cards_data):
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="business_cards_request_submitted",
            details={"data": business_cards_data}
        )

    await message_obj.answer(
        "✅ Заявка на визитки отправлена!\n\n"
        "Благодарим за ответ, наша команда получила твой запрос. "
        "Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи."
    )
    await state.clear()

@router.callback_query(F.data == "pr_conference_bot")
async def show_conference_bot_links(callback: CallbackQuery):
    """Показать ссылки на ботов конференций"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    username = callback.from_user.username

    # Получаем конференции пользователя
    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            "🤖 Бот на конференцию\n\n"
            "У вас нет активных конференций. Обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="pr_menu")]
            ])
        )
        return

    # Создаем клавиатуру со ссылками на ботов
    builder = InlineKeyboardBuilder()

    # Ссылки на ботов для разных конференций (настройте под свои)
    BOT_LINKS = {
        "Conference 2024": "https://t.me/conference2024_bot",
        "Summit Dubai": "https://t.me/summit_dubai_bot",
        "Business Forum": "https://t.me/business_forum_bot",
    }

    for conf in conferences:
        bot_link = BOT_LINKS.get(conf, "https://t.me/conference_bot")
        builder.row(InlineKeyboardButton(
            text=f"🤖 {conf}",
            url=bot_link
        ))

    builder.row(
        InlineKeyboardButton(text="◀️ Назад в PR", callback_data="pr_menu"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="menu_main")
    )

    await callback.message.edit_text(
        "🤖 **Бот на конференцию**\n\n"
        "Выберите конференцию, чтобы перейти в её бота:\n\n"
        "📌 *Примечание:* Боты содержат актуальную информацию о расписании,\n"
        "спикерах, локациях и другие важные материалы.\n\n"
        "👇 Нажмите на кнопку с нужной конференцией:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "pr_business_cards")
async def start_business_cards_form(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_name)
    await callback.message.edit_text(
        "📇 Заказ визиток\n\nШаг 1 из 5\nУкажите имя и фамилию для визитки:",
        reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True, user_id=callback.from_user.id)
    )


@router.callback_query(F.data == "pr_banner")
async def start_banner_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы для заказа баннера"""
    user_id = callback.from_user.id
    await state.set_state(PRBannerForm.waiting_for_name)

    await callback.message.edit_text(
        f"{await t(user_id, 'pr_banner_form_title')}\n\n"
        f"{await t(user_id, 'pr_banner_step1')}",
        reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True, user_id=user_id)
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
        reply_markup=await get_back_next_keyboard(back_to="banner_step1")
    )


@router.message(PRBannerForm.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    """Обработка должности"""
    await state.update_data(position=message.text)
    await state.set_state(PRBannerForm.waiting_for_company)

    await message.answer(
        "Шаг 3 из 6\n"
        "Название компании/партнерской программы:",
        reply_markup=await get_back_next_keyboard(back_to="banner_step2")
    )


@router.message(PRBannerForm.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    """Обработка компании"""
    await state.update_data(company=message.text)
    await state.set_state(PRBannerForm.waiting_for_language)

    # Клавиатура с выбором языка
    from aiogram.types import KeyboardButton
    from aiogram.utils.keyboard import ReplyKeyboardBuilder

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🇷🇺 Русский"))
    builder.row(KeyboardButton(text="🇬🇧 English"))

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
        [InlineKeyboardButton(text=await t(message.from_user.id, 'yes'), callback_data="banner_photo_yes"),
         InlineKeyboardButton(text=await t(message.from_user.id, 'no'), callback_data="banner_photo_no")],
        [InlineKeyboardButton(text=await t(message.from_user.id, 'back'), callback_data="banner_back_step4")]
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
        "Пожалуйста, прикрепите изображение",
        reply_markup=await get_back_next_keyboard(back_to="banner_step5")
    )


@router.message(PRBannerForm.waiting_for_photo, F.photo)
async def process_photo_upload(message: Message, state: FSMContext):
    """Обработка загруженного фото"""
    # Сохраняем file_id фото
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id, photo_required=True)
    await submit_banner_request(message, state)


@router.callback_query(F.data == "banner_photo_no", PRBannerForm.waiting_for_photo_choice)
async def process_photo_no(callback: CallbackQuery, state: FSMContext):
    """Пользователь НЕ хочет добавлять фото - переходим к комментариям"""
    await state.update_data(photo_required=False, photo_id=None)
    await state.set_state(PRBannerForm.waiting_for_comments)

    await callback.message.edit_text(
        "Шаг 7 из 7\n\n"
        "📝 Ваши комментарии (необязательно)\n\n"
        "Если у вас есть дополнительные пожелания к баннеру, "
        "напишите их ниже.\n\n"
        "Или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="banner_skip_comments")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="banner_back_step6")]
        ])
    )


@router.message(PRBannerForm.waiting_for_comments, F.text)
async def process_banner_comments(message: Message, state: FSMContext):
    """Обработка комментариев для баннера"""
    await state.update_data(comments=message.text)
    await submit_banner_request(message, state)


@router.callback_query(F.data == "banner_skip_comments", PRBannerForm.waiting_for_comments)
async def skip_banner_comments(callback: CallbackQuery, state: FSMContext):
    """Пропустить комментарии"""
    await state.update_data(comments="")
    await submit_banner_request(callback, state)


@router.callback_query(F.data == "banner_back_step6")
async def back_to_photo_choice(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору фото"""
    await state.set_state(PRBannerForm.waiting_for_photo_choice)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(callback.from_user.id, 'yes'), callback_data="banner_photo_yes"),
         InlineKeyboardButton(text=await t(callback.from_user.id, 'no'), callback_data="banner_photo_no")],
        [InlineKeyboardButton(text=await t(callback.from_user.id, 'back'), callback_data="banner_back_step5")]
    ])

    await callback.message.edit_text(
        "Шаг 5 из 7\nДобавить фотографию в баннер?",
        reply_markup=keyboard
    )

@router.message(BusinessCardsForm.waiting_for_name)
async def process_business_cards_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_position_en)
    await message.answer(await t(message.from_user.id, 'banner_step2'))


@router.message(BusinessCardsForm.waiting_for_position_en)
async def process_business_cards_position(message: Message, state: FSMContext):
    await state.update_data(position_en=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_company)
    await message.answer(
        "Шаг 3 из 5\nНазвание компании/партнерской программы:",
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step2")
    )


@router.message(BusinessCardsForm.waiting_for_company)
async def process_business_cards_company(message: Message, state: FSMContext):
    await state.update_data(company=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_contacts)
    await message.answer(
        "Шаг 4 из 5\nУкажите контакты для связи (Telegram/email):",
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step3")
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
    """Обработка выбора фирменного стиля и переход к комментариям"""
    brand_style = callback.data == "brand_style_yes"
    await state.update_data(brand_style=brand_style)
    await state.set_state(BusinessCardsForm.waiting_for_comments)

    await callback.message.edit_text(
        "Шаг 6 из 6\n\n"
        "📝 Ваши комментарии (необязательно)\n\n"
        "Если у вас есть дополнительные пожелания к дизайну визиток, "
        "напишите их ниже.\n\n"
        "Или нажмите 'Пропустить':",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="cards_skip_comments")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="cards_back_step5")]
        ])
    )


# handlers/pr.py - обновить функцию submit_banner_request

async def submit_banner_request(update, state: FSMContext):
    """Отправка заявки на баннер с комментариями"""
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
        'photo_file_id': data.get('photo_id', ''),
        'comments': data.get('comments', '')  # НОВОЕ ПОЛЕ
    }

    # Сохраняем в БД
    if await db.save_banner_request(banner_data):
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="banner_request_submitted",
            details={"request_id": "new", "data": banner_data}
        )

    await message_obj.answer(
        await t(message_obj.from_user.id, 'banner_success'),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(message_obj.from_user.id, 'back'), callback_data="pr_menu")],
            [InlineKeyboardButton(text=await t(message_obj.from_user.id, 'main_menu'), callback_data="menu_main")]
        ])
    )
    await state.clear()


@router.message(BusinessCardsForm.waiting_for_comments, F.text)
async def process_business_cards_comments(message: Message, state: FSMContext):
    """Обработка комментариев для визиток"""
    await state.update_data(comments=message.text)
    await submit_business_cards_request(message, state)


@router.callback_query(F.data == "cards_skip_comments", BusinessCardsForm.waiting_for_comments)
async def skip_business_cards_comments(callback: CallbackQuery, state: FSMContext):
    """Пропустить комментарии"""
    await state.update_data(comments="")
    await submit_business_cards_request(callback, state)


@router.callback_query(F.data == "cards_back_step5")
async def back_to_brand_style(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору фирменного стиля"""
    await state.set_state(BusinessCardsForm.waiting_for_brand_style)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="brand_style_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="brand_style_no")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="business_cards_back_step4")]
    ])

    await callback.message.edit_text(
        "Шаг 5 из 6\nНужно ли придерживаться фирменного стиля?",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("banner_back_"))
async def handle_banner_back(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки Назад в форме баннера"""
    step = callback.data.split("_")[-1]

    if step == "step1":
        await state.set_state(PRBannerForm.waiting_for_name)
        await callback.message.edit_text(
            "Шаг 1 из 6\nУкажите ваше имя и фамилию:",
            reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True)
        )
    elif step == "step2":
        await state.set_state(PRBannerForm.waiting_for_position)
        await callback.message.edit_text(
            "Шаг 2 из 6\nНапишите свою должность/роль:",
            reply_markup=await get_back_next_keyboard(back_to="banner_step1")
        )


@router.callback_query(F.data == "pr_menu")
async def back_to_pr_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню PR"""
    await state.clear()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "📢 Раздел PR\n\nВыберите опцию:",
        reply_markup=await get_pr_menu_keyboard(user_id)
    )


@router.callback_query(F.data == "pr_question")
async def start_pr_question(callback: CallbackQuery, state: FSMContext):
    """Вопрос PR без категорий - сразу ввод текста"""
    await state.set_state(PRQuestionForm.waiting_for_question)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="pr_menu")]
    ])

    await callback.message.edit_text(
        "❓ **Вопрос к PR-отделу**\n\n"
        "Напишите ваш вопрос (максимум 500 символов):\n\n",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.message(PRQuestionForm.waiting_for_question, F.text.len() <= 500)
async def process_pr_question(message: Message, state: FSMContext):
    """Обработка вопроса PR (без категорий)"""
    question_text = message.text

    pr_question_data = {
        'username': message.from_user.username,
        'user_id': message.from_user.id,
        'category': 'general',
        'question': question_text
    }

    if await db.save_pr_question(pr_question_data):
        await send_question_to_manager(
            bot=message.bot,
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
        [InlineKeyboardButton(text="◀️ Назад в PR", callback_data="pr_menu")]
    ])

    await message.answer(
        "✅ **Вопрос отправлен!**\n\n"
        "Благодарим за вопрос. Наша PR-команда свяжется с вами в ближайшее время.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.clear()


@router.message(PRQuestionForm.waiting_for_question, F.text.len() > 500)
async def process_pr_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    await message.answer(
        "❌ **Вопрос слишком длинный**\n\n"
        "Максимальная длина вопроса - 500 символов.\n"
        "Пожалуйста, сократите ваш вопрос и попробуйте снова."
    )

@router.callback_query(F.data == "cancel_form")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    """Отмена заполнения формы"""
    await state.clear()
    user_id = callback.from_user.id

    # Пытаемся отредактировать, если не получается - отправляем новое
    try:
        await callback.message.edit_text(
            "❌ Cancelled.\n\nBack to PR menu:",
            reply_markup=await get_pr_menu_keyboard(user_id)  # Добавлен user_id
        )
    except:
        await callback.message.answer(
            "❌ Cancelled.\n\nBack to PR menu:",
            reply_markup=await get_pr_menu_keyboard(user_id)  # Добавлен user_id
        )
    await callback.answer()