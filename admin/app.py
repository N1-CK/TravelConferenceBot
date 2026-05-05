from aiogram.client.session import aiohttp
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
from urllib.parse import unquote
import requests


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utility.notifications import *
from database import db

from locales import get_text

import logging
logger = logging.getLogger(__name__)

from aiogram import Bot
import threading
import concurrent.futures

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================
# КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: ОДИН EVENT LOOP
# ============================================

_bg_loop = asyncio.new_event_loop()
_db_initialized = False

def _run_bg_loop(loop):
    """Функция для работы фонового потока"""
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Запускаем цикл навсегда в отдельном фоновом (daemon) потоке
_bg_thread = threading.Thread(target=_run_bg_loop, args=(_bg_loop,), daemon=True)
_bg_thread.start()

@app.context_processor
def inject_request():
    return {'request': request}

def run_async(coro, timeout=30):
    """
    Универсальная функция. Отправляет асинхронную задачу в стабильный
    фоновый цикл и ждет результат. Безопасна для Flask.
    """
    future = asyncio.run_coroutine_threadsafe(coro, _bg_loop)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        logger.error("Async operation timeout")
        return None
    except Exception as e:
        logger.error(f"Async execution error: {e}")
        return None


def init_db():
    """Инициализация БД"""
    global _db_initialized
    if not _db_initialized:
        try:
            run_async(db.create_pool())

            # КРИТИЧЕСКИ ВАЖНО: создаем таблицы для групп и функций
            # run_async(db.create_groups_tables())

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


