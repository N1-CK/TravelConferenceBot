from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import get_main_menu_keyboard, get_profile_edit_keyboard, get_language_keyboard
from database import db
import logging

logger = logging.getLogger(__name__)
router = Router()

class ProfileEditStates(StatesGroup):
    """Состояния для редактирования профиля"""
    waiting_for_fullname = State()
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_language = State()


@router.callback_query(F.data == "menu_main")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню"""
    await state.clear()  # Очищаем все состояния
    try:
        await callback.message.edit_text(
            "Главное меню. Выберите раздел:",
            reply_markup=get_main_menu_keyboard()
        )
    except:
        await callback.message.delete()
        await callback.answer(
            "Главное меню. Выберите раздел:",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "menu_pr")
async def show_pr_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел PR"""
    from keyboards import get_pr_menu_keyboard

    await callback.message.edit_text(
        "📢 Раздел PR\n\n"
        "Выберите опцию:",
        reply_markup=get_pr_menu_keyboard()
    )


@router.callback_query(F.data == "menu_event")
async def show_event_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел EVENT"""
    from keyboards import get_event_menu_keyboard

    await callback.message.edit_text(
        "🎪 Раздел EVENT\n\n"
        "Выберите опцию:",
        reply_markup=get_event_menu_keyboard()
    )


@router.callback_query(F.data == "menu_travel")
async def show_travel_menu(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел TRAVEL - используем единый travel_module.py"""
    # Вместо прямой загрузки клавиатуры, переходим в travel_module
    from handlers.travel_module import show_travel_menu as travel_menu_handler
    await travel_menu_handler(callback, state)


@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя с данными из БД"""
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Получаем данные пользователя из БД
    user_data = await db.get_user_data(user_id)

    if not user_data:
        # Если данных нет, создаем базовую запись
        user_data = {
            'user_id': user_id,
            'username': username,
            'full_name': callback.from_user.full_name,
            'position': 'Не указано',
            'company': 'Не указано',
            'language': 'ru'
        }
        await db.save_user_registration(user_data)

    # Формируем текст профиля
    profile_text = (
        "👤 *Ваш профиль*\n\n"
        f"*ID:* `{user_id}`\n"
        f"*Username:* @{username}\n"
        f"*Имя:* {user_data.get('full_name', 'Не указано')}\n"
        f"*Должность:* {user_data.get('position', 'Не указано')}\n"
        f"*Компания:* {user_data.get('company', 'Не указано')}\n"
        f"*Язык:* {'🇷🇺 Русский' if user_data.get('language') == 'ru' else '🇬🇧 English'}\n"
        f"*Дата регистрации:* {user_data.get('registered_at', 'Не указано').strftime('%d.%m.%Y') if user_data.get('registered_at') else 'Не указано'}\n\n"
        "Выберите действие:"
    )

    # Клавиатура с кнопками редактирования
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить имя", callback_data="profile_edit_name"),
        InlineKeyboardButton(text="✏️ Изменить должность", callback_data="profile_edit_position")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить компанию", callback_data="profile_edit_company"),
        InlineKeyboardButton(text="🌐 Сменить язык", callback_data="profile_edit_language")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить профиль", callback_data="profile_refresh"),
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")
    )

    await callback.message.edit_text(
        profile_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "profile_refresh")
async def refresh_profile(callback: CallbackQuery):
    """Обновить отображение профиля"""
    await show_profile(callback)


@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery):
    """Показать помощь"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from keyboards import get_main_menu_keyboard

    # Создаем клавиатуру с кнопкой "Главное меню"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")]
    ])

    await callback.message.edit_text(
        "🆘 Помощь по боту:\n\n"
        "• Для возврата в главное меню нажмите кнопку ниже\n"
        "• По вопросам доступа обращайтесь к администратору\n"
        "• Технические проблемы: support@conference.com",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "profile_edit_name")
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования имени"""
    await state.set_state(ProfileEditStates.waiting_for_fullname)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_profile")]
    ])

    await callback.message.edit_text(
        "✏️ *Редактирование имени*\n\n"
        "Введите ваше имя и фамилию:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(ProfileEditStates.waiting_for_fullname)
async def process_name_edit(message: Message, state: FSMContext):
    """Обработка нового имени"""
    user_id = message.from_user.id
    new_name = message.text.strip()

    # Валидация
    if len(new_name) < 2 or len(new_name) > 100:
        await message.answer(
            "❌ Имя должно содержать от 2 до 100 символов.\n"
            "Попробуйте еще раз или нажмите /cancel"
        )
        return

    # Обновляем в БД
    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {db.db_schema}.user_profiles 
                SET full_name = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_name, user_id)

        # Логируем действие
        await db.log_user_action(
            user_id=user_id,
            username=message.from_user.username,
            action="profile_updated",
            details={"field": "full_name", "new_value": new_name}
        )

        await message.answer("✅ Имя успешно обновлено!")

        # Возвращаемся к профилю (отправляем новое сообщение)
        await show_profile_as_new_message(message)

    except Exception as e:
        logger.error(f"Error updating name: {e}")
        await message.answer("❌ Ошибка при обновлении имени. Попробуйте позже.")

    await state.clear()


# ============================================
# РЕДАКТИРОВАНИЕ ДОЛЖНОСТИ
# ============================================

@router.callback_query(F.data == "profile_edit_position")
async def edit_position_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования должности"""
    await state.set_state(ProfileEditStates.waiting_for_position)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_profile")]
    ])

    await callback.message.edit_text(
        "✏️ *Редактирование должности*\n\n"
        "Введите вашу должность:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(ProfileEditStates.waiting_for_position)
async def process_position_edit(message: Message, state: FSMContext):
    """Обработка новой должности"""
    user_id = message.from_user.id
    new_position = message.text.strip()

    if len(new_position) < 2 or len(new_position) > 100:
        await message.answer(
            "❌ Должность должна содержать от 2 до 100 символов.\n"
            "Попробуйте еще раз или нажмите /cancel"
        )
        return

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {db.db_schema}.user_profiles 
                SET position = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_position, user_id)

        await db.log_user_action(
            user_id=user_id,
            username=message.from_user.username,
            action="profile_updated",
            details={"field": "position", "new_value": new_position}
        )

        await message.answer("✅ Должность успешно обновлена!")
        await show_profile_as_new_message(message)

    except Exception as e:
        logger.error(f"Error updating position: {e}")
        await message.answer("❌ Ошибка при обновлении должности.")

    await state.clear()


