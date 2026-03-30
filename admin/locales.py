# locales.py
TEXTS = {
    'ru': {
        'dashboard': 'Дашборд',
        'broadcast': 'Рассылка',
        'pr_panel': 'PR-панель',
        'event_panel': 'Event-панель',
        'travel_panel': 'Travel-панель',
        'user_chats': 'Чаты с пользователями',
        'manage_managers': 'Управление менеджерами',
        'change_password': 'Сменить пароль',
        'logout': 'Выход',

        'role_admin': 'Администратор',
        'role_manager': 'Менеджер',
        'role_user': 'Пользователь',

        'login_time': 'Вход:',
        'password_changed_success': 'Пароль успешно изменен',
        'invalid_current_password': 'Неверный текущий пароль',
        'error': 'Произошла ошибка',

        'current_password': 'Текущий пароль',
        'new_password': 'Новый пароль',
        'confirm_password': 'Подтверждение пароля',
        'min_chars': 'Минимум 6 символов',
        'passwords_not_match': 'Пароли не совпадают',
        'save': 'Сохранить',
        'back': 'Назад'
    },
    'en': {
        'dashboard': 'Dashboard',
        'broadcast': 'Broadcast',
        'pr_panel': 'PR Panel',
        'event_panel': 'Event Panel',
        'travel_panel': 'Travel Panel',
        'user_chats': 'User Chats',
        'manage_managers': 'Manage Managers',
        'change_password': 'Change Password',
        'logout': 'Logout',

        'role_admin': 'Administrator',
        'role_manager': 'Manager',
        'role_user': 'User',

        'login_time': 'Login:',
        'password_changed_success': 'Password changed successfully',
        'invalid_current_password': 'Invalid current password',
        'error': 'An error occurred',

        'current_password': 'Current Password',
        'new_password': 'New Password',
        'confirm_password': 'Confirm Password',
        'min_chars': 'Minimum 6 characters',
        'passwords_not_match': 'Passwords do not match',
        'save': 'Save',
        'back': 'Back'
    }
}


def get_text(key, lang='ru'):
    """Получить текст на нужном языке"""
    return TEXTS.get(lang, TEXTS['ru']).get(key, key)