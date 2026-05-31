# utility/lang_utils.py
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Общие тексты для всего бота
COMMON_TEXTS = {
    'ru': {
        # ============================================
        # НАВИГАЦИЯ
        # ============================================
        'next': "➡️ Далее",
        'back': "◀️ Назад",
        'main_menu': "🏠 Главное меню",
        'cancel': "❌ Отмена",
        'submit': "✅ Отправить",
        'skip': "⏭️ Пропустить",
        'confirm': "✅ Подтвердить",
        'yes': "✅ Да",
        'no': "❌ Нет",
        'confirm_data_storage': "✅ Подтвердить хранение данных",
        'dont_store': "❌ Не хранить",
        'check_again': "🔄 Проверить снова",
        'new_request': "📝 Новая заявка",
        'lang_ru': "🇷🇺 Русский",
        'lang_en': "🇬🇧 English",
        'question_button': "❓Вопрос",

        # ============================================
        # ВЫБОР ЯЗЫКА И РЕГИСТРАЦИЯ
        # ============================================
        'choose_lang': "Пожалуйста, выберите язык / please choose your language:",
        'language_selected': "🇷🇺 Выбран русский язык",
        'ask_fullname': "Пожалуйста, введите ваше имя и фамилию:",
        'ask_position': "Укажите вашу должность:",
        'ask_company': "Укажите полное название партнерской программы/ компании на английском, где вы работаете:",
        'welcome': "Добро пожаловать в Travel Conference Bot!",
        'main_menu_title': "Главное меню. Выберите раздел:",
        'select_conference': "Выберите вашу конференцию:",
        'select_conference_button': "Выбрать конференцию",
        'switch_conference': "🔄 Сменить конференцию",
        'conference_selected': "Выбрана конференция: *{conference}*",
        'back_to_conferences': "◀️ Назад к списку конференций",
        'conference_details_template': "📋 *{name}*\n\n📍 Город: {city}\n📅 Даты конференции: {conf_start} - {conf_end}\n✈️ Даты поездки: {trip_start} - {trip_end}",

        # ============================================
        # ОШИБКИ
        # ============================================
        'error_invalid_name': "❌ Пожалуйста, введите корректное имя (от 3 до 100 символов).",
        'error_invalid_position': "❌ Пожалуйста, введите корректную должность.",
        'error_invalid_company': "❌ Пожалуйста, введите корректное название компании.",
        'error_registration_failed': "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.",
        'error_not_whitelisted': "⛔ Извините, у вас нет доступа к боту конференции.\n\nОбратитесь к своему руководителю.\n\n"
                                 "⛔ Sorry, you do not have access to this conference bot.\n\nPlease contact your manager.",
        'error_validation': "❌ Пожалуйста, введите корректные данные.",
        'error_no_username': "❌ Пожалуйста, установите username в Telegram.",
        'error_no_conferences': "❌ Для вашего аккаунта не найдено конференций.",
        'error_wrong_time_format': "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30)",
        'error_wrong_date_format': "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ",
        'error_invalid_card': "❌ Неверный номер карты. Попробуйте снова:",
        'error_invalid_address': "❌ Адрес слишком короткий. Попробуйте снова:",
        'error_saving_request': "❌ Ошибка сохранения заявки. Пожалуйста, попробуйте позже.",
        'error_loading_requests': "❌ Ошибка загрузки ваших заявок.",
        'form_cancelled': "❌ Заполнение формы отменено.",

        # ============================================
        # ГЛАВНОЕ МЕНЮ
        # ============================================
        'pr': "📢 PR",
        'event': "🎪 EVENT",
        'travel': "✈️ TRAVEL",
        'help': "❓ Помощь",
        'my_profile': "👤 Профиль",
        'help_text': "🆘 Помощь по боту:\n\n• Для возврата в главное меню нажмите кнопку ниже\n• По вопросам доступа обращайтесь к администратору\n",

        # ============================================
        # ПРОФИЛЬ
        # ============================================
        'not_specified': "Не указано",
        'profile_template': "👤 *Ваш профиль*\n\n*ID:* `{userid}`\n*Username:* @{username}\n*Имя:* {full_name}\n*Должность:* {position}\n*Компания:* {company}\n*Язык:* {language}\n*Дата регистрации:* {registered_at}\n\nВыберите действие:",
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
        'field_name': "Имя",
        'field_position': "Должность",
        'field_company': "Компания",
        'field_language': "Язык",

        # ============================================
        # PR РАЗДЕЛ
        # ============================================
        'pr_title': "📢 Раздел PR",
        'pr_banner': "🎨 Баннер",
        'pr_business_cards': "📇 Визитки",
        'pr_dinner': "🍽 Партнерский ужин",
        'pr_conference_bot': "🤖 Бот на конференцию",
        'pr_conference_rules': "📝 Правила поведения",
        'pr_question': "❓ Вопрос PR",
        'pr_banner_form_title': "🎨 Заказ баннера для соцсетей",
        'pr_banner_step1': "Шаг 1 из 5\nУкажите ваше имя и фамилию:",
        'pr_banner_step2': "Шаг 2 из 5\nНапишите свою должность/роль:",
        'pr_banner_step3': "Шаг 3 из 5\nНазвание компании/партнерской программы:",
        'pr_banner_step4': "Шаг 4 из 5\nВыберите желаемый язык баннера:",
        'pr_banner_step5': "Шаг 5 из 6\nПожалуйста, прикрепите изображение",
        'pr_banner_step6': "Шаг 5 из 5\n📝 Ваши комментарии (необязательно):",
        'banner_success': "✅ Заявка на баннер отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",

        # PR Business Cards Form (визитки)
        'business_cards_success': "✅ Заявка на визитки отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",

        'business_cards_title': "📇 Заказ визиток",
        'business_cards_step1': "Шаг 1 из 5\nУкажите имя и фамилию для визитки:",
        'business_cards_step2': "Шаг 2 из 5\nУкажите должность на английском (как будет на визитке):",
        'business_cards_step3': "Шаг 3 из 5\nНазвание компании/партнерской программы:",
        'business_cards_step4': "Шаг 4 из 5\nУкажите контакты для связи (Telegram/email):",
        # 'business_cards_step5': "Шаг 5 из 5\nНужно ли придерживаться фирменного стиля?",
        'business_cards_step6': "Шаг 5 из 5\n📝 Ваши комментарии (необязательно)\n\nЕсли у вас есть дополнительные пожелания к дизайну визиток, напишите их ниже.\n\nИли нажмите 'Пропустить':",
        'business_cards_brand_style_yes': "✅ Да, придерживаться",
        'business_cards_brand_style_no': "❌ Нет, не нужно",
        'business_cards_back_step2': "business_cards_back_step2",
        'business_cards_back_step3': "business_cards_back_step3",
        'business_cards_back_step4': "business_cards_back_step4",
        'business_cards_skip_comments': "⏭️ Пропустить",
        'business_cards_back_to_brand_style': "◀️ Назад",

        # PR Question Form
        'pr_question_title': "❓ Вопрос к PR-отделу",
        'pr_question_prompt': "Напишите ваш вопрос (максимум 500 символов):",
        'pr_question_success': "✅ *Вопрос отправлен!*\n\nБлагодарим за вопрос. Наша PR-команда свяжется с вами в ближайшее время.",
        'pr_question_too_long': "❌ *Вопрос слишком длинный*\n\nМаксимальная длина вопроса - 500 символов.\nПожалуйста, сократите ваш вопрос и попробуйте снова.",

        # PR Conference Bot
        'pr_conference_bot_title': "🤖 Бот на конференцию",
        'pr_conference_bot_no_conferences': "У вас нет активных конференций. Обратитесь к администратору.",
        'pr_conference_bot_description': "Выберите конференцию, чтобы перейти в её бота:\n\n📌 *Примечание:* Боты содержат актуальную информацию о расписании,\nспикерах, локациях и другие важные материалы.\n\n👇 Нажмите на кнопку с нужной конференцией:",
        'pr_conference_bot_button': "🤖 {conference}",

        # Cancel form
        'form_cancelled_message': "❌ Отменено.\n\nВозврат в меню PR:",

        # PR Banner Form (остальные шаги)
        'banner_step2': "Шаг 2 из 6\nНапишите свою должность/роль:",
        'banner_step3': "Шаг 3 из 6\nНазвание компании/партнерской программы:",
        'banner_step4': "Шаг 4 из 6\nВыберите желаемый язык баннера:",
        'banner_step5': "Шаг 5 из 6\nПожалуйста, прикрепите изображение для баннера:",
        'banner_step6': "Шаг 6 из 6\n📝 Ваши комментарии (необязательно)\n\nИли нажмите 'Пропустить':",
        'banner_skip_comments': "⏭️ Пропустить",
        'banner_back_step4': "banner_back_step4",
        'banner_back_step5': "banner_back_step5",
        'banner_back_step6': "banner_back_step6",
        'banner_photo_required_error': "❌ Пожалуйста, пришлите фотографию.\n\nНажмите на скрепку 📎 и выберите фото.",

        # PR Menu back
        'pr_menu_title': "📢 Раздел PR\n\nВыберите опцию:",
        'cards_back_step5': "cards_back_step5",
        'back_to_pr': "◀️ Назад в PR",

        # Кнопки для визиток (callback_data)
        'business_cards_back_step2_cb': "business_cards_back_step2",
        'business_cards_back_step3_cb': "business_cards_back_step3",
        'business_cards_back_step4_cb': "business_cards_back_step4",
        'cards_back_step5_cb': "cards_back_step5",

        # Кнопки для баннера (callback_data)
        'banner_back_step4_cb': "banner_back_step4",
        'banner_back_step5_cb': "banner_back_step5",
        'banner_back_step6_cb': "banner_back_step6",
        'banner_skip_comments_cb': "banner_skip_comments",

        # Кнопки для вопросов
        'cancel_button': "❌ Отмена",

        # ============================================
        # EVENT РАЗДЕЛ
        # ============================================
        'event_title': "🎪 Раздел EVENT",
        'event_ticket': "🎫 Билет на конференцию",
        'event_booth': "ℹ️ О стенде",
        'event_info': "ℹ️ О конференции",
        'event_question': "❓ Вопрос Event департаменту",

        # Билеты
        'start_event_text': "Для покупки билета, пожалуйста, предоставьте следующую информацию\n\n",
        'ticket_step': "Шаг {step} из {total}",
        'ticket_full_name': "Укажите ваши имя и фамилию:",
        'ticket_position': "Ваша должность:",
        'ticket_company': "Название партнерской программы/компании:",
        'ticket_email': "Ваш email (на него придет билет):",
        'ticket_phone': "Ваш номер телефона (для связи):",
        'ticket_country': "Какую страну указывать для регистрации билета?",
        'ticket_success': "✅ Заявка на билет отправлена!\n\nБилет будет отправлен на email: {email}\n\nБлагодарим за ответ! Наша команда обработает ваш запрос и отправит билет в ближайшее время.\n\nСледите за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",
        'ticket_country_prompt': "Пожалуйста, напишите название вашей страны:",
        'error_invalid_country': "❌ Пожалуйста, введите корректное название страны (минимум 2 символа)",

        # В секцию EVENT (после event_question):
        'event_rules': "📋 Правила поведения",
        'event_rules_pdf': "📋 Правила поведения (PDF)",
        'accept_rules': "✅ Я ознакомился(ась)",
        'back_to_event': "◀️ Назад в EVENT",

        # Информация о конференции
        'conference_info_title': "ℹ️ Общая информация о конференции:",
        'conference_name': "📅 Название",
        'conference_city': "📍 Город",
        'conference_dates': "📅 Даты конференции",
        'trip_dates': "✈️ Даты поездки",
        'bot_link': "🤖 Бот конференции",
        'additional_info': "ℹ️ Дополнительная информация",
        'not_specified_info': "Не указано",
        'no_conference_info': "ℹ️ Информация о конференции не найдена.\n\nПожалуйста, обратитесь к организаторам.",

        # Правила поведения (текстовая версия)
        'rules_text': (
            "📋 *Правила поведения на конференции*\n\n"
            "1. Будьте вежливы и уважительны к другим участникам\n"
            "2. Соблюдайте дресс-код: Business casual\n"
            "3. Не опаздывайте на сессии и встречи\n"
            "4. Выключайте звук мобильных устройств во время выступлений\n"
            "5. Соблюдайте чистоту в конференц-зонах\n"
            "6. Фото и видео съемка разрешена только с согласия участников\n"
            "7. Запрещено распространение материалов без разрешения\n\n"
            "Нарушение правил может привести к ограничению доступа."
        ),
        'rules_pdf_caption': "📋 *Правила поведения на конференции*\n\nПожалуйста, ознакомьтесь с правилами.",
        'rules_accepted': "✅ Правила приняты",

        # Для ticket формы
        'error_invalid_email': "❌ Пожалуйста, введите корректный email (пример: name@domain.com):",
        'error_invalid_phone': "❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр):",
        'error_wrong_date_format_range': "❌ Неверный формат дат. Используйте: ДД.ММ.ГГГГ - ДД.ММ.ГГГГ",

        # Для booth информации
        'booth_location': "Стенд находится в главном холле конференц-центра",
        'booth_hours': "Часы работы: 9:00 - 18:00",
        'booth_contact': "Контакты: +7 (999) 123-45-67",
        'booth_info_note': "По всем вопросам обращайтесь к сотрудникам на стенде",

        'event_question_prompt': "Напишите ваш вопрос (максимум 500 символов):",
        # ============================================
        # TRAVEL РАЗДЕЛ
        # ============================================
        'travel_welcome': "✈️ TRAVEL\nВыберите опцию:",
        'travel_title': "✈️ TRAVEL",
        'travel_flight_request': "✈️ Заявка на авиабилет",
        'travel_visa_support': "🛂 Виз. поддержка",
        'travel_flight_info': "ℹ️ О рейсах",
        'travel_hotel': "🏨 Отель",
        'travel_per_diem': "💰 Суточные",
        'travel_my_requests': "📋 Мои заявки",
        'travel_question': "❓ Вопрос",
        'travel_back_to_menu': "◀️ Назад в TRAVEL",

        # Визовая поддержка
        'visa_support_title': "🛂 Визовая поддержка\n\nВыберите ваш статус:",
        'visa_have': "✅ У меня есть виза",
        'visa_not_have': "❌ У меня нет визы",
        'visa_special': "🔄 Особый случай",
        'visa_need_help': "✅ Да, нужна помощь с билетами/отелем",
        'visa_bought_myself': "🛒 Я купил всё сам",
        'special_case_processing': "🔄 Обработка особого случая...",
        'thanks_for_info': "✅ Спасибо за информацию!\n\nОтлично, что вы организовали поездку самостоятельно.\nЕсли у вас есть вопросы, обратитесь к travel-команде.",

        # Паспортные данные
        'passport_consent': "📋 *Согласие на хранение данных*\n\nРазрешаете ли вы хранить ваши паспортные данные для будущих бронирований в течение 6 месяцев?",
        'use_saved_data': "✅ Использовать сохраненные данные",
        'enter_new_data': "✏️ Ввести новые данные",
        'saved_passport_found': "📋 *Найдены сохраненные паспортные данные*\n\nИмя: {first_name} {last_name}\nПаспорт: {passport_number}\n\nИспользовать сохраненные данные?",

        # Форма паспортных данных
        'passport_step1': "Шаг 1 из 10\nВаше имя (как в паспорте):",
        'passport_step2': "Шаг 2 из 10\nВаша фамилия (как в паспорте):",
        'passport_step3': "Шаг 3 из 10\nВаш номер телефона:",
        'passport_step4': "Шаг 4 из 10\nНомер паспорта:",
        'passport_step5': "Шаг 5 из 10\nДата рождения (ДД.ММ.ГГГГ):",
        'passport_step6': "Шаг 6 из 10\nСтрана выдачи паспорта:",
        'passport_step7': "Шаг 7 из 10\nДата выдачи паспорта (ДД.ММ.ГГГГ):",
        'passport_step8': "Шаг 8 из 10\nСрок действия паспорта (ДД.ММ.ГГГГ):",
        'passport_step9': "Шаг 9 из 10\nОткуда планируете вылетать?",
        'passport_step10': "Шаг 10 из 10\nКуда планируете возвращаться?",

        # Багаж и отель
        'baggage_question': "Шаг 11 из 12\nНужен ли зарегистрированный багаж?",
        'baggage_yes': "✅ Да",
        'baggage_no': "❌ Нет",
        'hotel_question': "🏨 *Нужен ли отель?*\n\nБудет ли вам нужен отель для этой конференции?\n\n*Примечание:* Компания не возмещает расходы за самостоятельно забронированные отели или брони для сопровождающих лиц.",
        'hotel_needed_yes': "✅ Да, нужен отель",
        'hotel_needed_no': "❌ Нет, отель не нужен",
        'hotel_booking_note': "🏨 *Бронирование отеля*\n\nЕсли вам нужен отель, пожалуйста, заполните форму заявки на авиабилет. Там будет вопрос о необходимости отеля.\n\nПосле отправки заявки наш travel-менеджер свяжется с вами для уточнения деталей.",

        # Выбор рейса
        'flight_choice': "✈️ *Выберите ваш рейс*\n\nПожалуйста, выберите наиболее удобный рейс:",
        'flight_no_suitable': "❌ Ни один из рейсов не подходит. Свяжитесь со мной",
        'select_conference_for_flight': "✈️ Информация о рейсах\n\nВыберите конференцию:",
        'select_conference_for_hotel': "🏨 Информация об отеле\n\nВыберите конференцию:",
        'no_flights_found': "❌ Информация о рейсах для этой конференции не найдена.",
        'no_hotel_found': "❌ Информация об отеле для этой конференции не найдена.",

        # Информация о рейсах и отелях
        'flight_info_template': "*Рейс {fl_num}*\n\nНомер рейса: {flight_number}\nНомер бронирования: *{book_number}*\n\n📍 *Маршрут*\n{departure_from} → {arrival_city}\n\n🏷 *Дата и время*\nДата: {departure_date}\nВылет: {departure_time}\nПрилет: {arrival_time}\n\n🧳 *Багаж*\nРучная кладь: {carry_luggage} кг\nБагаж: {luggage} кг\n\n🛩️ Авиакомпания: *{airline}*",
        'hotel_info_template': "🏨 *{hotel_name}*\n\n📍 _{hotel_address}_\n\n{hotel_link}\n\nЗабронировано для конференции: *{conference}*",
        'registration_info': "📌 *Регистрация на рейс*\n\nВы можете зарегистрироваться на рейс *за 24 часа до вылета* по этой ссылке:\n",
        'registration_airline': "*{airline}*: {checkin_url}\n",
        'final_text': "\n_Желаем приятного полета!_ 🔥",

        # Суточные
        'per_diem_question': "💰 Суточные\n\nКуда вы хотите получить суточные?",
        'per_diem_card': "💳 Банковская карта",
        'per_diem_crypto': "🪙 Криптокошелек",
        'network_trc20': "TRC20 (USDT)",
        'network_erc20': "ERC20 (USDT)",
        'network_bep20': "BEP20 (USDT/BUSD)",
        'enter_card_number': "💳 Введите номер вашей карты:",
        'enter_crypto_address': "🪙 Введите адрес вашего криптокошелька ({network}):",
        'per_diem_consent': "📝 *Подтверждение*\n\nЯ даю согласие на обработку персональных данных",
        'per_diem_success': "✅ *Заявка на суточные отправлена!*\n\nБлагодарим за запрос. Наша финансовая команда обработает ваши платежные данные и свяжется с вами при необходимости.\n\nПо вопросам обращайтесь к travel-команде через бота.",

        # Вопросы
        'question_to_manager': "❓ Вопрос travel-менеджеру\n\nНапишите ваш вопрос (максимум 500 символов):",
        'question_sent': "✅ *Вопрос отправлен!*\n\nБлагодарим за вопрос. Наша travel-команда свяжется с вами в ближайшее время.",
        'question_too_long': "❌ Вопрос слишком длинный. Максимум 500 символов.",
        'success_question': "✅ *Вопрос отправлен!*\n\nБлагодарим за вопрос. Наша команда свяжется с вами в ближайшее время.",
        'success_rules': "✅ Правила приняты",

        # Мои заявки
        'my_requests_title': "📋 *Ваши travel-заявки*\n\n",
        'visa_status_pending': "🛂 *Визовая поддержка:* ⏳ В обработке\n   Отправлено: {submitted}\n\n",
        'visa_status_no': "🛂 *Визовая поддержка:* 📝 Нет заявок\n\n",
        'flight_status_pending': "✈️ *Заявка на билет:* ⏳ В обработке\n   Отправлено: {submitted}\n\n",
        'flight_status_no': "✈️ *Заявка на билет:* 📝 Нет заявок\n\n",
        'per_diem_status_pending': "💰 *Суточные:* ⏳ В обработке\n   Отправлено: {submitted}\n\n",
        'per_diem_status_no': "💰 *Суточные:* 📝 Нет заявок\n\n",
        'status_footer': "_Вы получите уведомления при изменении статуса._",

        # Успешная отправка формы
        'form_complete': "✅ *Заявка успешно отправлена!*\n\n📋 *Следующие шаги:*\n• Следите за уведомлениями в Telegram\n• Если нужна виза: начните сбор документов\n• Проверяйте email для подтверждения билетов\n• Нажмите 'Мои заявки' для проверки статуса\n\n⏰ *Ожидаемые сроки:*\n• Авиабилеты: 1-3 рабочих дня\n• Визовая поддержка: 5-10 рабочих дней\n• Бронирование отеля: 2-4 рабочих дня\n\n_Наша travel-команда скоро свяжется с вами._",

        # Дополнительные фразы
        'back_to_travel': "◀️ Назад в TRAVEL",
        'travel_flight_form_title': "✈️ Заявка на авиабилет",
        'travel_baggage_question': "Нужен ли багаж?",
        'travel_hotel_question': "Нужен ли отель для этой конференции?\n\n*Примечание:* Компания не возмещает расходы за самостоятельно забронированные отели или брони для сопровождающих лиц.",
        'flight_info_title': "✈️ Информация о рейсах\n\nВыберите конференцию:",
        'hotel_info_title': "🏨 Информация об отеле\n\nВыберите конференцию:",
        'no_flights': "❌ Информация о рейсах для этой конференции не найдена.",
        'no_hotel': "❌ Информация об отеле для этой конференции не найдена.",

        'multiple_companies_found': "🔍 Найдено несколько компаний. Выберите одну:",
        'company_not_found': "Компания '{company}' не найдена в списке.\n\nЕсли это правильное название, нажмите подтвердить.\nИначе нажмите «Повторить ввод» и укажите компанию заново:",
        'multiple_companies_with_input': "🔍 Найдено несколько компаний. Выберите одну или подтвердите свой вариант:\n\nВаш ввод: {company_input}",
        'company_not_found_simple': "Компания '{company}' не найдена в списке.\n\nЕсли это правильное название, нажмите подтвердить.\nИначе введите название заново:",
        'confirm_company': "✅ Подтвердить '{company}'",
        'retry_input': "🔄 Повторить ввод",
        'ask_company_prompt': "Укажите полное название партнерской программы/ компании на английском, где вы работаете:",


        # ===== AFFILIATE MODULE (Партнерские ужины) =====
        'affiliate_welcome': "🍽 Я AffilMeet Модуль.\nЧем могу помочь?",
        'affiliate_restaurants': "🍽 Рестораны",
        'affiliate_report': "📝 Отчет о встрече",
        'affiliate_rules': "ℹ️ Политика конференции",
        'affiliate_limits': "ℹ️ Лимиты расходов",
        'affiliate_cities_list': "📅 Список городов",
        'affiliate_my_bookings': "✅ Мои бронирования",
        'affiliate_choose_action': "Выберите действие:",
        'affiliate_select_city': "🏙 *Выберите город:*",
        'affiliate_restaurants_in_city': "🍽 *Рестораны в {city}:*",
        'affiliate_restaurant': "Ресторан",
        'affiliate_city': "Город",
        'affiliate_address': "Адрес",
        'affiliate_average_bill': "Средний чек",
        'affiliate_link': "Ссылка",
        'affiliate_info': "Информация",
        'affiliate_book_here': "📅 Забронировать",
        'affiliate_back_to_list': "◀️ Назад к списку",
        'affiliate_no_cities': "Нет доступных городов",
        'affiliate_no_restaurants': "🍽 Нет ресторанов в {city}",
        'affiliate_restaurant_not_found': "❌ Ресторан не найден",
        'affiliate_not_specified': "Не указано",
        'affiliate_no_info': "Нет дополнительной информации",
        'affiliate_enter_password': "🔐 Введите пароль для доступа к партнерским ужинам:",
        'affiliate_password_correct': "✅ Пароль верный! Введите название вашей партнерской программы:",
        'affiliate_wrong_password': "❌ Неверный пароль. Попробуйте снова.",
        'affiliate_enter_company': "Введите название вашей партнерской программы:",
        'affiliate_company_empty': "Название компании не может быть пустым. Пожалуйста, введите название партнерской программы:",
        'affiliate_matches_found': "🔍 Найдены совпадающие партнерские программы. Выберите одну:",
        'affiliate_submit_as': "✅ Подтвердить '{company}'",
        'affiliate_try_again': "🔄 Попробовать снова",
        'affiliate_no_matches': "Точных совпадений не найдено. Ваша партнерская программа будет сохранена как '{company}'.\n\nЕсли это правильно, нажмите Подтвердить. Иначе попробуйте ввести другое название.",
        'affiliate_enter_company_again': "Пожалуйста, введите название вашей партнерской программы снова:",
        'affiliate_save_error': "❌ Ошибка сохранения",
        'affiliate_enter_manager_name': "Введите ваше имя (менеджер, участвующий во встрече):",
        'affiliate_select_date': "Выберите дату встречи:",
        'affiliate_enter_time': "Введите время встречи (ЧЧ:ММ, например 14:30):",
        'affiliate_wrong_time_format': "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30)",
        'affiliate_date_selected': "Выбрана дата: {date}",
        'affiliate_wrong_datetime_format': "❌ Неверный формат даты/времени",
        'affiliate_enter_partner_company': "Введите название компании партнера:",
        'affiliate_enter_partner_name': "Введите имя партнера:",
        'affiliate_choose_partner_type': "Выберите тип партнера:",
        'affiliate_vip_partner': "⭐ VIP Партнер",
        'affiliate_regular_partner': "🤝 Обычный партнер",
        'affiliate_regular': "Обычный",
        'affiliate_choose_city': "Выберите город встречи:",
        'affiliate_choose_other_city': "◀️ Выбрать другой город",
        'affiliate_no_restaurants_in_city': "Нет ресторанов в {city}",
        'affiliate_choose_restaurant_in_city': "Выберите ресторан в {city}:",
        'affiliate_choose_payment': "Выберите способ оплаты:",
        'affiliate_payment_card': "💳 Карта",
        'affiliate_payment_cash': "💵 Наличные",
        'affiliate_payment_card_type': "Карта",
        'affiliate_payment_cash_type': "Наличные",
        'affiliate_enter_people_count': "Введите количество человек (включая вас):",
        'affiliate_enter_correct_people': "Введите корректное число (минимум 1)",
        'affiliate_booking_confirmation': "Подтверждение бронирования",
        'affiliate_manager': "Менеджер",
        'affiliate_datetime': "Дата и время",
        'affiliate_partner_company': "Компания партнера",
        'affiliate_partner': "Партнер",
        'affiliate_partner_type': "Тип партнера",
        'affiliate_people': "Количество человек",
        'affiliate_payment': "Оплата",
        'affiliate_is_correct': "Все верно?",
        'affiliate_confirm_yes': "✅ Да, подтвердить",
        'affiliate_confirm_no': "❌ Нет, отменить",
        'affiliate_duplicate_booking': "❌ Найдено дублирующее бронирование! У вас уже есть бронь на это время с этим партнером.",
        'affiliate_booking_saved': "✅ Бронирование успешно сохранено!",
        'affiliate_with_partner': "с",
        'affiliate_from': "из",
        'affiliate_booking_error': "❌ Ошибка сохранения бронирования",
        'affiliate_booking_saved_whats_next': "✅ Бронирование сохранено!\n\nЧто дальше?",
        'affiliate_no_bookings': "Нет бронирований",
        'affiliate_your_bookings': "Ваши бронирования",
        'affiliate_people_lower': "чел",
        'affiliate_create_booking': "📅 Создать бронь",
        'affiliate_new_booking': "📅 Новая бронь",
        'affiliate_enter_manager_name_report': "Введите имя менеджера, участвовавшего во встрече:",
        'affiliate_enter_meeting_date': "Введите дату встречи (ДД.ММ.ГГГГ):",
        'affiliate_enter_partner_name_report': "Введите имя партнера:",
        'affiliate_describe_results': "Опишите результаты встречи:",
        'affiliate_enter_budget': "Введите бюджет встречи (если есть):",
        'affiliate_meeting_report': "Отчет о встрече",
        'affiliate_date': "Дата",
        'affiliate_company': "Компания",
        'affiliate_results': "Результаты",
        'affiliate_budget': "Бюджет",
        'affiliate_send': "✅ Да, отправить",
        'affiliate_report_saved': "✅ Отчет успешно сохранен!",
        'affiliate_results_short': "Результаты",
        'affiliate_report_error': "❌ Ошибка сохранения отчета",
        'affiliate_report_saved_whats_next': "✅ Отчет сохранен!\n\nЧто дальше?",
        'affiliate_conference_policy': "📄 Политика конференции",
        'affiliate_spending_limits': "💰 Лимиты расходов",
        'affiliate_no_access': "⛔ У вас нет доступа к партнерским ужинам",
        'affiliate_wrong_date_format': "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ",

        'help_message': 'Раздел будет дополняться и обновляться',
        'travel_compensation': '🚕 Компенсация за такси и визы',
        'stub_compensation': 'Тут будет информация по компенсации',
        'no_bot_link': 'Извините, у вас нет доступа к боту конференции',
        'stub_rules': 'Тут будут правила поведения',
        'change_conference': '🔄 Сменить конференцию',
    },
    'en': {
        # ============================================
        # NAVIGATION
        # ============================================
        'next': "➡️ Next",
        'back': "◀️ Back",
        'main_menu': "🏠 Main Menu",
        'cancel': "❌ Cancel",
        'submit': "✅ Submit",
        'skip': "⏭️ Skip",
        'confirm': "✅ Confirm",
        'yes': "✅ Yes",
        'no': "❌ No",
        'confirm_data_storage': "✅ Confirm data storage",
        'dont_store': "❌ Don't store",
        'check_again': "🔄 Check again",
        'new_request': "📝 New request",
        'lang_ru': "🇷🇺 Russian",
        'lang_en': "🇬🇧 English",
        'question_button': "❓Question",

        # ============================================
        # LANGUAGE SELECTION AND REGISTRATION
        # ============================================
        'choose_lang': "Please choose your language:",
        'language_selected': "🇬🇧 English selected",
        'ask_fullname': "Please enter your full name:",
        'ask_position': "Enter your job title:",
        'ask_company': "Please provide the full name of the affiliate program/company where you work:",
        'welcome': "Welcome to Travel Conference Bot!",
        'main_menu_title': "Main menu. Select a section:",
        'select_conference': "Select your conference:",
        'select_conference_button': "Select conference",
        'switch_conference': "🔄 Switch conference",
        'conference_selected': "Selected conference: {conference}",
        'back_to_conferences': "◀️ Back to conferences",
        'conference_details_template': "📋 *{name}*\n\n📍 City: {city}\n📅 Conference dates: {conf_start} - {conf_end}\n✈️ Trip dates: {trip_start} - {trip_end}",

        # ============================================
        # ERRORS
        # ============================================
        'error_invalid_name': "❌ Please enter a valid name (3-100 characters).",
        'error_invalid_position': "❌ Please enter a valid job title.",
        'error_invalid_company': "❌ Please enter a valid company name.",
        'error_registration_failed': "❌ Registration error. Please try again later.",
        'error_not_whitelisted': "⛔ Sorry, you do not have access to this conference bot.\n\nPlease contact your manager.",
        'error_validation': "❌ Please enter valid data.",
        'error_no_username': "❌ Please set your Telegram username first.",
        'error_no_conferences': "❌ No conferences found for your account.",
        'error_wrong_time_format': "❌ Wrong time format. Use HH:MM (e.g., 14:30)",
        'error_wrong_date_format': "❌ Wrong date format. Use DD.MM.YYYY",
        'error_invalid_card': "❌ Invalid card number. Try again:",
        'error_invalid_address': "❌ Address too short. Try again:",
        'error_saving_request': "❌ Error saving request. Please try again later.",
        'error_loading_requests': "❌ Error loading your requests.",
        'form_cancelled': "❌ Form cancelled.",

        # ============================================
        # MAIN MENU
        # ============================================
        'pr': "📢 PR",
        'event': "🎪 EVENT",
        'travel': "✈️ TRAVEL",
        'help': "❓ Help",
        'my_profile': "👤 Profile",
        'help_text': "🆘 Bot help:\n\n• To return to main menu press the button below\n• For access issues contact administrator\n",

        # ============================================
        # PROFILE
        # ============================================
        'not_specified': "Not specified",
        'profile_template': "👤 *Your Profile*\n\n*ID:* `{userid}`\n*Username:* @{username}\n*Full name:* {full_name}\n*Position:* {position}\n*Company:* {company}\n*Language:* {language}\n*Registered:* {registered_at}\n\nSelect action:",
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
        'field_name': "Name",
        'field_position': "Position",
        'field_company': "Company",
        'field_language': "Language",

        # ============================================
        # PR SECTION
        # ============================================
        'pr_title': "📢 PR Section",
        'pr_banner': "🎨 Banner",
        'pr_business_cards': "📇 Business Cards",
        'pr_dinner': "🍽 Partner Dinner",
        'pr_conference_bot': "🤖 Conference Bot",
        'pr_conference_rules': "📝 Behaviour rules",
        'pr_question': "❓ Question to PR Department",
        'pr_banner_form_title': "🎨 Banner request for social networks",
        'pr_banner_step1': "Step 1 of 5\nEnter your full name:",
        'pr_banner_step2': "Step 2 of 5\nEnter your job title:",
        'pr_banner_step3': "Step 3 of 5\nEnter the name of your partner program / company name:",
        'pr_banner_step4': "Step 4 of 5\nChoose the language for the banner:",
        'pr_banner_step5': "Step 5 of 6\nPlease attach the image",
        'pr_banner_step6': "Step 5 of 5\nYour comments (optional)"
                                "\n\nOr click 'Skip':",
        'banner_success': "✅ Banner request submitted!\n\nThank you for your response. "
                          "Our team has received your request. "
                          "Keep an eye on notifications so you don’t miss any updates on the task status.",

        # PR Business Cards Form
        'business_cards_title': "📇 Business Card Order",
        'business_cards_step1': "Step 1 of 5\nEnter your name for the business card:",
        'business_cards_step2': "Step 2 of 5\nEnter your job title/role:",
        'business_cards_step3': "Step 3 of 5\nCompany / partner program name:",
        'business_cards_step4': "Step 4 of 5\nEnter contact information (Telegram/email):",
        # 'business_cards_step5': "Step 5 of 5\nShould the corporate style be followed?",
        'business_cards_step6': "Step 5 of 5\nYour comments (optional)"
                                "\n\nOr click 'Skip':",
        'business_cards_brand_style_yes': "✅ Yes, brand style",
        'business_cards_brand_style_no': "❌ No, not needed",
        'business_cards_back_step2': "business_cards_back_step2",
        'business_cards_back_step3': "business_cards_back_step3",
        'business_cards_back_step4': "business_cards_back_step4",
        'business_cards_skip_comments': "⏭️ Skip",
        'business_cards_back_to_brand_style': "◀️ Back",
        'business_cards_success': "✅ Your business card request has been submitted!\n\n"
                                  "Thank you for your response. Our team has received your request. "
                                  "Keep an eye on notifications so you don’t miss any updates on the task status",

        # PR Question Form
        'pr_question_title': "❓ Question to PR Department",
        'pr_question_prompt': "Write your question (max 500 characters):",
        'pr_question_success': "✅ *Question sent!*\n\nThank you for your question. Our PR team will contact you shortly.",
        'pr_question_too_long': "❌ *Question too long*\n\nMaximum question length is 500 characters.\nPlease shorten your question and try again.",

        # PR Conference Bot
        'pr_conference_bot_title': "🤖 Conference Bot",
        'pr_conference_bot_no_conferences': "You have no active conferences. Please contact the administrator.",
        'pr_conference_bot_description': "Select a conference to go to its bot:\n\n📌 "
                                         "*Note:* Bots contain up-to-date information about the schedule,"
                                         "\nspeakers, locations and other important materials.\n\n👇 "
                                         "Click the button with the desired conference:",
        'pr_conference_bot_button': "🤖 {conference}",

        # Cancel form
        'form_cancelled_message': "❌ Cancelled.\n\nReturning to PR menu:",

        'banner_step2': "Step 2 of 6\nEnter your position/role:",
        'banner_step3': "Step 3 of 6\nCompany/partner program name:",
        'banner_step4': "Step 4 of 6\nSelect banner language:",
        'banner_step5': "Step 5 of 6\nPlease attach an image for the banner:",
        'banner_step6': "Step 6 of 6\n📝 Your comments (optional)\n\nOr click 'Skip':",
        'banner_skip_comments': "⏭️ Skip",
        'banner_back_step4': "banner_back_step4",
        'banner_back_step5': "banner_back_step5",
        'banner_back_step6': "banner_back_step6",
        'banner_photo_required_error': "❌ Please send a photo.\n\nClick the paperclip 📎 and select a photo.",

        # PR Menu back
        'pr_menu_title': "📢 PR Section\n\nSelect an option:",
        'cards_back_step5': "cards_back_step5",
        # Buttons for conferences
        'back_to_pr': "◀️ Back to PR",

        # Business cards buttons (callback_data)
        'business_cards_back_step2_cb': "business_cards_back_step2",
        'business_cards_back_step3_cb': "business_cards_back_step3",
        'business_cards_back_step4_cb': "business_cards_back_step4",
        'cards_back_step5_cb': "cards_back_step5",

        # Banner buttons (callback_data)
        'banner_back_step4_cb': "banner_back_step4",
        'banner_back_step5_cb': "banner_back_step5",
        'banner_back_step6_cb': "banner_back_step6",
        'banner_skip_comments_cb': "banner_skip_comments",

        # Question buttons
        'cancel_button': "❌ Cancel",

        # ============================================
        # EVENT SECTION
        # ============================================
        'event_title': "🎪 EVENT Section",
        'event_ticket': "🎫 Conference Ticket",
        'event_booth': "ℹ️ Booth information",
        'event_info': "ℹ️ Event info",
        'event_question': "❓Question to Event Department",


        # Tickets
        'start_event_text': "Please provide the following information to purchase your ticket\n\n",
        'ticket_step': "Step {step} of {total}",
        'ticket_full_name': "Please enter your first and last name for the ticket registration:",
        'ticket_position': "Enter your position / job title:",
        'ticket_company': "Enter your affiliate programme name:",
        'ticket_email': "Enter your email address (ticket will be sent here):",
        'ticket_phone': "Enter your phone number (for contact):",
        'ticket_country': "Which country should be used for ticket registration?",
        'ticket_success': "✅ Your Conference Ticket!\n\nTicket will be sent to: {email}\n\n"
                          "Once the ticket is issued by the administrator, you will receive a notification.\n\n",
        'ticket_country_prompt': "Please write the name of your country:",
        'error_invalid_country': "❌ Please enter a valid country name (minimum 2 characters)",


        'event_rules': "📋 Code of Conduct",
        'event_rules_pdf': "📋 Code of Conduct (PDF)",
        'accept_rules': "✅ I have read and agree",
        'back_to_event': "◀️ Back to EVENT",

        # Conference info
        'conference_info_title': "ℹ️ Conference Information:",
        'conference_name': "📅 Name",
        'conference_city': "📍 City",
        'conference_dates': "📅 Conference dates",
        'trip_dates': "✈️ Trip dates",
        'bot_link': "🤖 Conference bot",
        'additional_info': "ℹ️ Additional information",
        'not_specified_info': "Not specified",
        'no_conference_info': "ℹ️ Conference information not found.\n\nPlease contact the organizers.",

        # Rules text
        'rules_text': (
            "📋 *Conference Code of Conduct*\n\n"
            "1. Be polite and respectful to other participants\n"
            "2. Follow the dress code: Business casual\n"
            "3. Don't be late for sessions and meetings\n"
            "4. Silence mobile devices during presentations\n"
            "5. Keep conference areas clean\n"
            "6. Photo and video recording only with participants' consent\n"
            "7. Distribution of materials without permission is prohibited\n\n"
            "Violation of rules may lead to access restriction."
        ),
        'rules_pdf_caption': "📋 *Conference Code of Conduct*\n\nPlease read the rules carefully.",
        'rules_accepted': "✅ Rules accepted",

        # For ticket form
        'ticket_country_other_prompt': "Please write your country name:",
        'error_invalid_email': "❌ Please enter a valid email address (e.g., name@domain.com):",
        'error_invalid_phone': "❌ Please enter a valid phone number (minimum 4 digits):",
        'error_wrong_date_format_range': "❌ Invalid date format. Use: DD.MM.YYYY - DD.MM.YYYY",

        # For booth information
        'booth_location': "Booth is located in the main hall of the conference center",
        'booth_hours': "Working hours: 9:00 - 18:00",
        'booth_contact': "Contacts: +7 (999) 123-45-67",
        'booth_info_note': "For any questions, please contact the staff at the booth",
        'event_question_prompt': "Write your question (max 500 characters):",
        # ============================================
        # TRAVEL SECTION
        # ============================================
        'travel_welcome': "✈️ TRAVEL\nSelect an option:",
        'travel_title': "✈️ TRAVEL",
        'travel_flight_request': "✈️ Flight Request",
        'travel_visa_support': "🛂 Visa Support",
        'travel_flight_info': "ℹ️ Flight Info",
        'travel_hotel': "🏨 Hotel",
        'travel_per_diem': "💰 Daily allowance",
        'travel_my_requests': "📋 My requests",
        'travel_question': "Question to Travel Department",
        'travel_back_to_menu': "◀️ Back to TRAVEL",

        # Visa support
        'visa_support_title': "🛂 Visa Support\n\nChoose your status:",
        'visa_have': "✅ I have a visa",
        'visa_not_have': "❌ I don't have a visa",
        'visa_special': "🔄 Special case",
        'visa_need_help': "✅ Yes, need help with tickets/hotel",
        'visa_bought_myself': "🛒 I bought everything myself",
        'special_case_processing': "🔄 Processing special case...",
        'thanks_for_info': "✅ Thank you for the information!\n\nGreat that you've organized your travel independently.\nIf you have questions, contact travel team.",

        # Passport data
        'passport_consent': "📋 *Data Storage Consent*\n\nDo you allow us to store your passport data for future bookings within 6 months?",
        'use_saved_data': "✅ Use saved data",
        'enter_new_data': "✏️ Enter new data",
        'saved_passport_found': "📋 *Saved passport data found*\n\nName: {first_name} {last_name}\nPassport: {passport_number}\n\nUse saved data?",

        # Passport form
        'passport_step1': "Step 1 of 10\nYour first name as in passport:",
        'passport_step2': "Step 2 of 10\nYour last name as in passport:",
        'passport_step3': "Step 3 of 10\nYour phone number:",
        'passport_step4': "Step 4 of 10\nPassport number:",
        'passport_step5': "Step 5 of 10\nDate of birth (DD.MM.YYYY):",
        'passport_step6': "Step 6 of 10\nCountry of passport issuance:",
        'passport_step7': "Step 7 of 10\nPassport issue date (DD.MM.YYYY):",
        'passport_step8': "Step 8 of 10\nPassport expiration date (DD.MM.YYYY):",
        'passport_step9': "Step 9 of 10\nWhere are you planning to fly from?",
        'passport_step10': "Step 10 of 10\nWhere are you planning to return to?",

        # Baggage and hotel
        'baggage_question': "Step 11 of 12\nDo you need checked baggage?",
        'baggage_yes': "✅ Yes",
        'baggage_no': "❌ No",
        'hotel_question': "🏨 *Hotel needed?*\n\nWill you need a hotel for this conference?\n\n*Note:* Company does not reimburse independent bookings or +1 accompanying persons.",
        'hotel_needed_yes': "✅ Yes, need hotel",
        'hotel_needed_no': "❌ No, don't need hotel",
        'hotel_booking_note': "🏨 *Hotel Booking*\n\nIf you need a hotel, please fill out the flight request form. There will be a question about hotel needs.\n\nAfter submitting the request, our travel manager will contact you to clarify the details.",

        # Flight selection
        'flight_choice': "✈️ *Choose your flight*\n\nPlease select the most convenient flight:",
        'flight_no_suitable': "❌ None of the flights are suitable. Contact me",
        'select_conference_for_flight': "✈️ Flight Information\n\nSelect the conference:",
        'select_conference_for_hotel': "🏨 Hotel Information\n\nSelect the conference:",
        'no_flights_found': "❌ No flight information found for this conference.",
        'no_hotel_found': "❌ Hotel information not found for this conference.",

        # Flight and hotel info
        'flight_info_template': "*Flight {fl_num}*\n\nFlight number: {flight_number}\nBooking number: *{book_number}*\n\n📍 *Route*\n{departure_from} → {arrival_city}\n\n🏷 *Date & Time*\nDate: {departure_date}\nDeparture: {departure_time}\nArrival: {arrival_time}\n\n🧳 *Luggage*\nCarry-on: {carry_luggage} kg\nChecked: {luggage} kg\n\n🛩️ Airline: *{airline}*",
        'hotel_info_template': "🏨 *{hotel_name}*\n\n📍 _{hotel_address}_\n\n{hotel_link}\n\nBooked for conference: *{conference}*",
        'registration_info': "📌 *Check-in*\n\nYou can check in for your flight *24 hours before departure* using this link:\n",
        'registration_airline': "*{airline}*: {checkin_url}\n",
        'final_text': "\n_Wish you a great flight!_ 🔥",

        # Daily allowance
        'per_diem_question': "💰 Daily allowance\n\nWhere would you like to receive the daily allowance?",
        'per_diem_card': "💳 Bank card",
        'per_diem_crypto': "🪙 Crypto wallet",
        'network_trc20': "TRC20 (USDT)",
        'network_erc20': "ERC20 (USDT)",
        'network_bep20': "BEP20 (USDT/BUSD)",
        'enter_card_number': "💳 Enter your card number:",
        'enter_crypto_address': "🪙 Enter your crypto wallet address ({network}):",
        'per_diem_consent': "📝 *Confirmation*\n\nI consent to the processing of personal data",
        'per_diem_success': "✅ *Daily allowance request submitted!*\n\nThank you for your request. Our finance team will process your payment details and contact you if additional information is needed.\n\nFor questions, contact our travel team via bot.",

        # Questions
        'question_to_manager': "❓ Question to Travel Manager\n\nPlease write your question (max 500 characters):",
        'question_sent': "✅ *Question sent!*\n\nThank you for your question. Our travel team will contact you soon.",
        'question_too_long': "❌ Question is too long. Maximum 500 characters.",
        'success_question': "✅ *Question sent!*\n\nThank you for your question. Our team will contact you shortly.",
        'success_rules': "✅ Rules accepted",

        # My requests
        'my_requests_title': "📋 *Your Travel Requests*\n\n",
        'visa_status_pending': "🛂 *Visa Support:* ⏳ Processing\n   Submitted: {submitted}\n\n",
        'visa_status_no': "🛂 *Visa Support:* 📝 No requests yet\n\n",
        'flight_status_pending': "✈️ *Flight Request:* ⏳ Processing\n   Submitted: {submitted}\n\n",
        'flight_status_no': "✈️ *Flight Request:* 📝 No requests yet\n\n",
        'per_diem_status_pending': "💰 *Daily allowance:* ⏳ Processing\n   Submitted: {submitted}\n\n",
        'per_diem_status_no': "💰 *Daily allowance:* 📝 No requests yet\n\n",
        'status_footer': "_You will receive notifications when status changes._",

        # Form success
        'form_complete': "✅ *Request submitted successfully!*\n\n📋 *Next steps:*\n• Check Telegram notifications for updates\n• If visa needed: start document collection\n• Monitor email for ticket confirmations\n• Click 'My Requests' to check status\n\n⏰ *Expected timeline:*\n• Flight tickets: 1-3 business days\n• Visa processing: 5-10 business days\n• Hotel booking: 2-4 business days\n\n_Our travel team will contact you soon._",

        # Additional phrases
        'back_to_travel': "◀️ Back to TRAVEL",
        'travel_flight_form_title': "✈️ Flight Request",
        'travel_baggage_question': "Do you need baggage?",
        'travel_hotel_question': "Do you need a hotel for this conference?\n\n*Note:* Company does not reimburse independent bookings or +1 accompanying persons.",
        'flight_info_title': "✈️ Flight Information\n\nSelect the conference:",
        'hotel_info_title': "🏨 Hotel Information\n\nSelect the conference:",
        'no_flights': "❌ No flight information found for this conference.",
        'no_hotel': "❌ Hotel information not found for this conference.",

        'multiple_companies_found': "🔍 Multiple companies found. Select one:",
        'company_not_found': "Company '{company}' not found in the list.\n\nIf this is the correct name, click confirm.\nOtherwise click 'Retry input' and enter the company name again:",
        'multiple_companies_with_input': "🔍 Multiple companies found. Select one or confirm your input:\n\nYour input: {company_input}",
        'company_not_found_simple': "Company '{company}' not found in the list.\n\nIf this is the correct name, click confirm.\nOtherwise enter the company name again:",
        'confirm_company': "✅ Confirm '{company}'",
        'retry_input': "🔄 Retry input",
        'ask_company_prompt': "Please provide the full name of the affiliate program/company where you work:",


        # ===== AFFILIATE MODULE (Partner Dinners) =====
        'affiliate_welcome': "🍽 I'm AffilMeet Module.\nHow can I help you?",
        'affiliate_restaurants': "🍽 Restaurants",
        'affiliate_report': "📝 Expense Report",
        'affiliate_rules': "ℹ️ Conference policy",
        'affiliate_limits': "ℹ️ Spending Limits",
        'affiliate_cities_list': "📅 Cities list",
        'affiliate_my_bookings': "✅ My Bookings",
        'affiliate_choose_action': "Choose action:",
        'affiliate_select_city': "🏙 *Select city:*",
        'affiliate_restaurants_in_city': "🍽 *Restaurants in {city}:*",
        'affiliate_restaurant': "Restaurant",
        'affiliate_city': "City",
        'affiliate_address': "Address",
        'affiliate_average_bill': "Average bill",
        'affiliate_link': "Link",
        'affiliate_info': "Info",
        'affiliate_book_here': "📅 Book here",
        'affiliate_back_to_list': "◀️ Back to list",
        'affiliate_no_cities': "No cities available",
        'affiliate_no_restaurants': "🍽 No restaurants in {city}",
        'affiliate_restaurant_not_found': "❌ Restaurant not found",
        'affiliate_not_specified': "Not specified",
        'affiliate_no_info': "No additional info",
        'affiliate_enter_password': "🔐 Enter password for partner dinners access:",
        'affiliate_password_correct': "✅ Password correct! Enter your partner program name:",
        'affiliate_wrong_password': "❌ Wrong password. Try again.",
        'affiliate_enter_company': "Enter your partner program name:",
        'affiliate_company_empty': "Company name cannot be empty. Please enter your partner program name:",
        'affiliate_matches_found': "🔍 Found matching partner programs. Select one:",
        'affiliate_submit_as': "✅ Submit as '{company}'",
        'affiliate_try_again': "🔄 Try again",
        'affiliate_no_matches': "No exact matches found. Your partner program will be saved as '{company}'.\n\nIf this is correct, click Submit. Otherwise, try entering a different name.",
        'affiliate_enter_company_again': "Please enter your partner program name again:",
        'affiliate_save_error': "❌ Error saving",
        'affiliate_enter_manager_name': "Enter your name (manager attending the meeting):",
        'affiliate_select_date': "Select meeting date:",
        'affiliate_enter_time': "Enter meeting time (HH:MM, e.g. 14:30):",
        'affiliate_wrong_time_format': "❌ Wrong time format. Use HH:MM (e.g., 14:30)",
        'affiliate_date_selected': "Date selected: {date}",
        'affiliate_wrong_datetime_format': "❌ Wrong date/time format",
        'affiliate_enter_partner_company': "Enter partner company name:",
        'affiliate_enter_partner_name': "Enter partner name:",
        'affiliate_choose_partner_type': "Choose partner type:",
        'affiliate_vip_partner': "⭐ VIP Partner",
        'affiliate_regular_partner': "🤝 Regular Partner",
        'affiliate_regular': "Regular",
        'affiliate_choose_city': "Choose meeting city:",
        'affiliate_choose_other_city': "◀️ Choose other city",
        'affiliate_no_restaurants_in_city': "No restaurants in {city}",
        'affiliate_choose_restaurant_in_city': "Choose restaurant in {city}:",
        'affiliate_choose_payment': "Choose payment method:",
        'affiliate_payment_card': "💳 Card",
        'affiliate_payment_cash': "💵 Cash",
        'affiliate_payment_card_type': "Card",
        'affiliate_payment_cash_type': "Cash",
        'affiliate_enter_people_count': "Enter number of people (including you):",
        'affiliate_enter_correct_people': "Enter correct number (minimum 1)",
        'affiliate_booking_confirmation': "Booking Confirmation",
        'affiliate_manager': "Manager",
        'affiliate_datetime': "Date & Time",
        'affiliate_partner_company': "Partner Company",
        'affiliate_partner': "Partner",
        'affiliate_partner_type': "Partner Type",
        'affiliate_people': "People",
        'affiliate_payment': "Payment",
        'affiliate_is_correct': "Is everything correct?",
        'affiliate_confirm_yes': "✅ Yes, confirm",
        'affiliate_confirm_no': "❌ No, cancel",
        'affiliate_duplicate_booking': "❌ Duplicate booking found! You already have a booking at this time with this partner.",
        'affiliate_booking_saved': "✅ Booking saved successfully!",
        'affiliate_with_partner': "with",
        'affiliate_from': "from",
        'affiliate_booking_error': "❌ Error saving booking",
        'affiliate_booking_saved_whats_next': "✅ Booking saved!\n\nWhat's next?",
        'affiliate_no_bookings': "No bookings yet",
        'affiliate_your_bookings': "Your bookings",
        'affiliate_people_lower': "people",
        'affiliate_create_booking': "📅 Create booking",
        'affiliate_new_booking': "📅 New booking",
        'affiliate_enter_manager_name_report': "Enter manager name who attended the meeting:",
        'affiliate_enter_meeting_date': "Enter meeting date (DD.MM.YYYY):",
        'affiliate_enter_partner_name_report': "Enter partner name:",
        'affiliate_describe_results': "Describe meeting results:",
        'affiliate_enter_budget': "Enter meeting budget (if any):",
        'affiliate_meeting_report': "Meeting Report",
        'affiliate_date': "Date",
        'affiliate_company': "Company",
        'affiliate_results': "Results",
        'affiliate_budget': "Budget",
        'affiliate_send': "✅ Yes, send",
        'affiliate_report_saved': "✅ Report saved successfully!",
        'affiliate_results_short': "Results",
        'affiliate_report_error': "❌ Error saving report",
        'affiliate_report_saved_whats_next': "✅ Report saved!\n\nWhat's next?",
        'affiliate_conference_policy': "📄 Conference Policy",
        'affiliate_spending_limits': "💰 Spending Limits",
        'affiliate_no_access': "⛔ You do not have access to partner dinners",
        'affiliate_wrong_date_format': "❌ Wrong date format. Use DD.MM.YYYY",

        'help_message': 'This section will be updated and expanded',
        'travel_compensation': '🚕 Taxi and Visa Compensation',
        'stub_compensation': 'Information about compensation will be here',
        'no_bot_link': 'Sorry, you do not have access to the conference bot',
        'stub_rules': 'Here will be the rules of conduct',
        'change_conference': '🔄 Change Conference',

    }
}


async def get_user_lang(user_id: int) -> str:
    """Получить язык пользователя из БД с ленивым импортом"""
    try:
        from database import db
        user_data = await db.get_user_data(user_id)
        return user_data.get('language', 'ru') if user_data else 'ru'
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return 'ru'


async def t(user_id: int, key: str, **kwargs) -> str:
    """Получить локализованный текст для пользователя"""
    lang = await get_user_lang(user_id)
    text = COMMON_TEXTS.get(lang, COMMON_TEXTS['ru']).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} in text '{key}'")
    return text


def get_text_sync(lang: str, key: str, **kwargs) -> str:
    """Синхронная версия для использования в клавиатурах (без await)"""
    text = COMMON_TEXTS.get(lang, COMMON_TEXTS['ru']).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} in text '{key}'")
    return text