# ============================================
# РЕДАКТИРОВАНИЕ КОМПАНИИ
# ============================================

@router.callback_query(F.data == "profile_edit_company")
async def edit_company_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования компании"""
    await state.set_state(ProfileEditStates.waiting_for_company)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_profile")]
    ])

    await callback.message.edit_text(
        "✏️ *Редактирование компании*\n\n"
        "Введите название вашей компании или партнерской программы:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(ProfileEditStates.waiting_for_company)
async def process_company_edit(message: Message, state: FSMContext):
    """Обработка новой компании"""
    user_id = message.from_user.id
    username = message.from_user.username
    new_company = message.text.strip()

    if len(new_company) < 2 or len(new_company) > 100:
        await message.answer(
            "❌ Название компании должно содержать от 2 до 100 символов.\n"
            "Попробуйте еще раз или нажмите /cancel"
        )
        return

    try:
        async with db.pool.acquire() as conn:
            # Обновляем в user_profiles
            await conn.execute(f"""
                UPDATE {db.db_schema}.user_profiles 
                SET company = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_company, user_id)

            # Также обновляем в user_company для совместимости
            await conn.execute(f"""
                INSERT INTO {db.db_schema}.user_company (user_id, username, company, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET company = EXCLUDED.company,
                    username = EXCLUDED.username,
                    updated_at = NOW()
            """, user_id, username, new_company)

        await db.log_user_action(
            user_id=user_id,
            username=username,
            action="profile_updated",
            details={"field": "company", "new_value": new_company}
        )

        await message.answer("✅ Компания успешно обновлена!")
        await show_profile_as_new_message(message)

    except Exception as e:
        logger.error(f"Error updating company: {e}")
        await message.answer("❌ Ошибка при обновлении компании.")

    await state.clear()


# ============================================
# РЕДАКТИРОВАНИЕ ЯЗЫКА
# ============================================

@router.callback_query(F.data == "profile_edit_language")
async def edit_language_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования языка"""
    await state.set_state(ProfileEditStates.waiting_for_language)

    # Клавиатура выбора языка
    from keyboards import get_language_keyboard

    await callback.message.edit_text(
        "🌐 *Выберите язык интерфейса*\n\n"
        "Выберите предпочитаемый язык:",
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("lang_"), ProfileEditStates.waiting_for_language)
async def process_language_edit(callback: CallbackQuery, state: FSMContext):
    """Обработка нового языка"""
    user_id = callback.from_user.id
    new_lang = callback.data.split("_")[1]  # 'ru' или 'en'

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {db.db_schema}.user_profiles 
                SET language = $1, updated_at = NOW()
                WHERE user_id = $2
            """, new_lang, user_id)

        await db.log_user_action(
            user_id=user_id,
            username=callback.from_user.username,
            action="profile_updated",
            details={"field": "language", "new_value": new_lang}
        )

        # Уведомление на выбранном языке
        confirm_text = "✅ Language updated to English!" if new_lang == "en" else "✅ Язык обновлен на русский!"
        await callback.message.edit_text(confirm_text)

        # Возвращаемся к профилю
        await show_profile(callback)

    except Exception as e:
        logger.error(f"Error updating language: {e}")
        await callback.message.edit_text("❌ Ошибка при обновлении языка.")

    await state.clear()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def show_profile_as_new_message(message: Message):
    """Показать профиль как новое сообщение (когда нельзя отредактировать)"""
    user_id = message.from_user.id
    username = message.from_user.username

    user_data = await db.get_user_data(user_id)

    if not user_data:
        user_data = {
            'full_name': message.from_user.full_name,
            'position': 'Не указано',
            'company': 'Не указано',
            'language': 'ru'
        }

    profile_text = (
        "👤 *Ваш профиль*\n\n"
        f"*ID:* `{user_id}`\n"
        f"*Username:* @{username}\n"
        f"*Имя:* {user_data.get('full_name', 'Не указано')}\n"
        f"*Должность:* {user_data.get('position', 'Не указано')}\n"
        f"*Компания:* {user_data.get('company', 'Не указано')}\n"
        f"*Язык:* {'🇷🇺 Русский' if user_data.get('language') == 'ru' else '🇬🇧 English'}\n\n"
        "Выберите действие:"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить имя", callback_data="profile_edit_name"),
        InlineKeyboardButton(text="✏️ Изменить должность", callback_data="profile_edit_position")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить компанию", callback_data="profile_edit_company"),
        InlineKeyboardButton(text="🌐 Сменить язык", callback_data="profile_edit_language")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="profile_refresh"),
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")
    )

    await message.answer(
        profile_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


# Обработчик отмены
@router.message(lambda message: message.text == "/cancel")
async def cancel_edit(message: Message, state: FSMContext):
    """Отмена редактирования"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("❌ Редактирование отменено.")
        # Показываем профиль
        await show_profile_as_new_message(message)