def group_required(allowed_groups=None):
    """Декоратор для проверки доступа по группам менеджера"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                return redirect(url_for('login'))

            # Админ имеет доступ ко всему
            if session.get('role') == 'admin':
                return f(*args, **kwargs)

            user_groups = session.get('groups', [])

            # Если allowed_groups не указаны - доступ есть у всех
            if allowed_groups is None:
                return f(*args, **kwargs)

            # Проверяем, есть ли у менеджера нужная группа
            if any(group in user_groups for group in allowed_groups):
                return f(*args, **kwargs)

            flash('У вас нет доступа к этой странице', 'danger')
            return redirect(url_for('dashboard'))

        return decorated_function

    return decorator

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
                form_data.add_field('document', open(file, 'rb'),
                                    filename=os.path.basename(file),
                                    content_type='application/octet-stream')
                if text:
                    form_data.add_field('caption', text)
                    form_data.add_field('parse_mode', 'HTML')

                try:
                    async with session.post(url, data=form_data) as resp:
                        result = await resp.json()
                        return result.get('ok', False)
                except Exception as e:
                    print(f"Error sending document: {e}")
                    return False
                finally:
                    # Закрываем файл
                    if 'form_data' in locals():
                        pass
            else:
                # Отправка только текста
                url = f"{self.api_url}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': text if text else "",
                    'parse_mode': 'HTML'  # Для текста parse_mode работает
                }

                try:
                    async with session.post(url, json=payload) as resp:
                        result = await resp.json()
                        return result.get('ok', False)
                except Exception as e:
                    print(f"Error sending message: {e}")
                    return False

    async def broadcast_to_users(self, users, message, files=None):
        """Массовая рассылка пользователям с файлами (с оптимизацией отправки по file_id)"""
        results = {'success': 0, 'failed': 0, 'file_ids': []}
        file_count = len(files) if files else 0

        # Кеш: загружаем файл в ТГ один раз, сохраняем его ID, дальше шлем всем мгновенно по ID
        file_ids_map = {}

        for user in users:
            user_id = user.get('user_id')
            if not user_id:
                results['failed'] += 1
                continue

            success = False
            try:
                html_message = message if message else ""

                async with aiohttp.ClientSession() as session:
                    if files and len(files) > 0:
                        # Отправляем файлы
                        for idx, file_path in enumerate(files):
                            if os.path.exists(file_path):
                                url = f"{self.api_url}/sendDocument"
                                form_data = aiohttp.FormData()
                                form_data.add_field('chat_id', str(user_id))

                                # ОПТИМИЗАЦИЯ: Если файл уже в ТГ, просто отдаем его file_id
                                if file_path in file_ids_map:
                                    form_data.add_field('document', file_ids_map[file_path])

                                    if idx == 0 and html_message:
                                        form_data.add_field('caption', html_message)
                                        form_data.add_field('parse_mode', 'HTML')

                                    async with session.post(url, data=form_data) as resp:
                                        result = await resp.json()
                                        if result.get('ok'): success = True
                                else:
                                    # ИНАЧЕ: Физически грузим файл (произойдет только для 1-го юзера)
                                    with open(file_path, 'rb') as f:
                                        form_data.add_field('document', f, filename=os.path.basename(file_path))

                                        if idx == 0 and html_message:
                                            form_data.add_field('caption', html_message)
                                            form_data.add_field('parse_mode', 'HTML')

                                        async with session.post(url, data=form_data) as resp:
                                            result = await resp.json()
                                            if result.get('ok'):
                                                success = True
                                                # Ловим настоящий Telegram file_id и сохраняем!
                                                doc = result.get('result', {}).get('document', {})
                                                if 'file_id' in doc:
                                                    file_ids_map[file_path] = doc['file_id']

                                await asyncio.sleep(0.05)
                        if files and len(files) > 0:
                            success = True
                    else:
                        # Отправка только текста
                        url = f"{self.api_url}/sendMessage"
                        payload = {
                            'chat_id': user_id,
                            'text': html_message,
                            'parse_mode': 'HTML'
                        }
                        async with session.post(url, json=payload) as resp:
                            result = await resp.json()
                            success = result.get('ok', False)

            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
                success = False

            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

        results['file_count'] = file_count
        results['file_ids'] = list(file_ids_map.values())  # Передаем полученные ID в роут
        return results


# Инициализация Telegram бота
bot = TelegramBot(os.getenv('TG_BOT_TOKEN', ''))

# ============================================
# МАРШРУТЫ
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа для менеджеров и администраторов"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Сначала проверяем в таблице managers
        manager = run_async(db.verify_manager(username, password))

        if manager:
            session['logged_in'] = True
            session['username'] = manager['username']
            session['manager_id'] = manager['id']
            session['full_name'] = manager['full_name']
            session['role'] = manager['role']  # 'admin' или 'manager'
            session['groups'] = manager['group_names']  # ['pr', 'event', 'travel']
            session['login_time'] = datetime.now().isoformat()

            flash(f'Добро пожаловать, {manager["full_name"] or manager["username"]}!', 'success')
            return redirect(url_for('dashboard'))

        # Если не нашли в managers, проверяем в admin_users (старые админы)
        admin = run_async(db.verify_admin(username, password))

        if admin:
            # Конвертируем старого админа в менеджера
            session['logged_in'] = True
            session['username'] = admin['username']
            session['manager_id'] = admin['id']
            session['full_name'] = admin['full_name']
            session['role'] = admin['role']  # 'admin'
            session['groups'] = ['admin', 'pr', 'event', 'travel']  # Все группы
            session['login_time'] = datetime.now().isoformat()

            flash(f'Добро пожаловать, {admin["full_name"] or admin["username"]}!', 'success')
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
    companies = run_async(db.get_all_companies_from_config())
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
                if not allowed_file(file.filename):
                    flash(f'Файл {file.filename} имеет запрещенный формат!', 'danger')
                    continue  # Пропускаем опасный файл

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

        # Вытаскиваем настоящие Telegram file_id, которые бот только что получил
        telegram_file_ids = results.get('file_ids', [])

        manager_name = session.get('full_name') or session.get('username') or 'Менеджер'
        display_name = f"{manager_name} (Рассылка)"
        messages_to_insert = []

        for user in users_to_send:
            uid = user.get('user_id')
            if uid:
                # Если были файлы, объединяем текст и файл в ОДНО сообщение
                if saved_files and telegram_file_ids:
                    for idx, tg_file_id in enumerate(telegram_file_ids):
                        # Текст прикрепляем только к первому файлу как подпись (caption)
                        text_to_save = message if idx == 0 and message else ""
                        messages_to_insert.append(
                            (uid, display_name, 'outgoing', text_to_save, None, tg_file_id)
                        )
                # Если файлов нет, сохраняем просто текст
                elif message:
                    messages_to_insert.append(
                        (uid, display_name, 'outgoing', message, None, None)
                    )

        if messages_to_insert:
            run_async(db.save_user_messages_bulk(messages_to_insert))

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
        companies = run_async(db.get_all_companies_from_config())
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


@app.route('/api/users/count', methods=['GET', 'POST'])
@login_required
def api_users_count():
    """API для подсчета пользователей по фильтрам"""
    if request.method == 'POST':
        data = request.get_json()
        companies = data.get('companies', [])
        conferences = data.get('conferences', [])
    else:
        companies = request.args.get('companies', '').split(',')
        conferences = request.args.get('conferences', '').split(',')
        if companies == ['']:
            companies = []
        if conferences == ['']:
            conferences = []

    if companies:
        users = run_async(db.get_users_by_company_list(companies))
    elif conferences:
        users = run_async(db.get_users_by_conference_list(conferences))
    else:
        users = run_async(db.get_users_by_company_list())

    return jsonify({'count': len(users)})

# ============================================
# ПАНЕЛИ МЕНЕДЖЕРОВ
# ============================================

@app.route('/event')
@login_required
@group_required(['event', 'admin'])
def event_panel():
    """Панель Event-менеджера"""
    ticket_requests = run_async(db.get_all_ticket_requests())
    ticket_stats = run_async(db.get_ticket_request_stats())

    stats = {
        'ticket_stats': ticket_stats
    }

    return render_template('event_panel.html',
                           ticket_requests=ticket_requests,
                           stats=stats,
                           username=session.get('username'))


# app.py - ЗАМЕНИТЕ существующую функцию travel_panel

@app.route('/travel')
@login_required
@group_required(['travel', 'admin'])
def travel_panel():
    """Панель Travel-менеджера"""
    # Получаем статистику
    stats = run_async(db.get_travel_stats())

    # Получаем заявки на билеты и суточные
    requests = run_async(db.get_all_travel_flight_requests())
    per_diem_requests = run_async(db.get_all_per_diem_requests())

    return render_template('travel_panel.html',
                           requests=requests,
                           per_diem_requests=per_diem_requests,
                           stats=stats,
                           username=session.get('username'))


@app.route('/pr')
@login_required
@group_required(['pr', 'admin'])
def pr_panel():
    """Панель PR-менеджера"""
    banner_requests = run_async(db.get_all_banner_requests())
    business_cards = run_async(db.get_all_business_cards())

    # Убеждаемся, что у каждой заявки есть статус
    for req in banner_requests:
        if 'status' not in req or not req.get('status'):
            req['status'] = 'pending'
    for card in business_cards:
        if 'status' not in card or not card.get('status'):
            card['status'] = 'pending'

    # Получаем фильтры
    banner_filter = request.args.get('banner_filter', 'all')
    cards_filter = request.args.get('cards_filter', 'all')

    # Применяем фильтры для отображения
    filtered_banners = banner_requests
    if banner_filter != 'all':
        filtered_banners = [r for r in banner_requests if r.get('status') == banner_filter]

    filtered_cards = business_cards
    if cards_filter != 'all':
        filtered_cards = [c for c in business_cards if c.get('status') == cards_filter]

    # Статистика для баннеров
    banner_stats = {
        'total': len(banner_requests),
        'pending': len([r for r in banner_requests if r.get('status') == 'pending']),
        'in_progress': len([r for r in banner_requests if r.get('status') == 'in_progress']),
        'ready': len([r for r in banner_requests if r.get('status') == 'ready'])
    }

    # Статистика для визиток
    cards_stats = {
        'total': len(business_cards),
        'pending': len([c for c in business_cards if c.get('status') == 'pending']),
        'in_progress': len([c for c in business_cards if c.get('status') == 'in_progress']),
        'ready': len([c for c in business_cards if c.get('status') == 'ready'])
    }

    return render_template('pr_panel.html',
                           banner_requests=filtered_banners,
                           business_cards=filtered_cards,
                           banner_stats=banner_stats,
                           cards_stats=cards_stats,
                           banner_filter=banner_filter,
                           cards_filter=cards_filter,
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
        confirm_password = request.form.get('confirm_password')

        # Проверка совпадения паролей
        if new_password != confirm_password:
            flash(get_text('passwords_not_match', session.get('lang', 'ru')), 'danger')
            return redirect(url_for('change_password'))

        # Проверка длины
        if len(new_password) < 6:
            flash(get_text('password_min_length', session.get('lang', 'ru')), 'danger')
            return redirect(url_for('change_password'))

        # Пытаемся найти пользователя сначала в таблице managers, потом в admin_users
        manager = run_async(db.verify_manager(session['username'], old_password))

        if manager:
            # Это менеджер из таблицы managers
            success = run_async(db.update_manager_password(
                session['manager_id'],
                new_password
            ))
            if success:
                flash(get_text('password_changed_success', session.get('lang', 'ru')), 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(get_text('error_occurred', session.get('lang', 'ru')), 'danger')
        else:
            # Проверяем в старой таблице admin_users
            admin = run_async(db.verify_admin(session['username'], old_password))
            if admin:
                # Обновляем пароль в admin_users
                success = run_async(db.update_admin_password(session['username'], new_password))
                if success:
                    flash(get_text('password_changed_success', session.get('lang', 'ru')), 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash(get_text('error_occurred', session.get('lang', 'ru')), 'danger')
            else:
                flash(get_text('invalid_current_password', session.get('lang', 'ru')), 'danger')

    return render_template('change_password.html')


# Добавьте после других API маршрутов

@app.route('/api/per_diem/requests')
@login_required
def api_get_per_diem_requests():
    """API для получения заявок на суточные"""
    if session.get('role') != 'admin' and 'travel' not in session.get('groups', []):
        return jsonify({'error': 'Access denied'}), 403

    requests = run_async(db.get_all_per_diem_requests())
    return jsonify(requests)


@app.route('/api/per_diem/<int:request_id>/status', methods=['POST'])
@login_required
def api_update_per_diem_status(request_id):
    """Обновить статус заявки на суточные"""
    if session.get('role') != 'admin' and 'travel' not in session.get('groups', []):
        return jsonify({'error': 'Access denied'}), 403

    status = request.form.get('status')
    if status not in ['pending', 'in_progress', 'completed']:
        return jsonify({'error': 'Invalid status'}), 400

    success = run_async(db.update_per_diem_status(request_id, status))
    return jsonify({'success': success})


@app.route('/api/travel/requests')
@login_required
def api_get_travel_requests():
    """API для получения всех заявок на билеты (travel_flight_request)"""
    if session.get('role') != 'admin' and 'travel' not in session.get('groups', []):
        return jsonify({'error': 'Access denied'}), 403

    try:
        # Получаем данные напрямую через run_async
        requests = run_async(db.get_all_travel_flight_requests())
        return jsonify(requests)
    except Exception as e:
        logger.error(f"Error getting travel requests: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/travel/request/<int:request_id>')
@login_required
def api_get_travel_request(request_id):
    """API для получения деталей заявки на билет"""
    if session.get('role') != 'admin' and 'travel' not in session.get('groups', []):
        return jsonify({'error': 'Access denied'}), 403

    try:
        request_data = run_async(db.get_travel_flight_request_by_id(request_id))
        if request_data:
            return jsonify(request_data)
        return jsonify({'error': 'Request not found'}), 404
    except Exception as e:
        logger.error(f"Error getting travel request {request_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/travel/request/<int:request_id>/visa_status', methods=['POST'])
@login_required
def api_update_travel_visa_status(request_id):
    """Обновить статус визовой заявки и отправить уведомление"""
    if session.get('role') != 'admin' and 'travel' not in session.get('groups', []):
        return jsonify({'error': 'Access denied'}), 403

    status = request.form.get('status')
    if status not in ['pending', 'in_progress', 'ready']:
        return jsonify({'error': 'Invalid status'}), 400

    # Получаем текущий статус и данные пользователя
    current_request = run_async(db.get_travel_flight_request_by_id(request_id))
    old_status = current_request.get('visa_request_status') if current_request else None

    success = run_async(db.update_travel_visa_request_status(request_id, status))

    if success and current_request and old_status != status:
        # Получаем язык пользователя
        user_data = run_async(db.get_user_data(current_request.get('user_id')))
        lang = user_data.get('language', 'ru') if user_data else 'ru'

        # Отправляем уведомление
        from utility.notifications import notify_travel_visa_status_change
        run_async(notify_travel_visa_status_change(
            user_id=current_request.get('user_id'),
            request_id=request_id,
            old_status=old_status or 'pending',
            new_status=status,
            username=current_request.get('username'),
            lang=lang
        ))

        return jsonify({'success': True})

    return jsonify({'success': False}), 500

@app.route('/api/travel/request/<int:request_id>/flight_status', methods=['POST'])
@login_required
def api_update_travel_flight_status(request_id):
    """Обновить статус заявки на билет и отправить уведомление"""
    if session.get('role') != 'admin' and 'travel' not in session.get('groups', []):
        return jsonify({'error': 'Access denied'}), 403

    status = request.form.get('status')
    if status not in ['pending', 'in_progress', 'purchased']:
        return jsonify({'error': 'Invalid status'}), 400

    # Получаем текущий статус и данные пользователя
    current_request = run_async(db.get_travel_flight_request_by_id(request_id))
    old_status = current_request.get('flight_request_status') if current_request else None

    success = run_async(db.update_travel_flight_request_status(request_id, status))

    if success and current_request and old_status != status:
        # Получаем язык пользователя
        user_data = run_async(db.get_user_data(current_request.get('user_id')))
        lang = user_data.get('language', 'ru') if user_data else 'ru'

        # Отправляем уведомление
        from utility.notifications import notify_travel_flight_status_change
        run_async(notify_travel_flight_status_change(
            user_id=current_request.get('user_id'),
            request_id=request_id,
            old_status=old_status or 'pending',
            new_status=status,
            username=current_request.get('username'),
            lang=lang
        ))

        return jsonify({'success': True})

    return jsonify({'success': False}), 500


@app.route('/set_language/<lang>')
def set_language(lang):
    """Смена языка интерфейса"""
    if lang in ['ru', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('dashboard'))


@app.context_processor
def utility_processor():
    """Добавляет функцию get_text во все шаблоны с учетом выбранного языка"""

    def _get_text(key, default=None, **kwargs):
        lang = session.get('lang', 'ru')
        text = get_text(key, lang)

        # Если текст не найден (вернулся сам ключ) и указан default - используем default
        if text == key and default is not None:
            text = default

        # Применяем форматирование если есть kwargs
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass

        return text

    return dict(get_text=_get_text)


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
    """Обновить статус заявки на баннер с уведомлением"""
    status = request.form.get('status')
    if status not in ['pending', 'in_progress', 'ready']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    # Получаем текущий статус
    current_request = run_async(db.get_banner_request_by_id(request_id))
    old_status = current_request.get('status') if current_request else None

    success = run_async(db.update_banner_status(request_id, status))

    if success and current_request and old_status != status:
        # Получаем язык пользователя
        user_data = run_async(db.get_user_data(current_request.get('user_id')))
        lang = user_data.get('language', 'ru') if user_data else 'ru'

        # Отправляем уведомление с языком
        run_async(notify_banner_status_change(
            user_id=current_request.get('user_id'),
            request_id=request_id,
            old_status=old_status or 'pending',
            new_status=status,
            username=current_request.get('username'),
            lang=lang  # Добавляем явную передачу языка
        ))

        return jsonify({'success': True})

    return jsonify({'success': False}), 500


@app.route('/api/business_card/<int:request_id>/status', methods=['POST'])
@login_required
def update_business_card_status(request_id):
    """Обновить статус заявки на визитки с уведомлением"""
    status = request.form.get('status')
    if status not in ['pending', 'in_progress', 'ready']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    # Получаем текущий статус
    current_request = run_async(db.get_business_card_request_by_id(request_id))
    old_status = current_request.get('status') if current_request else None

    success = run_async(db.update_business_card_status(request_id, status))

    if success and current_request and old_status != status:
        # Получаем язык пользователя
        user_data = run_async(db.get_user_data(current_request.get('user_id')))
        lang = user_data.get('language', 'ru') if user_data else 'ru'

        # Отправляем уведомление с языком
        run_async(notify_business_card_status_change(
            user_id=current_request.get('user_id'),
            request_id=request_id,
            old_status=old_status or 'pending',
            new_status=status,
            username=current_request.get('username'),
            lang=lang  # Добавляем явную передачу языка
        ))

        return jsonify({'success': True})

    return jsonify({'success': False}), 500


# ============================================
# API ДЛЯ ГРУПП
# ============================================


@app.route('/api/users/all')
@login_required
def api_get_all_users():
    """API для получения всех пользователей"""
    users = run_async(db.get_all_users_basic())
    return jsonify(users)


@app.route('/api/users/by_conferences', methods=['POST'])
@login_required
def api_get_users_by_conferences():
    """API для получения пользователей по списку конференций (с деталями)"""
    data = request.get_json()
    conferences = data.get('conferences', [])

    if not conferences:
        return jsonify([])

    users = run_async(db.get_users_by_conference_list(conferences))
    return jsonify(users)


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


# В вашем веб-приложении (app.py или web_app.py)

# В app.py найдите и ЗАМЕНИТЕ этот асинхронный маршрут:

from urllib.parse import unquote


@app.route('/api/conferences/<path:conference_name>')
@login_required
def get_conference_details(conference_name):
    """API для получения деталей конференции (синхронная версия)"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    # Декодируем URL-encoded строку (преобразуем %20 обратно в пробелы)
    decoded_name = unquote(conference_name)

    print(f"DEBUG: Looking for conference: '{decoded_name}'")  # Для отладки

    try:
        def _get_details():
            async def fetch():
                async with db.pool.acquire() as conn:
                    # Получаем основную информацию о конференции
                    conference = await conn.fetchrow(f"""
                        SELECT 
                            conference_name as name,
                            city,
                            start_date,
                            end_date,
                            bot_link,
                            additional_info,
                            is_active
                        FROM {db.db_schema_config}.conferences
                        WHERE conference_name = $1
                    """, decoded_name)  # Используем декодированное имя

                    if not conference:
                        # Попробуем поискать без учета регистра
                        conference = await conn.fetchrow(f"""
                            SELECT 
                                conference_name as name,
                                city,
                                start_date,
                                end_date,
                                bot_link,
                                additional_info,
                                is_active
                            FROM {db.db_schema_config}.conferences
                            WHERE LOWER(conference_name) = LOWER($1)
                        """, decoded_name)

                    if not conference:
                        print(f"DEBUG: Conference '{decoded_name}' not found in database")
                        return None

                    # Получаем участников конференции
                    users = await conn.fetch(f"""
                        SELECT DISTINCT
                            up.user_id,
                            up.username,
                            up.full_name,
                            up.company,
                            up.position
                        FROM {db.db_schema_config}.user_profiles up
                        JOIN {db.db_schema}.user_conferences uc ON up.username = uc.username
                        WHERE uc.conference_name = $1
                        ORDER BY up.username
                    """, decoded_name)

                    # Подсчитываем количество участников
                    user_count = len(users) if users else 0

                    # Формируем ответ
                    result = dict(conference)
                    result['user_count'] = user_count
                    result['users'] = [dict(user) for user in users] if users else []

                    return result

            return run_async(fetch())

        result = _get_details()

        if result is None:
            return jsonify({'error': f'Conference "{decoded_name}" not found'}), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting conference details for '{decoded_name}': {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin_managers')
@login_required
@group_required(['admin'])
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


# app.py - добавить маршруты для управления менеджерами

@app.route('/admin_managers/<int:manager_id>')
@login_required
@group_required(['admin'])
def get_manager_json(manager_id):
    """API для получения данных менеджера"""
    managers = run_async(db.get_all_managers())
    manager = next((m for m in managers if m['id'] == manager_id), None)
    if manager:
        return jsonify(manager)
    return jsonify({'error': 'Not found'}), 404


@app.route('/admin_managers/edit/<int:manager_id>', methods=['POST'])
@login_required
@group_required(['admin'])
def edit_manager(manager_id):
    """Редактирование менеджера"""
    full_name = request.form.get('full_name')
    is_active = request.form.get('is_active') == 'true'
    groups = request.form.getlist('groups')

    # Обновляем данные менеджера
    success = run_async(db.update_manager(manager_id, full_name, is_active, groups))

    if success:
        flash('Данные менеджера обновлены', 'success')
    else:
        flash('Ошибка при обновлении', 'danger')

    return redirect(url_for('admin_managers'))


@app.route('/admin_managers/reset_password/<int:manager_id>', methods=['POST'])
@login_required
@group_required(['admin'])
def reset_manager_password(manager_id):
    """Сброс пароля менеджера"""
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('Пароли не совпадают', 'danger')
        return redirect(url_for('admin_managers'))

    if len(new_password) < 6:
        flash('Пароль должен содержать минимум 6 символов', 'danger')
        return redirect(url_for('admin_managers'))

    success = run_async(db.update_manager_password(manager_id, new_password))

    if success:
        flash('Пароль успешно изменен', 'success')
    else:
        flash('Ошибка при смене пароля', 'danger')

    return redirect(url_for('admin_managers'))


@app.route('/user_chats')
@login_required
def user_chats():
    """Страница чатов с пользователями"""
    conversations = run_async(db.get_user_conversations())
    return render_template('user_chats.html', conversations=conversations)

@app.route('/api/conversations')
@login_required
def api_get_conversations():
    """API для получения списка диалогов для боковой панели"""
    conversations = run_async(db.get_user_conversations())
    # Форматируем даты для JSON
    for conv in conversations:
        if conv.get('last_message_time'):
            conv['last_message_time'] = conv['last_message_time'].isoformat()
    return jsonify(conversations)

@app.route('/api/questions/forward', methods=['POST'])
@login_required
def api_forward_question():
    """API для пересылки вопроса в другой отдел (исправленная версия)"""
    data = request.get_json()

    question_id = data.get('question_id')
    source_department = data.get('source_department')
    target_department = data.get('target_department')
    source_table = data.get('source_table')

    if not all([question_id, source_department, target_department, source_table]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Проверяем права доступа менеджера к исходному отделу
    manager_groups = session.get('groups', [])
    role = session.get('role')

    # Админ может всё, менеджер только из своих отделов
    if role != 'admin' and source_department not in manager_groups:
        return jsonify({'error': f'Access denied to {source_department} department'}), 403

    # Получаем вопрос из исходной таблицы
    question = run_async(db.get_question_by_id(source_table, question_id))

    if not question:
        return jsonify({'error': 'Question not found'}), 404

    # Определяем целевую таблицу
    target_tables = {
        'pr': f'{db.db_schema_pr}.pr_questions',
        'event': f'{db.db_schema_event}.event_questions',
        'travel': f'{db.db_schema_travel}.travel_questions'
    }

    target_table = target_tables.get(target_department)
    if not target_table:
        return jsonify({'error': 'Invalid target department'}), 400

    # Сохраняем пересланный вопрос в целевой таблице
    forwarded_question = {
        'username': question.get('username'),
        'user_id': question.get('user_id'),
        'category': f"forwarded_from_{source_department}",
        'question': f"[🔄 Переслано из отдела {source_department.upper()} менеджером @{session.get('username')}]\n\n📝 Оригинальный вопрос:\n{question.get('question')}",
        'created_at': question.get('created_at')
    }

    success = run_async(db.save_forwarded_question(target_table, forwarded_question))

    if success:
        # Логируем действие
        run_async(db.log_user_action(
            user_id=session.get('manager_id', 0),
            username=session.get('username'),
            action="question_forwarded",
            details={
                "question_id": question_id,
                "source": source_department,
                "target": target_department,
                "source_table": source_table
            }
        ))
        return jsonify({'success': True, 'message': f'Question forwarded to {target_department.upper()}'})

    return jsonify({'error': 'Failed to forward question'}), 500


@app.route('/api/questions/<int:question_id>/departments', methods=['GET'])
@login_required
def api_get_available_departments_for_forward(question_id):
    """API для получения списка отделов, доступных для пересылки вопроса"""
    manager_groups = session.get('groups', [])
    role = session.get('role')

    # Все возможные отделы
    all_departments = [
        {'id': 'pr', 'name': '📢 PR отдел'},
        {'id': 'event', 'name': '🎪 Event отдел'},
        {'id': 'travel', 'name': '✈️ Travel отдел'}
    ]

    # Админ может пересылать в любой отдел (кроме исходного)
    if role == 'admin':
        # Нужно знать исходный отдел вопроса
        source_department = request.args.get('source', '')
        available = [d for d in all_departments if d['id'] != source_department]
        return jsonify({'departments': available})

    # Менеджер может пересылать только в те отделы, к которым у него есть доступ
    # (и которые не являются исходным отделом)
    source_department = request.args.get('source', '')
    available = [d for d in all_departments
                 if d['id'] != source_department and d['id'] in manager_groups]

    return jsonify({'departments': available})


@app.route('/api/user_messages/<int:user_id>')
@login_required
def api_get_user_messages(user_id):
    """API для получения сообщений пользователя"""
    messages = run_async(db.get_user_messages(user_id, limit=100))
    user_data = run_async(db.get_user_data(user_id))

    # Форматируем сообщения для отображения
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            'id': msg['id'],
            'direction': msg['direction'],
            'message_text': msg['message_text'],
            'sender_username': msg.get('username', ''),
            'file_type': msg.get('file_type'),
            'file_id': msg.get('file_id'),
            'created_at': msg['created_at'].isoformat()
        })

    return jsonify({
        'user_id': user_id,
        'username': user_data.get('username') if user_data else str(user_id),
        'full_name': user_data.get('full_name', ''),
        'messages': formatted_messages
    })


