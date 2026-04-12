# locales.py
import json
import os
from typing import Dict, Any

# Полные тексты для всех языков
TEXTS = {
    'ru': {
        # Навигация
        'dashboard': '📊 Дашборд',
        'broadcast': '📨 Рассылка',
        'pr_panel': '📢 PR-панель',
        'event_panel': '🎪 Event-панель',
        'travel_panel': '✈️ Travel-панель',
        'user_chats': '💬 Чаты с пользователями',
        'manage_managers': '👥 Управление менеджерами',
        'user_groups': '👥 Группы пользователей',
        'change_password': '🔑 Сменить пароль',
        'logout': '🚪 Выход',
        'users': '👥 Пользователи',
        'conferences': '📅 Конференции',

        # Роли
        'role_admin': 'Администратор',
        'role_manager': 'Менеджер',
        'role_user': 'Пользователь',
        'role_admin_desc': 'Полный доступ ко всем функциям',
        'role_manager_desc': 'Ограниченный доступ',
        'role_user_desc': 'Обычный пользователь',

        # PR
        'pr_banner': '📸 Заказать баннер',
        'pr_business_cards': '💳 Заказать визитки',
        'pr_dinner': '🍽️ Бизнес-ужин',
        'pr_conference_bot': '🤖 Бот конференции',
        'pr_conference_rules': '📋 Правила конференции',
        'question_button': '❓ Задать вопрос',

        # EVENT
        'event_ticket': '🎫 Заказать билет',
        'event_booth': '🏢 Заказать стенд',
        'event_info': 'ℹ️ Информация',

        # TRAVEL
        'travel_flight_request': '✈️ Заказать билеты',
        'travel_visa_support': '🛂 Визовая поддержка',
        'travel_flight_info': '📋 Информация о рейсах',
        'travel_hotel': '🏨 Бронирование отеля',
        'travel_per_diem': '💰 Суточные',
        'travel_my_requests': '📋 Мои заявки',

        # Общие
        'back': '◀️ Назад',
        'cancel': '❌ Отмена',
        'save': '💾 Сохранить',
        'delete': '🗑️ Удалить',
        'edit': '✏️ Редактировать',
        'add': '➕ Добавить',
        'search': '🔍 Поиск',
        'filter': '🔎 Фильтр',
        'export': '📤 Экспорт',
        'import': '📥 Импорт',
        'confirm': '✅ Подтвердить',
        'skip': '⏭️ Пропустить',
        'next': '⏩ Далее',
        'previous': '⏪ Назад',
        'close': '❌ Закрыть',
        'refresh': '🔄 Обновить',

        # Статусы
        'status_pending': '⏳ В ожидании',
        'status_approved': '✅ Одобрено',
        'status_rejected': '❌ Отклонено',
        'status_active': '🟢 Активен',
        'status_inactive': '⚫ Неактивен',
        'status_blocked': '🔴 Заблокирован',
        'status_online': '🟢 В сети',
        'status_offline': '⚪ Не в сети',

        # Сообщения
        'welcome': 'Добро пожаловать',
        'login_required': 'Требуется вход в систему',
        'access_denied': 'Доступ запрещен',
        'operation_success': 'Операция выполнена успешно',
        'operation_failed': 'Ошибка выполнения операции',
        'confirm_delete': 'Вы уверены, что хотите удалить?',
        'no_data': 'Нет данных для отображения',
        'loading': 'Загрузка...',
        'error_occurred': 'Произошла ошибка',

        # Формы
        'username': 'Имя пользователя',
        'password': 'Пароль',
        'full_name': 'Полное имя',
        'company': 'Компания',
        'position': 'Должность',
        'email': 'Email',
        'phone': 'Телефон',
        'language': 'Язык',
        'description': 'Описание',
        'created_at': 'Дата создания',
        'updated_at': 'Дата обновления',
        'last_active': 'Последняя активность',

        # Права доступа
        'permissions': 'Права доступа',
        'can_manage_users': 'Управление пользователями',
        'can_broadcast': 'Массовые рассылки',
        'can_view_stats': 'Просмотр статистики',
        'can_manage_conferences': 'Управление конференциями',

        # Администрирование
        'admin_panel': 'Панель администратора',
        'user_management': 'Управление пользователями',
        'group_management': 'Управление группами',
        'system_settings': 'Настройки системы',
        'logs': 'Журнал событий',
        'backup': 'Резервное копирование',

        # Группы
        'group_name': 'Название группы',
        'group_color': 'Цвет группы',
        'group_members': 'Участники группы',
        'add_group': 'Добавить группу',
        'edit_group': 'Редактировать группу',
        'delete_group': 'Удалить группу',

        # Конференции
        'conference_name': 'Название конференции',
        'conference_city': 'Город',
        'conference_dates': 'Даты проведения',
        'conference_participants': 'Участники',
        'add_conference': 'Добавить конференцию',
        'edit_conference': 'Редактировать конференцию',
        'delete_conference': 'Удалить конференцию',

        # Чаты
        'chats': 'Чаты',
        'send_message': 'Отправить сообщение',
        'type_message': 'Введите сообщение...',
        'attach_file': 'Прикрепить файл',
        'no_messages': 'Нет сообщений',

        # Статистика
        'total_users': 'Всего пользователей',
        'active_today': 'Активных сегодня',
        'total_broadcasts': 'Всего рассылок',
        'total_requests': 'Всего заявок',
        'pending_requests': 'Заявок на рассмотрении',

        # Дополнительно
        'my_profile': '👤 Мой профиль',
        'help': '❓ Помощь',
        'main_menu': '🏠 Главное меню',
        'change_language': '🌐 Сменить язык',

        # Travel
        'travel_visa_status': 'Статус визы',
        'travel_passport_data': 'Паспортные данные',
        'travel_city_from': 'Город вылета',
        'travel_city_to': 'Город прибытия',
        'travel_baggage': 'Багаж',
        'travel_preferences': 'Предпочтения',

        # PR
        'pr_photo_required': 'Требуется фото',
        'pr_brand_style': 'Бренд-стиль',
        'pr_contacts': 'Контакты',

        # Event
        'event_certificate': 'Справка-вызов',
        'event_company_legal': 'Юридическое название',
        'event_addressee': 'Кому',
        'event_dates': 'Даты',

        # Валидация
        'field_required': 'Это поле обязательно',
        'invalid_email': 'Неверный формат email',
        'password_min_length': 'Пароль должен содержать минимум 6 символов',
        'passwords_not_match': 'Пароли не совпадают',
        'invalid_username': 'Неверное имя пользователя',

        # Кнопки действий
        'btn_add': '➕ Добавить',
        'btn_edit': '✏️ Редактировать',
        'btn_delete': '🗑️ Удалить',
        'btn_save': '💾 Сохранить',
        'btn_cancel': '❌ Отмена',
        'btn_back': '◀️ Назад',
        'btn_next': 'Далее ▶️',
        'btn_submit': '📤 Отправить',
        'btn_upload': '📎 Загрузить',
        'btn_download': '📥 Скачать',
        'btn_preview': '👁️ Предпросмотр',

        # Заголовки страниц
        'title_login': 'Вход в систему',
        'title_dashboard': 'Панель управления',
        'title_users': 'Пользователи',
        'title_conferences': 'Конференции',
        'title_broadcast': 'Массовая рассылка',
        'title_pr_panel': 'PR-панель',
        'title_event_panel': 'Event-панель',
        'title_travel_panel': 'Travel-панель',
        'title_user_chats': 'Чаты с пользователями',
        'title_manage_managers': 'Управление менеджерами',
        'title_user_groups': 'Группы пользователей',
        'title_change_password': 'Смена пароля',

        # Сообщения об успехе/ошибке
        'success_login': 'Добро пожаловать, {}!',
        'success_logout': 'Вы вышли из системы',
        'success_password_change': 'Пароль успешно изменен',
        'success_user_add': 'Пользователь добавлен',
        'success_user_edit': 'Пользователь обновлен',
        'success_user_delete': 'Пользователь удален',
        'success_group_add': 'Группа создана',
        'success_group_edit': 'Группа обновлена',
        'success_group_delete': 'Группа удалена',
        'success_broadcast': 'Рассылка отправлена: {} успешно, {} ошибок',

        'error_login': 'Неверное имя пользователя или пароль',
        'error_password_mismatch': 'Текущий пароль неверен',
        'error_user_exists': 'Пользователь уже существует',
        'error_group_exists': 'Группа уже существует',
        'error_no_data': 'Нет данных для обработки',

        # Подсказки
        'hint_select_users': 'Выберите пользователей для рассылки',
        'hint_select_companies': 'Выберите компании',
        'hint_select_conferences': 'Выберите конференции',
        'hint_attach_files': 'Можно прикрепить несколько файлов',
        'hint_message_limit': 'Максимум 4000 символов',
    },
    'en': {
        # Navigation
        'dashboard': '📊 Dashboard',
        'broadcast': '📨 Broadcast',
        'pr_panel': '📢 PR Panel',
        'event_panel': '🎪 Event Panel',
        'travel_panel': '✈️ Travel Panel',
        'user_chats': '💬 User Chats',
        'manage_managers': '👥 Manage Managers',
        'user_groups': '👥 User Groups',
        'change_password': '🔑 Change Password',
        'logout': '🚪 Logout',
        'users': '👥 Users',
        'conferences': '📅 Conferences',

        # Roles
        'role_admin': 'Administrator',
        'role_manager': 'Manager',
        'role_user': 'User',
        'role_admin_desc': 'Full access to all features',
        'role_manager_desc': 'Limited access',
        'role_user_desc': 'Regular user',

        # PR
        'pr_banner': '📸 Order Banner',
        'pr_business_cards': '💳 Order Business Cards',
        'pr_dinner': '🍽️ Business Dinner',
        'pr_conference_bot': '🤖 Conference Bot',
        'pr_conference_rules': '📋 Conference Rules',
        'question_button': '❓ Ask Question',

        # EVENT
        'event_ticket': '🎫 Order Ticket',
        'event_booth': '🏢 Order Booth',
        'event_info': 'ℹ️ Information',

        # TRAVEL
        'travel_flight_request': '✈️ Book Tickets',
        'travel_visa_support': '🛂 Visa Support',
        'travel_flight_info': '📋 Flight Information',
        'travel_hotel': '🏨 Hotel Booking',
        'travel_per_diem': '💰 Per Diem',
        'travel_my_requests': '📋 My Requests',

        # General
        'back': '◀️ Back',
        'cancel': '❌ Cancel',
        'save': '💾 Save',
        'delete': '🗑️ Delete',
        'edit': '✏️ Edit',
        'add': '➕ Add',
        'search': '🔍 Search',
        'filter': '🔎 Filter',
        'export': '📤 Export',
        'import': '📥 Import',
        'confirm': '✅ Confirm',
        'skip': '⏭️ Skip',
        'next': '⏩ Next',
        'previous': '⏪ Previous',
        'close': '❌ Close',
        'refresh': '🔄 Refresh',

        # Statuses
        'status_pending': '⏳ Pending',
        'status_approved': '✅ Approved',
        'status_rejected': '❌ Rejected',
        'status_active': '🟢 Active',
        'status_inactive': '⚫ Inactive',
        'status_blocked': '🔴 Blocked',
        'status_online': '🟢 Online',
        'status_offline': '⚪ Offline',

        # Messages
        'welcome': 'Welcome',
        'login_required': 'Login required',
        'access_denied': 'Access denied',
        'operation_success': 'Operation successful',
        'operation_failed': 'Operation failed',
        'confirm_delete': 'Are you sure you want to delete?',
        'no_data': 'No data to display',
        'loading': 'Loading...',
        'error_occurred': 'An error occurred',

        # Forms
        'username': 'Username',
        'password': 'Password',
        'full_name': 'Full Name',
        'company': 'Company',
        'position': 'Position',
        'email': 'Email',
        'phone': 'Phone',
        'language': 'Language',
        'description': 'Description',
        'created_at': 'Created At',
        'updated_at': 'Updated At',
        'last_active': 'Last Active',

        # Permissions
        'permissions': 'Permissions',
        'can_manage_users': 'Manage Users',
        'can_broadcast': 'Broadcast',
        'can_view_stats': 'View Statistics',
        'can_manage_conferences': 'Manage Conferences',

        # Administration
        'admin_panel': 'Admin Panel',
        'user_management': 'User Management',
        'group_management': 'Group Management',
        'system_settings': 'System Settings',
        'logs': 'Logs',
        'backup': 'Backup',

        # Groups
        'group_name': 'Group Name',
        'group_color': 'Group Color',
        'group_members': 'Group Members',
        'add_group': 'Add Group',
        'edit_group': 'Edit Group',
        'delete_group': 'Delete Group',

        # Conferences
        'conference_name': 'Conference Name',
        'conference_city': 'City',
        'conference_dates': 'Dates',
        'conference_participants': 'Participants',
        'add_conference': 'Add Conference',
        'edit_conference': 'Edit Conference',
        'delete_conference': 'Delete Conference',

        # Chats
        'chats': 'Chats',
        'send_message': 'Send Message',
        'type_message': 'Type a message...',
        'attach_file': 'Attach File',
        'no_messages': 'No messages',

        # Statistics
        'total_users': 'Total Users',
        'active_today': 'Active Today',
        'total_broadcasts': 'Total Broadcasts',
        'total_requests': 'Total Requests',
        'pending_requests': 'Pending Requests',

        # Additional
        'my_profile': '👤 My Profile',
        'help': '❓ Help',
        'main_menu': '🏠 Main Menu',
        'change_language': '🌐 Change Language',

        # Travel
        'travel_visa_status': 'Visa Status',
        'travel_passport_data': 'Passport Data',
        'travel_city_from': 'Departure City',
        'travel_city_to': 'Arrival City',
        'travel_baggage': 'Baggage',
        'travel_preferences': 'Preferences',

        # PR
        'pr_photo_required': 'Photo Required',
        'pr_brand_style': 'Brand Style',
        'pr_contacts': 'Contacts',

        # Event
        'event_certificate': 'Invitation Letter',
        'event_company_legal': 'Legal Name',
        'event_addressee': 'Addressee',
        'event_dates': 'Dates',

        # Validation
        'field_required': 'This field is required',
        'invalid_email': 'Invalid email format',
        'password_min_length': 'Password must be at least 6 characters',
        'passwords_not_match': 'Passwords do not match',
        'invalid_username': 'Invalid username',

        # Action buttons
        'btn_add': '➕ Add',
        'btn_edit': '✏️ Edit',
        'btn_delete': '🗑️ Delete',
        'btn_save': '💾 Save',
        'btn_cancel': '❌ Cancel',
        'btn_back': '◀️ Back',
        'btn_next': 'Next ▶️',
        'btn_submit': '📤 Submit',
        'btn_upload': '📎 Upload',
        'btn_download': '📥 Download',
        'btn_preview': '👁️ Preview',

        # Page titles
        'title_login': 'Login',
        'title_dashboard': 'Dashboard',
        'title_users': 'Users',
        'title_conferences': 'Conferences',
        'title_broadcast': 'Mass Broadcast',
        'title_pr_panel': 'PR Panel',
        'title_event_panel': 'Event Panel',
        'title_travel_panel': 'Travel Panel',
        'title_user_chats': 'User Chats',
        'title_manage_managers': 'Manage Managers',
        'title_user_groups': 'User Groups',
        'title_change_password': 'Change Password',

        # Success/Error messages
        'success_login': 'Welcome, {}!',
        'success_logout': 'You have been logged out',
        'success_password_change': 'Password changed successfully',
        'success_user_add': 'User added',
        'success_user_edit': 'User updated',
        'success_user_delete': 'User deleted',
        'success_group_add': 'Group created',
        'success_group_edit': 'Group updated',
        'success_group_delete': 'Group deleted',
        'success_broadcast': 'Broadcast sent: {} successful, {} failed',

        'error_login': 'Invalid username or password',
        'error_password_mismatch': 'Current password is incorrect',
        'error_user_exists': 'User already exists',
        'error_group_exists': 'Group already exists',
        'error_no_data': 'No data to process',

        # Hints
        'hint_select_users': 'Select users for broadcast',
        'hint_select_companies': 'Select companies',
        'hint_select_conferences': 'Select conferences',
        'hint_attach_files': 'You can attach multiple files',
        'hint_message_limit': 'Maximum 4000 characters',
    }
}


def get_text(key: str, lang: str = 'ru') -> str:
    """Get localized text by key"""
    lang_dict = TEXTS.get(lang, TEXTS['ru'])
    return lang_dict.get(key, key)


def get_all_texts(lang: str = 'ru') -> Dict[str, str]:
    """Get all texts for a language"""
    return TEXTS.get(lang, TEXTS['ru']).copy()


class Localization:
    """Localization helper class"""

    def __init__(self, default_lang: str = 'ru'):
        self.default_lang = default_lang
        self._langs = TEXTS.keys()

    def get(self, key: str, lang: str = None) -> str:
        """Get localized text"""
        lang = lang or self.default_lang
        return get_text(key, lang)

    def get_all(self, lang: str = None) -> Dict[str, str]:
        """Get all texts for language"""
        lang = lang or self.default_lang
        return get_all_texts(lang)

    @property
    def available_languages(self) -> list:
        """Get list of available languages"""
        return list(self._langs)

    def format(self, key: str, *args, lang: str = None, **kwargs) -> str:
        """Get and format localized text"""
        text = self.get(key, lang)
        if args:
            return text.format(*args)
        if kwargs:
            return text.format(**kwargs)
        return text


# Global instance
loc = Localization('ru')