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
        'yes': "✅ Да",
        'no': "❌ Нет",

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
        'pr_banner_step6': "Пожалуйста, прикрепите изображение",
        'pr_banner_step7': "📝 Ваши комментарии (необязательно):",
        'banner_success': "✅ Заявка на баннер отправлена!\n\nБлагодарим за ответ, наша команда получила твой запрос. Следи за уведомлениями, чтобы не пропустить обновлений по статусу задачи.",


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

        'error_not_whitelisted': "⛔ Извините, у вас нет доступа к боту конференции.\n\nОбратитесь к своему руководителю.",
        'error_validation': "❌ Пожалуйста, введите корректные данные.",

        # Профиль
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
        'help_text': "🆘 Помощь по боту:\n\n• Для возврата в главное меню нажмите кнопку ниже\n• По вопросам доступа обращайтесь к администратору\n• Технические проблемы: support@conference.com",

        # ========== TRAVEL РАЗДЕЛ ==========
        # Главное меню
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

        'flight_info_title': "✈️ Информация о рейсах\n\nВыберите конференцию:",
        'hotel_info_title': "🏨 Информация об отеле\n\nВыберите конференцию:",
        'no_flights': "❌ Информация о рейсах для этой конференции не найдена.",
        'no_hotel': "❌ Информация об отеле для этой конференции не найдена.",
        'form_cancelled': "❌ Заполнение формы отменено.",
        'back_to_travel': "◀️ Назад в TRAVEL",

        # Визовая поддержка
        'visa_support_title': "🛂 Визовая поддержка\n\nВыберите ваш статус:",
        'visa_have': "✅ У меня есть виза",
        'visa_not_have': "❌ У меня нет визы",
        'visa_special': "🔄 Особый случай",
        'visa_need_help': "✅ Да, нужна помощь с билетами/отелем",
        'visa_bought_myself': "🛒 Я купил всё сам",

        # Паспортные данные
        'passport_consent': "📋 **Согласие на хранение данных**\n\nРазрешаете ли вы хранить ваши паспортные данные для будущих бронирований в течение 6 месяцев?",
        'use_saved_data': "✅ Использовать сохраненные данные",
        'enter_new_data': "✏️ Ввести новые данные",
        'saved_passport_found': "📋 **Найдены сохраненные паспортные данные**\n\nИмя: {first_name} {last_name}\nПаспорт: {passport_number}\n\nИспользовать сохраненные данные?",

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
        'baggage_yes': "✅ Да, нужен багаж",
        'baggage_no': "❌ Нет, только ручная кладь",
        'hotel_question': "🏨 **Нужен ли отель?**\n\nБудет ли вам нужен отель для этой конференции?\n\n*Примечание:* Компания не возмещает расходы за самостоятельно забронированные отели или брони для сопровождающих лиц.",
        'hotel_needed_yes': "✅ Да, нужен отель",
        'hotel_needed_no': "❌ Нет, отель не нужен",

        # Выбор рейса
        'flight_choice': "✈️ **Выберите ваш рейс**\n\nПожалуйста, выберите наиболее удобный рейс:",
        'flight_no_suitable': "❌ Ни один из рейсов не подходит. Свяжитесь со мной",
        'select_conference_for_flight': "✈️ Информация о рейсах\n\nВыберите конференцию:",
        'select_conference_for_hotel': "🏨 Информация об отеле\n\nВыберите конференцию:",

        # Информация о рейсах и отелях
        'no_flights_found': "❌ Информация о рейсах для этой конференции не найдена.",
        'no_hotel_found': "❌ Информация об отеле для этой конференции не найдена.",
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
        'per_diem_consent': "📝 **Подтверждение**\n\nЯ даю согласие на обработку персональных данных",
        'per_diem_success': "✅ **Заявка на суточные отправлена!**\n\nБлагодарим за запрос. Наша финансовая команда обработает ваши платежные данные и свяжется с вами при необходимости.\n\nПо вопросам обращайтесь к travel-команде через бота.",

        # Вопросы
        'question_to_manager': "❓ Вопрос travel-менеджеру\n\nНапишите ваш вопрос (максимум 500 символов):",
        'question_sent': "✅ **Вопрос отправлен!**\n\nБлагодарим за вопрос. Наша travel-команда свяжется с вами в ближайшее время.",
        'question_too_long': "❌ Вопрос слишком длинный. Максимум 500 символов.",

        # Мои заявки
        'my_requests_title': "📋 *Ваши travel-заявки*\n\n",
        'visa_status_pending': "🛂 *Визовая поддержка:* ⏳ В обработке\n   Отправлено: {submitted}\n\n",
        'visa_status_no': "🛂 *Визовая поддержка:* 📝 Нет заявок\n\n",
        'flight_status_pending': "✈️ *Заявка на билет:* ⏳ В обработке\n   Отправлено: {submitted}\n\n",
        'flight_status_no': "✈️ *Заявка на билет:* 📝 Нет заявок\n\n",
        'per_diem_status_pending': "💰 *Суточные:* ⏳ В обработке\n   Отправлено: {submitted}\n\n",
        'per_diem_status_no': "💰 *Суточные:* 📝 Нет заявок\n\n",
        'status_footer': "_Вы получите уведомления при изменении статуса._",
        'check_again': "🔄 Проверить снова",
        'new_request': "📝 Новая заявка",
        'error_loading_requests': "❌ Ошибка загрузки ваших заявок.",

        # Успешная отправка формы
        'form_complete': "✅ **Заявка успешно отправлена!**\n\n📋 *Следующие шаги:*\n• Следите за уведомлениями в Telegram\n• Если нужна виза: начните сбор документов\n• Проверяйте email для подтверждения билетов\n• Нажмите 'Мои заявки' для проверки статуса\n\n⏰ *Ожидаемые сроки:*\n• Авиабилеты: 1-3 рабочих дня\n• Визовая поддержка: 5-10 рабочих дней\n• Бронирование отеля: 2-4 рабочих дня\n\n_Наша travel-команда скоро свяжется с вами._",

        # Ошибки
        'error_no_username': "❌ Пожалуйста, установите username в Telegram.",
        'error_no_conferences': "❌ Для вашего аккаунта не найдено конференций.",
        'error_wrong_time_format': "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30)",
        'error_wrong_date_format': "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ",
        'error_invalid_card': "❌ Неверный номер карты. Попробуйте снова:",
        'error_invalid_address': "❌ Адрес слишком короткий. Попробуйте снова:",
        'error_saving_request': "❌ Ошибка сохранения заявки. Пожалуйста, попробуйте позже.",

        # Кнопки
        'confirm_data_storage': "✅ Подтвердить хранение данных",
        'dont_store': "❌ Не хранить",

        # Дополнительные фразы
        'special_case_processing': "🔄 Обработка особого случая...",
        'thanks_for_info': "✅ Спасибо за информацию!\n\nОтлично, что вы организовали поездку самостоятельно.\nЕсли у вас есть вопросы, обратитесь к travel-команде.",
        'hotel_booking_note': "🏨 **Бронирование отеля**\n\nЕсли вам нужен отель, пожалуйста, заполните форму заявки на авиабилет. Там будет вопрос о необходимости отеля.\n\nПосле отправки заявки наш travel-менеджер свяжется с вами для уточнения деталей.",

    },
    'en': {
        # Navigation
        'back': "◀️ Back",
        'main_menu': "🏠 Main Menu",
        'cancel': "❌ Cancel",
        'submit': "✅ Submit",
        'skip': "⏭️ Skip",
        'confirm': "✅ Confirm",
        'yes': "✅ Yes",
        'no': "❌ No",

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
        'banner_success': "✅ Banner request submitted!\n\nThank you for your response! Our team has received your request. Follow notifications for updates.",


        # EVENT section
        'event_title': "🎪 EVENT Section",
        'event_ticket': "🎫 Conference Ticket",
        'event_booth': "ℹ️ About Booth",
        'event_info': "ℹ️ About Conference",
        'event_question': "❓ Question",

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
        'error_not_whitelisted': "⛔ Sorry, you do not have access to this conference bot.\n\nPlease contact your manager.",
        'error_validation': "❌ Please enter valid data.",

        # Profile
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
        'help_text': "🆘 Bot help:\n\n• To return to main menu press the button below\n• For access issues contact administrator\n• Technical problems: support@conference.com",
        'help': "❓ Help",
        'my_profile': "👤 Profile",

        # ========== TRAVEL SECTION ==========
        # Main menu
        'travel_welcome': "✈️ TRAVEL SECTION\n\nChoose an option:",
        'travel_title': "✈️ TRAVEL",
        'travel_flight_request': "✈️ Flight Request",
        'travel_visa_support': "🛂 Visa Support",
        'travel_flight_info': "ℹ️ Flight Info",
        'travel_hotel': "🏨 Hotel",
        'travel_per_diem': "💰 Daily allowance",
        'travel_my_requests': "📋 My requests",
        'travel_question': "❓ Question",
        'travel_back_to_menu': "◀️ Back to TRAVEL",

        # Visa support
        'visa_support_title': "🛂 Visa Support\n\nChoose your status:",
        'visa_have': "✅ I have a visa",
        'visa_not_have': "❌ I don't have a visa",
        'visa_special': "🔄 Special case",
        'visa_need_help': "✅ Yes, need help with tickets/hotel",
        'visa_bought_myself': "🛒 I bought everything myself",

        # Passport data
        'passport_consent': "📋 **Data Storage Consent**\n\nDo you allow us to store your passport data for future bookings within 6 months?",
        'use_saved_data': "✅ Use saved data",
        'enter_new_data': "✏️ Enter new data",
        'saved_passport_found': "📋 **Saved passport data found**\n\nName: {first_name} {last_name}\nPassport: {passport_number}\n\nUse saved data?",

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
        'baggage_yes': "✅ Yes, need baggage",
        'baggage_no': "❌ No, only carry-on",
        'hotel_question': "🏨 **Hotel needed?**\n\nWill you need a hotel for this conference?\n\n*Note:* Company does not reimburse independent bookings or +1 accompanying persons.",
        'hotel_needed_yes': "✅ Yes, need hotel",
        'hotel_needed_no': "❌ No, don't need hotel",

        # Flight selection
        'flight_choice': "✈️ **Choose your flight**\n\nPlease select the most convenient flight:",
        'flight_no_suitable': "❌ None of the flights are suitable. Contact me",
        'select_conference_for_flight': "✈️ Flight Information\n\nSelect the conference:",
        'select_conference_for_hotel': "🏨 Hotel Information\n\nSelect the conference:",

        # Flight and hotel info
        'no_flights_found': "❌ No flight information found for this conference.",
        'no_hotel_found': "❌ Hotel information not found for this conference.",
        'flight_info_template': "*Flight {fl_num}*\n\nFlight number: {flight_number}\nBooking number: *{book_number}*\n\n📍 *Route*\n{departure_from} → {arrival_city}\n\n🏷 *Date & Time*\nDate: {departure_date}\nDeparture: {departure_time}\nArrival: {arrival_time}\n\n🧳 *Luggage*\nCarry-on: {carry_luggage} kg\nChecked: {luggage} kg\n\n🛩️ Airline: *{airline}*",
        'hotel_info_template': "🏨 *{hotel_name}*\n\n📍 _{hotel_address}_\n\n{hotel_link}\n\nBooked for conference: *{conference}*",
        'registration_info': "📌 *Check-in*\n\nYou can check in for your flight *24 hours before departure* using this link:\n",
        'registration_airline': "*{airline}*: {checkin_url}\n",
        'final_text': "\n_Wish you a great flight!_ 🔥",

        # Daily allowance
        'per_diem_question': "💰 Daily allowance\n\nWhere would you like to receive the Daily allowance?",
        'per_diem_card': "💳 Bank card",
        'per_diem_crypto': "🪙 Crypto wallet",
        'network_trc20': "TRC20 (USDT)",
        'network_erc20': "ERC20 (USDT)",
        'network_bep20': "BEP20 (USDT/BUSD)",
        'enter_card_number': "💳 Enter your card number:",
        'enter_crypto_address': "🪙 Enter your crypto wallet address ({network}):",
        'per_diem_consent': "📝 **Confirmation**\n\nI consent to the processing of personal data",
        'per_diem_success': "✅ **Daily allowance request submitted!**\n\nThank you for your request. Our finance team will process your payment details and contact you if additional information is needed.\n\nFor questions, contact our travel team via bot.",

        # Questions
        'question_to_manager': "❓ Question to Travel Manager\n\nPlease write your question (max 500 characters):",
        'question_sent': "✅ **Question sent!**\n\nThank you for your question. Our travel team will contact you soon.",
        'question_too_long': "❌ Question is too long. Maximum 500 characters.",

        # My requests
        'my_requests_title': "📋 *Your Travel Requests*\n\n",
        'visa_status_pending': "🛂 *Visa Support:* ⏳ Processing\n   Submitted: {submitted}\n\n",
        'visa_status_no': "🛂 *Visa Support:* 📝 No requests yet\n\n",
        'flight_status_pending': "✈️ *Flight Request:* ⏳ Processing\n   Submitted: {submitted}\n\n",
        'flight_status_no': "✈️ *Flight Request:* 📝 No requests yet\n\n",
        'per_diem_status_pending': "💰 *Daily allowance:* ⏳ Processing\n   Submitted: {submitted}\n\n",
        'per_diem_status_no': "💰 *Daily allowance:* 📝 No requests yet\n\n",
        'status_footer': "_You will receive notifications when status changes._",
        'check_again': "🔄 Check again",
        'new_request': "📝 New request",
        'error_loading_requests': "❌ Error loading your requests.",

        # Form success
        'form_complete': "✅ **Request submitted successfully!**\n\n📋 *Next steps:*\n• Check Telegram notifications for updates\n• If visa needed: start document collection\n• Monitor email for ticket confirmations\n• Click 'My Requests' to check status\n\n⏰ *Expected timeline:*\n• Flight tickets: 1-3 business days\n• Visa processing: 5-10 business days\n• Hotel booking: 2-4 business days\n\n_Our travel team will contact you soon._",

        # Errors
        'error_no_username': "❌ Please set your Telegram username first.",
        'error_no_conferences': "❌ No conferences found for your account.",
        'error_wrong_time_format': "❌ Wrong time format. Use HH:MM (e.g., 14:30)",
        'error_wrong_date_format': "❌ Wrong date format. Use DD.MM.YYYY",
        'error_invalid_card': "❌ Invalid card number. Try again:",
        'error_invalid_address': "❌ Address too short. Try again:",
        'error_saving_request': "❌ Error saving request. Please try again later.",

        # Buttons
        'confirm_data_storage': "✅ Confirm data storage",
        'dont_store': "❌ Don't store",

        # Additional phrases
        'special_case_processing': "🔄 Processing special case...",
        'thanks_for_info': "✅ Thank you for the information!\n\nGreat that you've organized your travel independently.\nIf you have questions, contact travel team.",
        'hotel_booking_note': "🏨 **Hotel Booking**\n\nIf you need a hotel, please fill out the flight request form. There will be a question about hotel needs.\n\nAfter submitting the request, our travel manager will contact you to clarify the details.",
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