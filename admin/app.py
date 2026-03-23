# app.py - замените весь код после импортов на это:

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from functools import wraps
import asyncio
import os
from datetime import datetime, timedelta
import secrets
import hashlib
import asyncpg
from dotenv import load_dotenv
import io
import csv
from werkzeug.utils import secure_filename

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db

from locales import get_text

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp'

# ============================================
# КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: ОДИН EVENT LOOP
# ============================================

# Создаем один event loop для всего приложения
_loop = None
_db_initialized = False

def get_event_loop():
    """Получить или создать единственный event loop"""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop

def run_async(coro):
    """Выполнить асинхронную функцию в единственном event loop"""
    loop = get_event_loop()
    try:
        if loop.is_running():
            # Если loop уже запущен, создаем задачу
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        else:
            # Если loop не запущен, запускаем его
            return loop.run_until_complete(coro)
    except RuntimeError as e:
        if "cannot run" in str(e) or "closed" in str(e):
            # Пересоздаем loop
            global _loop
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            return _loop.run_until_complete(coro)
        raise


def init_db():
    """Инициализация БД"""
    global _db_initialized
    if not _db_initialized:
        try:
            run_async(db.create_pool())

            # КРИТИЧЕСКИ ВАЖНО: создаем таблицы для групп и функций
            run_async(db.create_groups_tables())

            # СОЗДАЕМ ТАБЛИЦЫ ДЛЯ МЕНЕДЖЕРОВ
            run_async(db.create_managers_tables())

            _db_initialized = True
            print("✅ Database connection initialized")
            print("✅ Groups and features tables created")
            print("✅ Managers tables created")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

# Инициализируем БД сразу при старте
init_db()

# Конфигурация
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = hashlib.sha256(os.getenv('ADMIN_PASSWORD', 'admin123').encode()).hexdigest()
DB_SCHEMA = os.getenv('DB_SCHEMA')


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

