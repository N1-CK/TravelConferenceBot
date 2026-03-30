# locales.py
from typing import Dict, Any


TEXTS = {
    'ru': {
        'dashboard': 'Дашборд',
        'broadcast': 'Рассылка',
        'users': 'Пользователи',
        'conferences': 'Конференции',
        'logout': 'Выход',
        'role_admin': 'Администратор',
        'role_user': 'Пользователь',
        'role_manager': 'Менеджер',
        'user_management': 'Управление пользователями',
        'username': 'Логин',
        'full_name': 'Полное имя',
        'role': 'Роль',
        'permissions': 'Права',
        'last_active': 'Последняя активность',
        'status': 'Статус',
        'actions': 'Действия',
        'active': 'Активен',
        'blocked': 'Заблокирован',
        'add_user': 'Добавить пользователя',
        'edit_user': 'Редактировать пользователя',
        'password': 'Пароль',
        'leave_empty': 'оставьте пустым, чтобы не менять',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'confirm_delete': 'Вы уверены, что хотите удалить этого пользователя?'
    },
    'en': {
        'dashboard': 'Dashboard',
        'broadcast': 'Broadcast',
        'users': 'Users',
        'conferences': 'Conferences',
        'logout': 'Logout',
        'role_admin': 'Administrator',
        'role_user': 'User',
        'role_manager': 'Manager',
        'user_management': 'User Management',
        'username': 'Username',
        'full_name': 'Full Name',
        'role': 'Role',
        'permissions': 'Permissions',
        'last_active': 'Last Active',
        'status': 'Status',
        'actions': 'Actions',
        'active': 'Active',
        'blocked': 'Blocked',
        'add_user': 'Add User',
        'edit_user': 'Edit User',
        'password': 'Password',
        'leave_empty': 'leave empty to keep current',
        'save': 'Save',
        'cancel': 'Cancel',
        'confirm_delete': 'Are you sure you want to delete this user?'
    }
}

def get_text(key, lang='ru'):
    """Получить текст на нужном языке"""
    return TEXTS.get(lang, TEXTS['ru']).get(key, key)

