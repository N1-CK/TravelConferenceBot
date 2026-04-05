# utils/lang_utils.py
from database import db
from typing import Dict, Any

# Общие тексты для всего бота
COMMON_TEXTS = {
    'ru': {
        # Навигация
        'next': "➡️ Далее",
        'back': "◀️ Назад",
        'main_menu': "🏠 Главное меню",
        'cancel': "❌ Отмена",
        'submit': "✅ Отправить",
        'skip': "⏭️ Пропустить",
        'confirm': "✅ Подтвердить",
        'select_conference': "Выберите конференцию:",
        'conference_selected': "Выбрана конференция: *{conference}*",
        'switch_conference': "🔄 Сменить конференцию",
        'select_conference_button': "🎯 Выбрать конференцию",
        'my_profile': "👤 Профиль",
        'help': "❓ Помощь",

        # Выбор языка
        'choose_lang': "Пожалуйста, выберите язык / please choose your language:",
        'language_selected': "🇷🇺 Выбран русский язык",

        # Start.py, если пользователь в белом списке
        'ask_fullname': "Пожалуйста, введите ваше имя и фамилию:",
        'ask_position': "Укажите вашу должность:",
        'ask_company': "Укажите название вашей компании / партнерской программы:",
        'welcome': "Добро пожаловать в Travel Conference Bot!",
        'main_menu_title': "Главное меню. Выберите раздел:",
        'error_invalid_name': "❌ Пожалуйста, введите корректное имя (от 3 до 100 символов).",
        'error_invalid_position': "❌ Пожалуйста, введите корректную должность.",
        'error_invalid_company': "❌ Пожалуйста, введите корректное название компании.",
        'error_registration_failed': "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.",
        'back_to_conferences': "◀️ Назад к списку конференций",
        'conference_details_template': "📋 *{name}*\n\n📍 Город: {city}\n📅 Даты конференции: {conf_start} - {conf_end}\n✈️ Даты поездки: {trip_start} - {trip_end}",



        # Главное меню
        'pr': "📢 PR",
        'event': "🎪 EVENT",
        'travel': "✈️ TRAVEL",

        # PR раздел
        'pr_title': "📢 Раздел PR",
        'pr_banner': "🎨 Баннер",
        'pr_business_cards': "📇 Визитки",
        'pr_dinner': "🍽 Партнерский ужин",
        'pr_conference_bot': "🤖 Бот на конференцию",
        'pr_question': "❓ Вопрос PR",
        'pr_banner_form_title': "🎨 Заказ баннера для соцсетей",
        'pr_banner_step1': "Укажите ваше имя и фамилию:",
        'pr_banner_step2': "Напишите свою должность/роль:",
        'pr_banner_step3': "Название компании/партнерской программы:",
        'pr_banner_step4': "Выберите желаемый язык баннера:",
        'pr_banner_step5': "Добавить фотографию в баннер?",
        'pr_banner_step6': "Пожалуйста, прикрепите изображение:",
        'pr_banner_step7': "📝 Ваши комментарии (необязательно):",


        # EVENT раздел
        'event_title': "🎪 Раздел EVENT",
        'event_ticket': "🎫 Билет на конференцию",
        'event_booth': "ℹ️ О стенде",
        'event_info': "ℹ️ О конференции",
        'event_question': "❓ Вопрос",
        'event_certificate_form_title': "📄 Справка-вызов",
        'event_certificate_step1': "Укажите ФИО:",
        'event_certificate_step2': "Укажите должность:",
        'event_certificate_step3': "Название компании:",
        'event_certificate_step4': "Юридические данные компании (ИНН, ОГРН и т.д.):",
        'event_certificate_step5': "Кому адресовать справку? (ФИО, должность):",
        'event_certificate_step6': "Даты участия (например: 15.11.2024 - 17.11.2024):",

        # TRAVEL раздел
        'travel_title': "✈️ TRAVEL Section",
        'travel_flight_request': "✈️ Flight Request",
        'travel_visa_support': "🛂 Visa Support",
        'travel_flight_info': "ℹ️ Flight Info",
        'travel_hotel': "🏨 Hotel",
        'travel_per_diem': "💰 Daily allowance",
        'travel_my_requests': "📋 My requests",
        'travel_question': "❓ Question",
        'travel_flight_form_title': "✈️ Заявка на авиабилет",
        'travel_passport_step1': "Имя (как в паспорте):",
        'travel_passport_step2': "Фамилия (как в паспорте):",
        'travel_passport_step3': "Номер телефона:",
        'travel_passport_step4': "Номер паспорта:",
        'travel_passport_step5': "Дата рождения (ДД.ММ.ГГГГ):",
        'travel_passport_step6': "Страна выдачи паспорта:",
        'travel_passport_step7': "Дата выдачи паспорта (ДД.ММ.ГГГГ):",
        'travel_passport_step8': "Срок действия паспорта (ДД.ММ.ГГГГ):",
        'travel_passport_step9': "Откуда планируете вылетать?",
        'travel_passport_step10': "Куда планируете возвращаться?",
        'travel_baggage_question': "Нужен ли багаж?",
        'travel_hotel_question': "Нужен ли отель для этой конференции?\n\n*Примечание:* Компания не возмещает расходы за самостоятельно забронированные отели или брони для сопровождающих лиц.",
        'travel_welcome': "✈️ TRAVEL Section\n\nChoose an option:",
        'per_diem_question': "💰 Daily allowance\n\nWhere would you like to receive the Daily allowance?",
        'per_diem_card': "💳 Bank card (RF/RB)",
        'per_diem_crypto': "🪙 Crypto wallet",
        'network_trc20': "TRC20",
        'network_erc20': "ERC20",
        'network_bep20': "BEP20",


        # Формы
        'ticket_step': "Шаг {step} из {total}",
        'ticket_full_name': "Укажите ваши имя и фамилию (как в паспорте):",
        'ticket_position': "Ваша должность:",
        'ticket_company': "Название партнерской программы/компании:",
        'ticket_email': "Ваш email (на него придет билет):",
        'ticket_phone': "Ваш номер телефона (для связи):",
        'ticket_country': "Какую страну указывать для регистрации билета?\n\nВыберите из списка:",
        'ticket_success': "✅ **Заявка на билет отправлена!**\n\n📧 Билет будет отправлен на email: {email}\n\nБлагодарим за ответ! Наша команда обработает ваш запрос и отправит билет в ближайшее время.\n\nСледите за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",

        # Успешные сообщения
        'success_certificate': "✅ Заявка на справку-вызов отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",
        'success_question': "✅ **Вопрос отправлен!**\n\nБлагодарим за вопрос. Наша команда свяжется с вами в ближайшее время.",
        'success_rules': "✅ Правила приняты",

        # Ошибки
        'error_no_username': "❌ У вас не установлен username в Telegram.\n\nПожалуйста, установите username в настройках Telegram и попробуйте снова.",
        'error_not_whitelisted': "⛔ Извините, у вас нет доступа к боту конференции.\n\nОбратитесь к своему руководителю.",
        'error_validation': "❌ Пожалуйста, введите корректные данные.",

        # Профиль
        'not_specified': "Не указано",
        'profile_template': "👤 *Ваш профиль*\n\n*ID:* `{user_id}`\n*Username:* @{username}\n*Имя:* {full_name}\n*Должность:* {position}\n*Компания:* {company}\n*Язык:* {language}\n*Дата регистрации:* {registered_at}\n\nВыберите действие:",
        'edit_name': "✏️ Изменить имя",
        'edit_position': "✏️ Изменить должность",
        'edit_company': "✏️ Изменить компанию",
        'edit_language': "🌐 Сменить язык",
        'refresh_profile': "🔄 Обновить профиль",
        'edit_name_title': "✏️ *Редактирование имени*\n\nВведите ваше имя и фамилию:",
        'edit_position_title': "✏️ *Редактирование должности*\n\nВведите вашу должность:",
        'edit_company_title': "✏️ *Редактирование компании*\n\nВведите название вашей компании или партнерской программы:",
        'edit_language_title': "🌐 *Выберите язык интерфейса*\n\nВыберите предпочитаемый язык:",
        'profile_updated': "✅ {field} успешно обновлено!",
        'profile_update_error': "❌ Ошибка при обновлении {field}. Попробуйте позже.",
        'cancel_edit': "❌ Редактирование отменено.",
        'help_text': "🆘 Помощь по боту:\n\n• Для возврата в главное меню нажмите кнопку ниже\n• По вопросам доступа обращайтесь к администратору\n• Технические проблемы: support@conference.com",
    },
    'en': {
        # Navigation
        'back': "◀️ Back",
        'main_menu': "🏠 Main Menu",
        'cancel': "❌ Cancel",
        'submit': "✅ Submit",
        'skip': "⏭️ Skip",
        'confirm': "✅ Confirm",

        # Главное меню
        'pr': "📢 PR",
        'event': "🎪 EVENT",
        'travel': "✈️ TRAVEL",

        #start.py
        'choose_lang': "Пожалуйста, выберите язык / please choose your language:",
        'language_selected': "🇬🇧 English selected",
        'ask_fullname': "Please enter your full name:",
        'ask_position': "Enter your job title:",
        'ask_company': "Enter your company/partner program name:",
        'welcome': "Welcome to Travel Conference Bot!",
        'main_menu_title': "Main menu. Select a section:",
        'error_invalid_name': "❌ Please enter a valid name (3-100 characters).",
        'error_invalid_position': "❌ Please enter a valid job title.",
        'error_invalid_company': "❌ Please enter a valid company name.",
        'error_registration_failed': "❌ Registration error. Please try again later.",
        'back_to_conferences': "◀️ Back to conferences",
        'conference_details_template': "📋 *{name}*\n\n📍 City: {city}\n📅 Conference dates: {conf_start} - {conf_end}\n✈️ Trip dates: {trip_start} - {trip_end}",


        'select_conference': "Choose your conference:",
        'conference_selected': "Chosen conference is: *{conference}*",
        'switch_conference': "🔄 Choose another conference",
        'select_conference_button': "Choose your conference",

        # PR section
        'pr_title': "📢 PR Section",
        'pr_banner': "🎨 Banner",
        'pr_business_cards': "📇 Business Cards",
        'pr_dinner': "🍽 Partner Dinner",
        'pr_conference_bot': "🤖 Conference Bot",
        'pr_question': "❓ Question to PR",


        # EVENT section
        'event_title': "🎪 EVENT Section",
        'event_ticket': "🎫 Conference Ticket",
        'event_booth': "ℹ️ About Booth",
        'event_info': "ℹ️ About Conference",
        'event_question': "❓ Question",

        # TRAVEL section
        'travel_title': "✈️ TRAVEL Section",
        'travel_flight_request': "✈️ Flight Request",
        'travel_visa_support': "🛂 Visa Support",
        'travel_flight_info': "ℹ️ Flight Info",
        'travel_hotel': "🏨 Hotel",
        'travel_per_diem': "💰 Daily allowance",
        'travel_my_requests': "📋 My requests",
        'travel_question': "❓ Question",
        'travel_welcome': "✈️ TRAVEL Section\n\nChoose an option:",
        'per_diem_question': "💰 Daily allowance\n\nWhere would you like to receive the Daily allowance?",
        'per_diem_card': "💳 Bank card (RF/RB)",
        'per_diem_crypto': "🪙 Crypto wallet",
        'network_trc20': "TRC20",
        'network_erc20': "ERC20",
        'network_bep20': "BEP20",

        # Forms
        'ticket_step': "Step {step} of {total}",
        'ticket_full_name': "✍️ Please enter your full name (as in passport):",
        'ticket_position': "💼 Your position:",
        'ticket_company': "🏢 Partner program/company name:",
        'ticket_email': "📧 Your email (ticket will be sent here):",
        'ticket_phone': "📱 Your phone number (for contact):",
        'ticket_country': "🌍 Which country should be used for ticket registration?\n\nSelect from the list:",
        'ticket_success': "✅ **Ticket request submitted!**\n\n📧 Ticket will be sent to: {email}\n\nThank you for your response! Our team will process your request and send the ticket shortly.\n\nFollow notifications for updates on your request status.",

        # Success messages
        'success_certificate': "✅ Certificate request submitted!\n\nThank you for your response! Our team has received your request. Follow notifications for updates.",
        'success_question': "✅ **Question sent!**\n\nThank you for your question. Our team will contact you shortly.",
        'success_rules': "✅ Rules accepted",

        # Errors
        'error_no_username': "❌ You don't have a username set in Telegram.\n\nPlease set your username in Telegram settings and try again.",
        'error_not_whitelisted': "⛔ Sorry, you do not have access to this conference bot.\n\nPlease contact your manager.",
        'error_validation': "❌ Please enter valid data.",

        # Profile
        'not_specified': "Not specified",
        'profile_template': "👤 *Your Profile*\n\n*ID:* `{user_id}`\n*Username:* @{username}\n*Full name:* {full_name}\n*Position:* {position}\n*Company:* {company}\n*Language:* {language}\n*Registered:* {registered_at}\n\nSelect action:",
        'edit_name': "✏️ Edit name",
        'edit_position': "✏️ Edit position",
        'edit_company': "✏️ Edit company",
        'edit_language': "🌐 Change language",
        'refresh_profile': "🔄 Refresh profile",
        'edit_name_title': "✏️ *Edit name*\n\nEnter your full name:",
        'edit_position_title': "✏️ *Edit position*\n\nEnter your position:",
        'edit_company_title': "✏️ *Edit company*\n\nEnter your company or partner program name:",
        'edit_language_title': "🌐 *Select interface language*\n\nChoose your preferred language:",
        'profile_updated': "✅ {field} updated successfully!",
        'profile_update_error': "❌ Error updating {field}. Please try again later.",
        'cancel_edit': "❌ Edit cancelled.",
        'help_text': "🆘 Bot help:\n\n• To return to main menu press the button below\n• For access issues contact administrator\n• Technical problems: support@conference.com",
        'help': "❓ Help",
        'my_profile': "👤 Profile",
    }
}


async def get_user_lang(user_id: int) -> str:
    """Получить язык пользователя из БД"""
    try:
        user_data = await db.get_user_data(user_id)
        return user_data.get('language', 'ru') if user_data else 'ru'
    except Exception:
        return 'ru'


async def t(user_id: int, key: str, **kwargs) -> str:
    """Получить локализованный текст для пользователя"""
    lang = await get_user_lang(user_id)
    text = COMMON_TEXTS.get(lang, COMMON_TEXTS['ru']).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_text_sync(lang: str, key: str, **kwargs) -> str:
    """Синхронная версия для использования в клавиатурах (без await)"""
    text = COMMON_TEXTS.get(lang, COMMON_TEXTS['ru']).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text