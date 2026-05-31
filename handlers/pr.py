from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    waiting_for_photo = State()  # Сразу фото
    waiting_for_comments = State()


class BusinessCardsForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_position_en = State()
    waiting_for_company = State()
    waiting_for_contacts = State()
    # waiting_for_brand_style = State()
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
        # 'brand_style': data.get('brand_style', False),
        'comments': data.get('comments', '')
    }

    if await db.save_business_cards_request(business_cards_data):
        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="business_cards_request_submitted",
            details={"data": business_cards_data}
        )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=await t(user_id, 'main_menu'),
            callback_data="menu_main"
        )
    )

    await message_obj.answer(
        text=await t(user_id, 'business_cards_success'),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data == "pr_conference_bot")
async def show_conference_bot_links(callback: CallbackQuery):
    """Показать ссылки на ботов конференций"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    username = callback.from_user.username
    user_id = callback.from_user.id

    conferences = await db.get_user_active_conferences(username)

    if not conferences:
        await callback.message.edit_text(
            await t(callback.from_user.id, 'pr_conference_bot_title'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=await t(user_id, 'back_to_pr'), callback_data="pr_menu")]
            ])
        )
        return

    builder = InlineKeyboardBuilder()

    BOT_LINKS = {
        "Conference 2024": "",
        "Summit Dubai": "",
        "Business Forum": "",
    }

    for conf in conferences:
        bot_link = BOT_LINKS.get(conf, "")
        builder.row(InlineKeyboardButton(
            text=f"🤖 {conf}",
            url=bot_link
        ))

    builder.row(
        InlineKeyboardButton(text=await t(user_id, 'back_to_pr'), callback_data="pr_menu"),
        InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")
    )

    await callback.message.edit_text(
        await t(user_id, 'pr_conference_bot_description'),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "pr_business_cards")
async def start_business_cards_form(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_name)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'business_cards_title') + "\n\n" + await t(user_id, 'business_cards_step1'),
        reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True, user_id=user_id)
    )


@router.callback_query(F.data == "pr_banner")
async def start_banner_form(callback: CallbackQuery, state: FSMContext):
    """Начало формы для заказа баннера (сразу с фото)"""
    user_id = callback.from_user.id
    await state.set_state(PRBannerForm.waiting_for_name)

    await callback.message.edit_text(
        f"{await t(user_id, 'pr_banner_form_title')}\n\n"
        f"{await t(user_id, 'pr_banner_step1')}",
        reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True, user_id=user_id)
    )


@router.message(PRBannerForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени - Шаг 1/6"""
    await state.update_data(name=message.text)
    await state.set_state(PRBannerForm.waiting_for_position)

    user_id = message.from_user.id
    await message.answer(
        await t(user_id, 'pr_banner_step2'),
        reply_markup=await get_back_next_keyboard(back_to="banner_step1", user_id=user_id)
    )


@router.message(PRBannerForm.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    """Обработка должности - Шаг 2/6"""
    await state.update_data(position=message.text)
    await state.set_state(PRBannerForm.waiting_for_company)

    user_id = message.from_user.id
    await message.answer(
        await t(user_id, 'pr_banner_step3'),
        reply_markup=await get_back_next_keyboard(back_to="banner_step2", user_id=user_id)
    )


@router.message(PRBannerForm.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    """Обработка компании - Шаг 3/6"""
    await state.update_data(company=message.text)
    await state.set_state(PRBannerForm.waiting_for_language)

    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'lang_ru'), callback_data="banner_lang_ru")],
        [InlineKeyboardButton(text=await t(user_id, 'lang_en'), callback_data="banner_lang_en")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="banner_back_step3")]
    ])

    await message.answer(
        await t(user_id, 'pr_banner_step4'),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "banner_back_step4")