class I18n:
    """Класс для интернационализации"""

    _translations = {
        'ru': {
            # Навигация
            'dashboard': 'Дашборд',
            'broadcast': 'Рассылка',
            'conferences': 'Конференции',
            'users': 'Пользователи',
            'logout': 'Выход',
            'admin_panel': 'Панель администратора',

            # Статистика
            'total_users': 'Всего пользователей',
            'active_today': 'Активных сегодня',
            'active_conferences': 'Активных конференций',
            'total_broadcasts': 'Всего рассылок',
            'top_companies': 'Топ компаний',
            'recent_broadcasts': 'Последние рассылки',
            'quick_actions': 'Быстрые действия',
            'broadcast_all': 'Рассылка всем',
            'broadcast_by_company': 'Рассылка по компаниям',
            'manage_conferences': 'Управление конференциями',
            'active_users': 'Активные пользователи',
            'recently_active': 'Недавно активные',

            # Рассылка
            'mass_broadcast': 'Массовая рассылка',
            'simple_broadcast': 'Простая рассылка',
            'advanced_broadcast': 'Расширенная рассылка',
            'recipient_type': 'Тип получателей',
            'all_users': 'Всем пользователям',
            'by_companies': 'По компаниям',
            'specific_users': 'Конкретным пользователям',
            'by_conferences': 'По конференциям',
            'select_companies': 'Выберите компании',
            'select_users': 'Выберите пользователей',
            'select_conferences': 'Выберите конференции',
            'message_text': 'Текст сообщения',
            'attach_files': 'Прикрепить файлы',
            'preview': 'Предпросмотр',
            'send': 'Отправить',
            'cancel': 'Отмена',
            'recipients': 'получателей',

            # Пользователи
            'user_management': 'Управление пользователями',
            'add_user': 'Добавить пользователя',
            'edit_user': 'Редактировать пользователя',
            'username': 'Имя пользователя',
            'password': 'Пароль',
            'full_name': 'Полное имя',
            'company': 'Компания',
            'position': 'Должность',
            'role': 'Роль',
            'language': 'Язык',
            'active': 'Активен',
            'last_active': 'Последняя активность',
            'requests': 'Заявки',
            'actions': 'Действия',
            'view': 'Просмотр',
            'message': 'Сообщение',
            'block': 'Заблокировать',
            'export': 'Экспорт',

            # Роли
            'role_admin': 'Администратор',
            'role_pr': 'PR-менеджер',
            'role_event': 'Event-менеджер',
            'role_travel': 'Travel-менеджер',
            'role_user': 'Пользователь',

            # Конференции
            'conference_management': 'Управление конференциями',
            'conference_name': 'Название конференции',
            'city': 'Город',
            'dates': 'Даты',
            'participants': 'Участников',
            'status': 'Статус',
            'active': 'Активна',
            'upcoming': 'Предстоит',
            'ended': 'Завершена',

            # Сообщения
            'select_at_least_one': 'Выберите хотя бы один пункт',
            'message_too_long': 'Сообщение слишком длинное',
            'no_recipients': 'Нет получателей',
            'broadcast_sent': 'Рассылка отправлена',
            'success': 'Успешно',
            'failed': 'Ошибок',
            'files': 'Файлов',
            'confirm_broadcast': 'Отправить рассылку?',

            # Формы
            'enter_username': 'Введите имя пользователя',
            'enter_password': 'Введите пароль',
            'enter_full_name': 'Введите полное имя',
            'select_role': 'Выберите роль',
            'save': 'Сохранить',
            'delete': 'Удалить',
            'close': 'Закрыть',

            # Ошибки
            'error': 'Ошибка',
            'not_found': 'Не найдено',
            'access_denied': 'Доступ запрещен',
            'invalid_credentials': 'Неверные учетные данные',
        },

        'en': {
            # Navigation
            'dashboard': 'Dashboard',
            'broadcast': 'Broadcast',
            'conferences': 'Conferences',
            'users': 'Users',
            'logout': 'Logout',
            'admin_panel': 'Admin Panel',

            # Statistics
            'total_users': 'Total Users',
            'active_today': 'Active Today',
            'active_conferences': 'Active Conferences',
            'total_broadcasts': 'Total Broadcasts',
            'top_companies': 'Top Companies',
            'recent_broadcasts': 'Recent Broadcasts',
            'quick_actions': 'Quick Actions',
            'broadcast_all': 'Broadcast to All',
            'broadcast_by_company': 'Broadcast by Company',
            'manage_conferences': 'Manage Conferences',
            'active_users': 'Active Users',
            'recently_active': 'Recently Active',

            # Broadcast
            'mass_broadcast': 'Mass Broadcast',
            'simple_broadcast': 'Simple Broadcast',
            'advanced_broadcast': 'Advanced Broadcast',
            'recipient_type': 'Recipient Type',
            'all_users': 'All Users',
            'by_companies': 'By Companies',
            'specific_users': 'Specific Users',
            'by_conferences': 'By Conferences',
            'select_companies': 'Select Companies',
            'select_users': 'Select Users',
            'select_conferences': 'Select Conferences',
            'message_text': 'Message Text',
            'attach_files': 'Attach Files',
            'preview': 'Preview',
            'send': 'Send',
            'cancel': 'Cancel',
            'recipients': 'recipients',

            # Users
            'user_management': 'User Management',
            'add_user': 'Add User',
            'edit_user': 'Edit User',
            'username': 'Username',
            'password': 'Password',
            'full_name': 'Full Name',
            'company': 'Company',
            'position': 'Position',
            'role': 'Role',
            'language': 'Language',
            'active': 'Active',
            'last_active': 'Last Active',
            'requests': 'Requests',
            'actions': 'Actions',
            'view': 'View',
            'message': 'Message',
            'block': 'Block',
            'export': 'Export',

            # Roles
            'role_admin': 'Administrator',
            'role_pr': 'PR Manager',
            'role_event': 'Event Manager',
            'role_travel': 'Travel Manager',
            'role_user': 'User',

            # Conferences
            'conference_management': 'Conference Management',
            'conference_name': 'Conference Name',
            'city': 'City',
            'dates': 'Dates',
            'participants': 'Participants',
            'status': 'Status',
            'active': 'Active',
            'upcoming': 'Upcoming',
            'ended': 'Ended',

            # Messages
            'select_at_least_one': 'Select at least one item',
            'message_too_long': 'Message is too long',
            'no_recipients': 'No recipients',
            'broadcast_sent': 'Broadcast sent',
            'success': 'Success',
            'failed': 'Failed',
            'files': 'Files',
            'confirm_broadcast': 'Send broadcast?',

            # Forms
            'enter_username': 'Enter username',
            'enter_password': 'Enter password',
            'enter_full_name': 'Enter full name',
            'select_role': 'Select role',
            'save': 'Save',
            'delete': 'Delete',
            'close': 'Close',

            # Errors
            'error': 'Error',
            'not_found': 'Not found',
            'access_denied': 'Access denied',
            'invalid_credentials': 'Invalid credentials',
        }
    }

    def __init__(self, language='ru'):
        self.language = language

    def t(self, key: str) -> str:
        """Получить перевод по ключу"""
        return self._translations.get(self.language, {}).get(key, key)

    def set_language(self, language: str):
        """Установить язык"""
        if language in self._translations:
            self.language = language


# Глобальный экземпляр
i18n = I18n()