@app.route('/api/user_messages/<int:user_id>/read', methods=['POST'])
@login_required
def api_mark_messages_read(user_id):
    """Отметить сообщения как прочитанные"""
    success = run_async(db.mark_messages_read(user_id, session.get('manager_id')))
    return jsonify({'success': success})


@app.route('/api/send_message', methods=['POST'])
@login_required
def api_send_message():
    """Отправка сообщения с сохранением реального Telegram file_id"""
    user_id = request.form.get('user_id', type=int)
    message = request.form.get('message')
    file = request.files.get('file')

    if not user_id: return jsonify({'error': 'User ID required'}), 400

    manager_display_name = f"{session.get('full_name', '')} (@{session.get('username', '')})"

    filepath = None
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    # 1. Сначала отправляем в Telegram, чтобы получить настоящий file_id
    telegram_file_id = None
    try:
        bot_token = os.getenv('TG_BOT_TOKEN')

        async def send_to_tg():
            async with Bot(token=bot_token) as bot_obj:
                if filepath:
                    from aiogram.types import FSInputFile
                    res = await bot_obj.send_document(user_id, FSInputFile(filepath), caption=message,
                                                      parse_mode="HTML")
                    return res.document.file_id
                else:
                    await bot_obj.send_message(user_id, message, parse_mode="HTML")
                    return None

        telegram_file_id = run_async(send_to_tg())
    except Exception as e:
        logger.error(f"TG Send error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if filepath and os.path.exists(filepath): os.remove(filepath)

    # 2. Теперь сохраняем в базу уже с ПРАВИЛЬНЫМ file_id
    msg_id = run_async(db.save_user_message(
        user_id=user_id,
        username=manager_display_name,
        message_text=message,
        file_type=file.content_type if file else None,
        file_id=telegram_file_id,  # Сохраняем ID от Telegram!
        direction='outgoing'
    ))

    return jsonify({'success': True, 'message_id': msg_id})


@app.route('/api/file/<file_id>')
@login_required
def api_get_file(file_id):
    """Маршрут для скачивания файлов из Telegram"""
    bot_token = os.getenv('TG_BOT_TOKEN')
    if not bot_token or not file_id:
        return "Ошибка конфигурации", 500

    # Если это просто имя файла (старые записи или ошибка), скачать не выйдет
    if len(file_id) < 20:
        return "Этот файл был удален с сервера и не имеет ID в Telegram", 404

    try:
        # 1. Получаем путь к файлу через API Telegram
        file_info = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}").json()
        if not file_info.get('ok'):
            return "Файл не найден в Telegram", 404

        file_path = file_info['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

        # 2. Скачиваем и отдаем пользователю
        file_data = requests.get(download_url)
        return send_file(
            io.BytesIO(file_data.content),
            download_name=file_path.split('/')[-1],
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        return "Ошибка при загрузке файла", 500


# Добавьте эти маршруты в app.py
# app.py - ЗАМЕНИТЕ существующий маршрут /api/questions

@app.route('/api/questions')
@login_required
def api_get_my_questions():
    """API для получения вопросов, доступных текущему менеджеру"""
    manager_groups = session.get('groups', [])
    role = session.get('role')

    # Админ видит все вопросы
    if role == 'admin':
        manager_groups = ['pr', 'event', 'travel']

    all_questions = []

    # Определяем соответствие групп и таблиц
    tables_map = {
        'pr': f'{db.db_schema_pr}.pr_questions',
        'event': f'{db.db_schema_event}.event_questions',
        'travel': f'{db.db_schema_travel}.travel_questions'
    }

    for group in manager_groups:
        if group not in tables_map:
            continue

        full_table = tables_map[group]

        # Получаем вопросы для этого отдела
        questions = run_async(db.get_all_questions_by_table(full_table))

        for q in questions:
            q['department'] = group
            all_questions.append(q)

    # Сортируем по дате (новые сверху)
    all_questions.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)

    return jsonify(all_questions)

# Добавьте эти маршруты в app.py

@app.route('/api/affiliate/bookings')
@login_required
def api_affiliate_bookings():
    """API для получения бронирований"""
    bookings = run_async(db.get_all_affiliate_bookings())
    return jsonify(bookings)

@app.route('/api/affiliate/reports')
@login_required
def api_affiliate_reports():
    """API для получения отчетов"""
    reports = run_async(db.get_all_affiliate_reports())
    return jsonify(reports)

@app.route('/api/affiliate/booking/<int:booking_id>/status', methods=['POST'])
@login_required
def api_update_booking_status(booking_id):
    """Обновить статус бронирования"""
    status = request.form.get('status')
    success = run_async(db.update_affiliate_booking_status(booking_id, status))
    return jsonify({'success': success})

@app.route('/api/affiliate/report/<int:report_id>/status', methods=['POST'])
@login_required
def api_update_report_status(report_id):
    """Обновить статус отчета"""
    status = request.form.get('status')
    success = run_async(db.update_affiliate_report_status(report_id, status))
    return jsonify({'success': success})


@app.route('/api/ticket/<int:request_id>/status', methods=['POST'])
@login_required
def api_update_ticket_status(request_id):
    """API для обновления статуса заявки на билет с уведомлением"""
    # Проверяем права доступа
    user_groups = session.get('groups', [])
    role = session.get('role')

    if role != 'admin' and 'event' not in user_groups:
        return jsonify({'error': 'Access denied'}), 403

    status = request.form.get('status')
    if status not in ['pending', 'in_progress', 'ready']:
        return jsonify({'error': 'Invalid status'}), 400

    # Получаем текущий статус до обновления
    current_request = run_async(db.get_ticket_request_by_id(request_id))
    old_status = current_request.get('status') if current_request else None

    success = run_async(db.update_ticket_request_status(request_id, status))

    if success:
        # Отправляем уведомление пользователю (синхронно через run_async)
        if current_request:
            # Используем run_async вместо create_task
            run_async(notify_ticket_status_change(
                user_id=current_request.get('user_id'),
                request_id=request_id,
                old_status=old_status or 'pending',
                new_status=status,
                username=current_request.get('username')
            ))

        # Логируем действие
        run_async(db.log_user_action(
            user_id=session.get('manager_id', 0),
            username=session.get('username'),
            action="ticket_status_changed",
            details={
                "request_id": request_id,
                "new_status": status,
                "old_status": old_status
            }
        ))
        return jsonify({'success': True})

    return jsonify({'error': 'Failed to update status'}), 500

@app.route('/api/questions/share', methods=['POST'])
@login_required
def api_share_question():
    """API для пересылки вопроса в другой отдел"""
    data = request.get_json()
    question_id = data.get('question_id')
    source_department = data.get('source_department')
    target_department = data.get('target_department')

    if not all([question_id, source_department, target_department]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Проверяем права
    manager_groups = session.get('groups', [])
    if source_department not in manager_groups and session.get('role') != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    success = run_async(db.share_question_with_department(
        question_id=question_id,
        question_type=f"{source_department}_question",
        source_department=source_department,
        target_department=target_department,
        shared_by=session.get('username')
    ))

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