def role_required(allowed_roles=None, permissions=None):
    """Декоратор для проверки роли и прав"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                return redirect(url_for('login'))

            role = session.get('role', 'user')

            # Проверка роли
            if allowed_roles and role not in allowed_roles:
                flash('У вас нет доступа к этой странице', 'danger')
                return redirect(url_for('dashboard'))

            # Проверка конкретных прав (для user-ролей)
            if permissions:
                for perm in permissions:
                    if not session.get('permissions', {}).get(perm, False):
                        flash(f'У вас нет права "{perm}"', 'danger')
                        return redirect(url_for('dashboard'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ============================================
# ИНТЕГРАЦИЯ С TELEGRAM БОТОМ
# ============================================

class TelegramBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, chat_id, text, file=None):
        """Отправить сообщение через Telegram API"""
        import aiohttp
        import os

        async with aiohttp.ClientSession() as session:
            if file:
                # Отправка с файлом
                url = f"{self.api_url}/sendDocument"
                form_data = aiohttp.FormData()
                form_data.add_field('chat_id', str(chat_id))
                form_data.add_field('document', file,
                                    filename=os.path.basename(file),
                                    content_type='application/octet-stream')
                if text:
                    form_data.add_field('caption', text, content_type='text/plain')

                try:
                    async with session.post(url, data=form_data) as resp:
                        result = await resp.json()
                        return result.get('ok', False)
                except Exception as e:
                    print(f"Error sending document: {e}")
                    return False
            else:
                # Отправка только текста
                url = f"{self.api_url}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'HTML'
                }

                try:
                    async with session.post(url, json=payload) as resp:
                        result = await resp.json()
                        return result.get('ok', False)
                except Exception as e:
                    print(f"Error sending message: {e}")
                    return False

    async def broadcast_to_users(self, users, message, files=None):
        """Массовая рассылка пользователям с файлами"""
        results = {'success': 0, 'failed': 0}
        file_count = len(files) if files else 0

        for user in users:
            user_id = user.get('user_id')
            if not user_id:
                results['failed'] += 1
                continue

            success = False
            if files and len(files) > 0:
                # Отправляем первый файл с подписью
                success = await self.send_message(user_id, message, files[0])
                # Отправляем остальные файлы без подписи
                for file in files[1:]:
                    await self.send_message(user_id, None, file)
            else:
                success = await self.send_message(user_id, message)

            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

            # Небольшая задержка чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.05)

        results['file_count'] = file_count
        return results


# Инициализация Telegram бота
bot = TelegramBot(os.getenv('TG_BOT_TOKEN', ''))

# ============================================
# МАРШРУТЫ
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа для менеджеров"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        manager = run_async(db.verify_manager(username, password))

        if manager:
            session['logged_in'] = True
            session['username'] = manager['username']
            session['manager_id'] = manager['id']
            session['full_name'] = manager['full_name']
            session['role'] = manager['role']
            session['groups'] = manager['group_names']  # ['pr', 'event', 'travel']
            session['login_time'] = datetime.now().isoformat()

            flash(f'Добро пожаловать, {manager["full_name"] or manager["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    """Главная панель - показывает только доступные разделы"""
    try:
        groups = session.get('groups', [])
        stats = run_async(db.get_stats())
        broadcasts = run_async(db.get_recent_broadcasts(5))
        conferences = run_async(db.get_conferences_list())
        active_conferences = conferences[:5] if conferences else []
        users = run_async(db.get_all_users_with_details())
        recent_users = sorted(users,
                              key=lambda x: x.get('last_active') or datetime.min,
                              reverse=True)[:5]

        return render_template('dashboard.html',
                               stats=stats,
                               groups=groups,
                               broadcasts=broadcasts,
                               active_conferences=active_conferences,
                               recent_users=recent_users,
                               username=session.get('username'),
                               full_name=session.get('full_name'))
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash('Ошибка загрузки данных', 'danger')
        # В случае ошибки передаем пустые значения для всех переменных
        return render_template('dashboard.html',
                               stats={'total_users': 0, 'active_today': 0, 'companies_stats': [],
                                      'banner_requests': 0, 'visa_requests': 0, 'active_conferences': 0,
                                      'total_broadcasts': 0},
                               groups=[],
                               broadcasts=[],
                               active_conferences=[],
                               recent_users=[],
                               username=session.get('username'),
                               full_name=session.get('full_name'))

@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    """Страница рассылки"""
    companies = run_async(db.get_companies_list())
    conferences = run_async(db.get_conferences_list())
    users = run_async(db.get_all_users_with_details())

    if request.method == 'POST':
        message = request.form.get('message')
        target_type = request.form.get('target_type', 'all')

        # Получаем файлы
        files = request.files.getlist('files')
        saved_files = []

        # Сохраняем загруженные файлы временно
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                saved_files.append(filepath)

        if not message and not saved_files:
            flash('Введите сообщение или прикрепите файл для рассылки', 'danger')
            return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)

        if message and len(message) > 4000:
            flash('Сообщение слишком длинное (макс. 4000 символов)', 'danger')
            return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)

        # Получаем пользователей в зависимости от типа рассылки
        users_to_send = []

        if target_type == 'all':
            users_to_send = run_async(db.get_users_by_company_list())
        elif target_type == 'company':
            companies_selected = request.form.getlist('companies')
            if not companies_selected:
                flash('Выберите хотя бы одну компанию', 'danger')
                return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)
            users_to_send = run_async(db.get_users_by_company_list(companies_selected))
        elif target_type == 'specific':
            user_ids = request.form.getlist('selected_users')
            if not user_ids:
                flash('Выберите хотя бы одного пользователя', 'danger')
                return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)
            user_ids = [int(uid) for uid in user_ids]
            users_to_send = run_async(db.get_users_by_ids_list(user_ids))
        elif target_type == 'conference':
            conferences_selected = request.form.getlist('conferences')
            if not conferences_selected:
                flash('Выберите хотя бы одну конференцию', 'danger')
                return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)
            users_to_send = run_async(db.get_users_by_conference_list(conferences_selected))

        if not users_to_send:
            flash('Нет пользователей для рассылки', 'warning')
            return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)

        # Отправляем сообщения
        results = run_async(bot.broadcast_to_users(users_to_send, message, saved_files))

        # Удаляем временные файлы
        for filepath in saved_files:
            try:
                os.remove(filepath)
            except:
                pass

        # Логируем рассылку
        company_info = ', '.join(request.form.getlist('companies')) if target_type == 'company' else target_type
        run_async(db.log_broadcast(
            username=session.get('username', 'admin'),
            broadcast_type=target_type,
            company=company_info,
            success=results['success'],
            failed=results['failed'],
            message_length=len(message) if message else 0,
            file_count=results.get('file_count', 0)
        ))

        flash(
            f'Рассылка завершена! Успешно: {results["success"]}, Ошибок: {results["failed"]}, Файлов: {results.get("file_count", 0)}',
            'success')
        return redirect(url_for('dashboard'))

    return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)


@app.route('/conferences')
@login_required
def conferences_page():
    """Страница активных конференций"""
    conferences = run_async(db.get_conferences_list())
    stats = {
        'total_conferences': len(conferences),
        'active_conferences': len([c for c in conferences if c.get('user_count', 0) > 0]),
        'upcoming_conferences': 0,
        'total_participants': sum(c.get('user_count', 0) for c in conferences)
    }

    return render_template('conferences.html',
                           conferences=conferences,
                           stats=stats,
                           username=session.get('username'))


@app.route('/users')
@login_required
def users_page():
    """Страница пользователей - админ может добавлять и изменять"""
    try:
        users = run_async(db.get_all_users_with_details())
        companies = run_async(db.get_companies_list())
        conferences = run_async(db.get_conferences_list())

        stats = {
            'total': len(users),
            'online': len([u for u in users if u.get('is_online')]),
            'active_today': len([u for u in users if u.get('last_active') and
                                 u['last_active'] > datetime.now() - timedelta(days=1)]),
            'with_requests': len([u for u in users if u.get('requests_count', 0) > 0]),
            'companies': len(companies),
            'conferences': len(conferences)
        }

        return render_template('users.html',
                               users=users,
                               companies=companies,
                               conferences=conferences,
                               stats=stats,
                               username=session.get('username'))
    except Exception as e:
        print(f"Users page error: {e}")
        flash('Ошибка загрузки пользователей', 'danger')
        return render_template('users.html',
                               users=[],
                               companies=[],
                               conferences=[],
                               stats={'total': 0, 'online': 0, 'active_today': 0, 'with_requests': 0,
                                      'companies': 0, 'conferences': 0},
                               username=session.get('username'))


# ============================================
# API МАРШРУТЫ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ
# ============================================

@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def api_get_user(user_id):
    """Получить данные пользователя"""
    user = run_async(db.get_user_details_by_id(user_id))
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    """Обновить данные пользователя"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Обновляем профиль пользователя
    user_data = {
        'user_id': user_id,
        'username': data.get('username'),
        'full_name': data.get('full_name'),
        'position': data.get('position'),
        'company': data.get('company'),
        'language': data.get('language', 'ru')
    }

    success = run_async(db.save_user_registration(user_data))
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update user'}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """Удалить пользователя (деактивировать)"""
    # TODO: реализовать деактивацию пользователя
    return jsonify({'success': True})