async def back_to_language_selection(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору языка"""
    await state.set_state(PRBannerForm.waiting_for_language)
    user_id = callback.from_user.id

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'lang_ru'), callback_data="banner_lang_ru")],
        [InlineKeyboardButton(text=await t(user_id, 'lang_en'), callback_data="banner_lang_en")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="banner_back_step3")]
    ])

    await callback.message.edit_text(
        await t(user_id, 'pr_banner_step4'),
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "banner_back_step3")
async def back_to_company(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу компании"""
    await state.set_state(PRBannerForm.waiting_for_company)
    user_id = callback.from_user.id

    await callback.message.edit_text(
        await t(user_id, 'pr_banner_step3'),
        reply_markup=await get_back_next_keyboard(back_to="banner_step2", user_id=user_id)
    )


@router.callback_query(F.data == "banner_step1")
async def back_to_name_from_position(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу имени (из шага должность)"""
    await state.set_state(PRBannerForm.waiting_for_name)
    user_id = callback.from_user.id

    await callback.message.edit_text(
        await t(user_id, 'pr_banner_step1'),
        reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True, user_id=user_id)
    )


@router.callback_query(F.data == "banner_step2")
async def back_to_position_from_company(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу должности (из шага компания)"""
    await state.set_state(PRBannerForm.waiting_for_position)
    user_id = callback.from_user.id

    await callback.message.edit_text(
        await t(user_id, 'pr_banner_step2'),
        reply_markup=await get_back_next_keyboard(back_to="banner_step1", user_id=user_id)
    )


@router.callback_query(F.data.startswith("banner_lang_"), PRBannerForm.waiting_for_language)
async def process_language(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка - Шаг 4/6, затем запрос фото"""
    lang_map = {
        "banner_lang_ru": "🇷🇺 Русский",
        "banner_lang_en": "🇬🇧 English"
    }
    language = lang_map.get(callback.data, callback.data)
    await state.update_data(language=language)

    # Переходим к загрузке фото (без вопроса)
    await state.set_state(PRBannerForm.waiting_for_photo)

    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'banner_step5'),  # "Шаг 5 из 6\nПожалуйста, прикрепите изображение для баннера:"
        reply_markup=await get_back_next_keyboard(back_to="banner_back_step4", user_id=user_id)
    )
    await callback.answer()


@router.message(PRBannerForm.waiting_for_photo, F.photo)
async def process_photo_upload(message: Message, state: FSMContext):
    """Обработка загруженного фото - Шаг 5/6"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(PRBannerForm.waiting_for_comments)

    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'skip'), callback_data="banner_skip_comments")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="banner_back_step5")]
    ])
    await message.answer(
        await t(user_id, 'banner_step6'),  # "Шаг 6 из 6\n📝 Ваши комментарии (необязательно):"
        reply_markup=keyboard
    )


@router.message(PRBannerForm.waiting_for_photo)
async def process_photo_required(message: Message, state: FSMContext):
    """Если прислали не фото"""
    user_id = message.from_user.id
    await message.answer(
        await t(user_id, 'banner_photo_required_error'),
        reply_markup=await get_back_next_keyboard(back_to="banner_back_step4", user_id=user_id)
    )


@router.message(PRBannerForm.waiting_for_comments, F.text)
async def process_banner_comments(message: Message, state: FSMContext):
    """Обработка комментариев для баннера - Шаг 6/6"""
    await state.update_data(comments=message.text)
    await submit_banner_request(message, state)


@router.callback_query(F.data == "banner_skip_comments", PRBannerForm.waiting_for_comments)
async def skip_banner_comments(callback: CallbackQuery, state: FSMContext):
    """Пропустить комментарии"""
    await state.update_data(comments="")
    await submit_banner_request(callback, state)


@router.callback_query(F.data == "banner_back_step5")
async def back_to_photo(callback: CallbackQuery, state: FSMContext):
    """Назад к загрузке фото"""
    await state.set_state(PRBannerForm.waiting_for_photo)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'banner_step5'),
        reply_markup=await get_back_next_keyboard(back_to="banner_back_step4", user_id=user_id)
    )


async def submit_banner_request(update, state: FSMContext):
    """Отправка заявки на баннер (с фото)"""
    data = await state.get_data()

    if isinstance(update, Message):
        username = update.from_user.username
        user_id = update.from_user.id
        message_obj = update
    else:
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
        'photo_required': True,
        'photo_file_id': data.get('photo_id', ''),
        'comments': data.get('comments', '')
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
        await t(user_id, 'banner_success'),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="pr_menu")],
            [InlineKeyboardButton(text=await t(user_id, 'main_menu'), callback_data="menu_main")]
        ])
    )
    await state.clear()


# ============================================
# BUSINESS CARDS HANDLERS
# ============================================

@router.message(BusinessCardsForm.waiting_for_name)
async def process_business_cards_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_position_en)
    user_id = message.from_user.id
    await message.answer(
        await t(user_id, 'business_cards_step2'),
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step2", user_id=user_id)
    )


@router.message(BusinessCardsForm.waiting_for_position_en)
async def process_business_cards_position(message: Message, state: FSMContext):
    await state.update_data(position_en=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_company)
    user_id = message.from_user.id
    await message.answer(
        await t(user_id, 'business_cards_step3'),
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step3", user_id=user_id)
    )


@router.message(BusinessCardsForm.waiting_for_company)
async def process_business_cards_company(message: Message, state: FSMContext):
    await state.update_data(company=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_contacts)
    user_id = message.from_user.id
    await message.answer(
        await t(user_id, 'business_cards_step4'),
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step4", user_id=user_id)
    )


@router.message(BusinessCardsForm.waiting_for_contacts)
async def process_business_cards_contacts(message: Message, state: FSMContext):
    await state.update_data(contacts=message.text)
    await state.set_state(BusinessCardsForm.waiting_for_comments)  # Сразу к комментариям

    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'skip'), callback_data="cards_skip_comments")],
        [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="business_cards_back_step4")]
    ])
    await message.answer(
        await t(user_id, 'business_cards_step6'),
        reply_markup=keyboard
    )