@app.route('/api/users/<int:user_id>/block', methods=['POST'])
@login_required
def api_block_user(user_id):
    """Заблокировать пользователя"""
    # TODO: реализовать блокировку
    return jsonify({'success': True})


@app.route('/api/users/<int:user_id>/unblock', methods=['POST'])
@login_required
def api_unblock_user(user_id):
    """Разблокировать пользователя"""
    # TODO: реализовать разблокировку
    return jsonify({'success': True})


@app.route('/api/users/export', methods=['GET'])
@login_required
def api_export_users():
    """Экспорт пользователей в CSV"""
    users = run_async(db.get_all_users_with_details())

    output = io.StringIO()
    writer = csv.writer(output)

    # Заголовки
    writer.writerow(['ID', 'Username', 'Full Name', 'Company', 'Position',
                     'Language', 'Registered', 'Last Active', 'Requests Count'])

    # Данные
    for user in users:
        writer.writerow([
            user['user_id'],
            user['username'],
            user.get('full_name', ''),
            user.get('company', ''),
            user.get('position', ''),
            user.get('language', 'ru'),
            user.get('registered_at', '').strftime('%Y-%m-%d %H:%M') if user.get('registered_at') else '',
            user.get('last_active', '').strftime('%Y-%m-%d %H:%M') if user.get('last_active') else '',
            user.get('requests_count', 0)
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@app.route('/api/users/count')
@login_required
def api_users_count():
    """API для подсчета пользователей по фильтрам"""
    companies = request.args.get('companies', '').split(',')
    conferences = request.args.get('conferences', '').split(',')

    if companies and companies[0]:
        users = run_async(db.get_users_by_company_list(companies))
    elif conferences and conferences[0]:
        users = run_async(db.get_users_by_conference_list(conferences))
    else:
        users = run_async(db.get_users_by_company_list())

    return jsonify({'count': len(users)})


# ============================================
# ПАНЕЛИ МЕНЕДЖЕРОВ
# ============================================

@app.route('/event')
@login_required
def event_panel():
    """Панель Event-менеджера"""
    certificates = run_async(db.get_all_certificates())
    conferences = run_async(db.get_conferences_list())

    stats = {
        'total_certificates': len(certificates),
        'active_conferences': len([c for c in conferences if c.get('user_count', 0) > 0]),
        'total_conferences': len(conferences)
    }

    return render_template('event_panel.html',
                           certificates=certificates,
                           conferences=conferences,
                           stats=stats,
                           username=session.get('username'))


@app.route('/travel')
@login_required
def travel_panel():
    """Панель Travel-менеджера"""
    visa_requests = run_async(db.get_all_visa_requests())
    flight_requests = run_async(db.get_all_flight_requests())

    stats = {
        'total_visa': len(visa_requests),
        'pending_visa': len([r for r in visa_requests if r.get('status', 'pending') == 'pending']),
        'total_flights': len(flight_requests),
    }

    return render_template('travel_panel.html',
                           visa_requests=visa_requests,
                           flight_requests=flight_requests,
                           stats=stats,
                           username=session.get('username'))


@app.route('/pr')
@login_required
def pr_panel():
    """Панель PR-менеджера"""
    banner_requests = run_async(db.get_all_banner_requests())
    business_cards = run_async(db.get_all_business_cards())

    stats = {
        'total_banners': len(banner_requests),
        'pending_banners': len([r for r in banner_requests if r.get('status', 'pending') == 'pending']),
        'total_cards': len(business_cards),
        'pending_cards': len([c for c in business_cards if c.get('status', 'pending') == 'pending'])
    }

    return render_template('pr_panel.html',
                           banner_requests=banner_requests,
                           business_cards=business_cards,
                           stats=stats,
                           username=session.get('username'))


@app.route('/user_groups')
@login_required
def user_groups_page():
    """Страница управления группами и функциями"""
    groups = run_async(db.get_all_groups())
    features = run_async(db.get_all_features())
    all_users = run_async(db.get_all_users_with_groups())

    stats = {
        'total_groups': len(groups),
        'total_users': len(all_users),
        'users_in_groups': sum(1 for u in all_users if u.get('groups')),
        'total_features': len(features)
    }

    return render_template('user_groups.html',
                           groups=groups,
                           features=features,
                           all_users=all_users,
                           stats=stats,
                           username=session.get('username'))


@app.route('/admin_users')
@login_required
def admin_users_page():
    """Страница управления администраторами"""
    admins = run_async(db.get_all_admin_users())
    return render_template('admin_users.html', admins=admins, username=session.get('username'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Смена пароля"""
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')

        admin = run_async(db.verify_admin(session['username'], old_password))
        if not admin:
            flash('Неверный текущий пароль', 'danger')
            return redirect(url_for('change_password'))

        success = run_async(db.update_admin_user(
            session['admin_id'],
            {'password': new_password}
        ))

        if success:
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Ошибка при смене пароля', 'danger')

    return render_template('change_password.html')


@app.context_processor
def utility_processor():
    """Добавляет функцию get_text во все шаблоны"""
    return dict(get_text=get_text)


# ============================================
# API ДЛЯ УПРАВЛЕНИЯ СТАТУСАМИ ЗАЯВОК
# ============================================

@app.route('/api/visa/<int:request_id>/status', methods=['POST'])
@login_required
def update_visa_status(request_id):
    """Обновить статус визовой заявки"""
    status = request.form.get('status')
    success = run_async(db.update_visa_status(request_id, status))
    if success:
        flash(f'Статус заявки #{request_id} обновлен на "{status}"', 'success')
    else:
        flash('Ошибка при обновлении статуса', 'danger')
    return redirect(url_for('travel_panel'))


@app.route('/api/banner/<int:request_id>/status', methods=['POST'])
@login_required
def update_banner_status(request_id):
    """Обновить статус заявки на баннер"""
    status = request.form.get('status')
    success = run_async(db.update_banner_status(request_id, status))
    if success:
        flash(f'Статус заявки #{request_id} обновлен', 'success')
    else:
        flash('Ошибка при обновлении статуса', 'danger')
    return redirect(url_for('pr_panel'))


@app.route('/api/certificate/<int:request_id>/status', methods=['POST'])
@login_required
def update_certificate_status(request_id):
    """Обновить статус справки"""
    status = request.form.get('status')
    success = run_async(db.update_certificate_status(request_id, status))
    if success:
        flash(f'Статус заявки #{request_id} обновлен', 'success')
    else:
        flash('Ошибка при обновлении статуса', 'danger')
    return redirect(url_for('event_panel'))


# ============================================
# API ДЛЯ ГРУПП
# ============================================

@app.route('/api/groups/add', methods=['POST'])
@login_required
def api_add_group():
    """API для добавления группы"""
    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color', '#667eea')

    if not name:
        flash('Название группы обязательно', 'danger')
        return redirect(url_for('user_groups_page'))

    success = run_async(db.add_group(name, description, color))
    if success:
        flash('Группа создана', 'success')
    else:
        flash('Ошибка при создании группы', 'danger')

    return redirect(url_for('user_groups_page'))


@app.route('/api/groups/<int:group_id>')
@login_required
def api_get_group(group_id):
    """API для получения информации о группе"""
    group = run_async(db.get_group(group_id))
    return jsonify(group)


@app.route('/api/groups/edit/<int:group_id>', methods=['POST'])
@login_required
def api_edit_group(group_id):
    """API для редактирования группы"""
    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color')

    success = run_async(db.update_group(group_id, name, description, color))
    if success:
        flash('Группа обновлена', 'success')
    else:
        flash('Ошибка при обновлении группы', 'danger')

    return redirect(url_for('user_groups_page'))


@app.route('/api/groups/delete/<int:group_id>', methods=['POST'])
@login_required
def api_delete_group(group_id):
    """API для удаления группы"""
    success = run_async(db.delete_group(group_id))
    if success:
        flash('Группа удалена', 'success')
    else:
        flash('Ошибка при удалении группы', 'danger')

    return redirect(url_for('user_groups_page'))


@app.route('/api/groups/<int:group_id>/users')
@login_required
def api_get_group_users(group_id):
    """API для получения пользователей группы"""
    users = run_async(db.get_group_users(group_id))
    return jsonify(users)


@app.route('/api/groups/<int:group_id>/users/<int:user_id>/add', methods=['POST'])
@login_required
def api_add_user_to_group(group_id, user_id):
    """API для добавления пользователя в группу"""
    success = run_async(db.add_user_to_group(user_id, group_id))
    return jsonify({'success': success})


@app.route('/api/groups/<int:group_id>/users/<int:user_id>/remove', methods=['POST'])
@login_required
def api_remove_user_from_group(group_id, user_id):
    """API для удаления пользователя из группы"""
    success = run_async(db.remove_user_from_group(user_id, group_id))
    return jsonify({'success': success})


@app.route('/api/groups/<int:group_id>/export')
@login_required
def export_group_users(group_id):
    """Экспорт участников группы в CSV"""
    users = run_async(db.get_group_users(group_id))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Username', 'Full Name', 'Company'])

    for user in users:
        writer.writerow([user['user_id'], user['username'], user.get('full_name', ''), user.get('company', '')])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'group_{group_id}_users.csv'
    )


@app.route('/api/groups/features/assign', methods=['POST'])
@login_required
def api_assign_features_to_group():
    """API для назначения функций группе"""
    data = request.get_json()
    group_id = data.get('group_id')
    features = data.get('features', [])

    success = run_async(db.assign_features_to_group(group_id, features))
    return jsonify({'success': success})


@app.route('/api/features/add', methods=['POST'])
@login_required
def api_add_feature():
    """API для добавления функции"""
    name = request.form.get('name')
    code = request.form.get('code')
    description = request.form.get('description')
    icon = request.form.get('icon', 'bi-grid')

    if not name or not code:
        flash('Название и код функции обязательны', 'danger')
        return redirect(url_for('user_groups_page'))

    success = run_async(db.add_feature(name, code, description, icon))
    if success:
        flash('Функция добавлена', 'success')
    else:
        flash('Ошибка при добавлении функции', 'danger')

    return redirect(url_for('user_groups_page'))


@app.route('/api/features/delete/<int:feature_id>', methods=['POST'])
@login_required
def api_delete_feature(feature_id):
    """API для удаления функции"""
    success = run_async(db.delete_feature(feature_id))
    return jsonify({'success': success})


@app.route('/api/users/all')
@login_required
def api_get_all_users():
    """API для получения всех пользователей"""
    users = run_async(db.get_all_users_basic())
    return jsonify(users)


@app.route('/group_features/<int:group_id>')
@login_required
def group_features_management(group_id):
    """Страница управления функциями группы"""
    group = run_async(db.get_group(group_id))
    features = run_async(db.get_all_features())
    group_features = run_async(db.get_group_features(group_id))

    return render_template('group_features.html',
                           group=group,
                           features=features,
                           group_features=group_features)


@app.route('/user_groups/<int:user_id>')
@login_required
def user_groups_management(user_id):
    """Страница управления группами конкретного пользователя"""
    user = run_async(db.get_user_details_by_id(user_id))
    groups = run_async(db.get_all_groups())
    user_groups = run_async(db.get_user_groups(user_id))

    return render_template('user_groups_edit.html',
                           user=user,
                           groups=groups,
                           user_groups=user_groups)


@app.route('/manage_group/<int:group_id>')
@login_required
def manage_group_users(group_id):
    """Управление участниками группы"""
    group = run_async(db.get_group(group_id))
    users = run_async(db.get_all_users_basic())
    group_users = run_async(db.get_group_users(group_id))

    return render_template('manage_group_users.html',
                           group=group,
                           users=users,
                           group_users=group_users)


@app.route('/api/visa/<int:request_id>')
@login_required
def api_visa_details(request_id):
    """API для получения деталей визовой заявки"""
    data = run_async(db.get_visa_request(request_id))
    return jsonify(data)


@app.route('/api/banner/<int:request_id>')
@login_required
def api_banner_details(request_id):
    """API для получения деталей заявки на баннер"""
    data = run_async(db.get_banner_request(request_id))
    return jsonify(data)


@app.route('/api/business_card/<int:request_id>')
@login_required
def api_business_card_details(request_id):
    """API для получения деталей заявки на визитки"""
    data = run_async(db.get_business_card_request(request_id))
    return jsonify(data)


@app.route('/api/certificate/<int:request_id>')
@login_required
def api_certificate_details(request_id):
    """API для получения деталей справки"""
    data = run_async(db.get_certificate_request(request_id))
    return jsonify(data)


@app.route('/api/conferences/<path:conference_name>')
@login_required
def api_conference_details(conference_name):
    """API для получения деталей конференции"""
    return jsonify({
        'name': conference_name,
        'city': 'Москва',
        'start_date': '2024-11-15',
        'end_date': '2024-11-17',
        'user_count': 0,
        'users': []
    })


@app.route('/admin_managers')
@login_required
def admin_managers():
    """Страница управления менеджерами (только для админа)"""
    if session.get('role') != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))

    managers = run_async(db.get_all_managers())
    groups = run_async(db.get_manager_groups())

    return render_template('admin_managers.html',
                           managers=managers,
                           groups=groups)


@app.route('/admin_managers/add', methods=['POST'])
@login_required
def add_manager():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    groups = request.form.getlist('groups')

    success = run_async(db.add_manager(username, password, full_name, groups))

    if success:
        flash('Менеджер добавлен', 'success')
    else:
        flash('Ошибка при добавлении', 'danger')

    return redirect(url_for('admin_managers'))


@app.route('/admin_managers/delete/<int:manager_id>', methods=['POST'])
@login_required
def delete_manager(manager_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    success = run_async(db.delete_manager(manager_id))
    return jsonify({'success': success})


# ============================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================


if __name__ == '__main__':
    # Инициализируем БД перед запуском Flask
    print("Initializing database...")
    try:
        init_db()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Check your .env file and make sure PostgreSQL is running")
        # Не выходим, но предупреждаем
        print("⚠️ Continuing without database connection...")

    # Запускаем Flask
    app.run(host='0.0.0.0', port=5005, debug=True)