# @router.callback_query(F.data.startswith("brand_style_"), BusinessCardsForm.waiting_for_brand_style)
# async def process_business_cards_brand_style(callback: CallbackQuery, state: FSMContext):
#     brand_style = callback.data == "brand_style_yes"
#     await state.update_data(brand_style=brand_style)
#     await state.set_state(BusinessCardsForm.waiting_for_comments)
#
#     user_id = callback.from_user.id
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=await t(user_id, 'skip'), callback_data="cards_skip_comments")],
#         [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="business_cards_back_step5")]
#     ])
#     await callback.message.edit_text(
#         await t(user_id, 'business_cards_step6'),
#         reply_markup=keyboard
#     )


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


@router.callback_query(F.data == "business_cards_back_step2")
async def back_to_name_bc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_name)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'business_cards_title') + "\n\n" + await t(user_id, 'business_cards_step1'),
        reply_markup=await get_back_next_keyboard(back_to="pr_menu", next_disabled=True, user_id=user_id)
    )
    await callback.answer()


@router.callback_query(F.data == "business_cards_back_step3")
async def back_to_position_from_company_bc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_position_en)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'business_cards_step2'),
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step2", user_id=user_id)
    )
    await callback.answer()


@router.callback_query(F.data == "business_cards_back_step4")
async def back_to_contacts_from_style(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_contacts)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'business_cards_step4'),
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step3", user_id=user_id)
    )
    await callback.answer()


# @router.callback_query(F.data == "business_cards_back_step5")
# async def back_to_style_from_comments(callback: CallbackQuery, state: FSMContext):
#     await state.set_state(BusinessCardsForm.waiting_for_brand_style)
#     user_id = callback.from_user.id
#
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=await t(user_id, 'business_cards_brand_style_yes'), callback_data="brand_style_yes"),
#          InlineKeyboardButton(text=await t(user_id, 'business_cards_brand_style_no'), callback_data="brand_style_no")],
#         [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="business_cards_back_step4")]
#     ])
#     await callback.message.edit_text(
#         await t(user_id, 'business_cards_step5'),
#         reply_markup=keyboard
#     )
#     await callback.answer()


@router.callback_query(F.data == "business_cards_back_step3_company")
async def back_to_company_from_contacts_bc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BusinessCardsForm.waiting_for_company)
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'business_cards_step3'),
        reply_markup=await get_back_next_keyboard(back_to="business_cards_back_step3", user_id=user_id)
    )
    await callback.answer()


# @router.callback_query(F.data == "cards_back_step5")
# async def back_to_brand_style(callback: CallbackQuery, state: FSMContext):
#     await state.set_state(BusinessCardsForm.waiting_for_brand_style)
#     user_id = callback.from_user.id
#
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=await t(user_id, 'business_cards_brand_style_yes'),
#                               callback_data="brand_style_yes")],
#         [InlineKeyboardButton(text=await t(user_id, 'business_cards_brand_style_no'), callback_data="brand_style_no")],
#         [InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="business_cards_back_step5")]
#     ])
#
#     await callback.message.edit_text(
#         await t(user_id, 'business_cards_step5'),
#         reply_markup=keyboard
#     )


# ============================================
# PR QUESTION
# ============================================

@router.callback_query(F.data == "pr_question")
async def start_pr_question(callback: CallbackQuery, state: FSMContext):
    """Вопрос PR без категорий - сразу ввод текста"""
    await state.set_state(PRQuestionForm.waiting_for_question)

    user_id = callback.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'cancel_button'), callback_data="pr_menu")]
    ])

    await callback.message.edit_text(
        f"{await t(user_id, 'pr_question_title')}\n\n{await t(user_id, 'pr_question_prompt')}\n\n",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "pr_conference_rules")
async def pr_conference_rules_handler(callback: CallbackQuery):
    user_id = callback.from_user.id

    from keyboards import get_pr_menu_keyboard
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=await t(user_id, 'back'), callback_data="menu_pr"))

    text = await t(user_id, 'stub_rules')
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


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

    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=await t(user_id, 'back_to_pr'), callback_data="pr_menu")]
    ])

    await message.answer(
        await t(message.from_user.id, 'pr_question_success'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.clear()


@router.message(PRQuestionForm.waiting_for_question, F.text.len() > 500)
async def process_pr_question_too_long(message: Message):
    """Вопрос слишком длинный"""
    await message.answer(await t(message.from_user.id, 'pr_question_too_long'))


@router.callback_query(F.data == "pr_menu")
async def back_to_pr_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню PR"""
    await state.clear()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        await t(user_id, 'pr_menu_title'),
        reply_markup=await get_pr_menu_keyboard(user_id)
    )


@router.callback_query(F.data == "cancel_form")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    """Отмена заполнения формы"""
    await state.clear()
    user_id = callback.from_user.id

    cancel_text = await t(user_id, 'form_cancelled_message')
    try:
        await callback.message.edit_text(cancel_text, reply_markup=await get_pr_menu_keyboard(user_id))
    except:
        await callback.message.answer(cancel_text, reply_markup=await get_pr_menu_keyboard(user_id))
    await callback.answer()