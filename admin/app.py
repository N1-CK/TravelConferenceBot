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

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp'

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


# Вспомогательная функция для выполнения async запросов к БД
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================
# МОДЕЛИ ДЛЯ РАБОТЫ С БД
# ============================================

class Database:
    @staticmethod
    async def get_users_by_company(companies=None):
        """Получить пользователей по списку компаний"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            if companies:
                if isinstance(companies, str):
                    companies = [companies]

                query = f"""
                    SELECT user_id, username, company
                    FROM {DB_SCHEMA}.user_company
                    WHERE company = ANY($1::text[])
                """
                rows = await conn.fetch(query, companies)
            else:
                query = f"""
                    SELECT user_id, username, company
                    FROM {DB_SCHEMA}.user_company
                """
                rows = await conn.fetch(query)

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_users_by_ids(user_ids):
        """Получить пользователей по списку ID"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            query = f"""
                SELECT user_id, username, company
                FROM {DB_SCHEMA}.user_company
                WHERE user_id = ANY($1::bigint[])
            """
            rows = await conn.fetch(query, user_ids)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting users by ids: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_users_by_conference(conferences):
        """Получить пользователей по списку конференций"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            if isinstance(conferences, str):
                conferences = [conferences]

            query = f"""
                SELECT DISTINCT uc.user_id, uc.username, uc.company
                FROM {DB_SCHEMA}.user_company uc
                JOIN {DB_SCHEMA}.user_conferences uconf ON uc.username = uconf.username
                WHERE uconf.conference_name = ANY($1::text[])
            """
            rows = await conn.fetch(query, conferences)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting users by conference: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_companies():
        """Получить список компаний"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)
            query = f"""
                SELECT DISTINCT company
                FROM {DB_SCHEMA}.user_profiles
                WHERE company IS NOT NULL AND company != ''
                ORDER BY company
            """
            rows = await conn.fetch(query)
            return [row['company'] for row in rows]
        except Exception as e:
            print(f"Error getting companies: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_conferences():
        """Получить список активных конференций"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            # Пытаемся получить из user_conferences
            try:
                query = f"""
                    SELECT DISTINCT conference_name as name, 
                           COUNT(DISTINCT username) as user_count
                    FROM {DB_SCHEMA}.user_conferences
                    GROUP BY conference_name
                    ORDER BY conference_name
                """
                rows = await conn.fetch(query)
                if rows:
                    return [dict(row) for row in rows]
            except:
                pass

            # Fallback: получаем из company как конференции
            companies = await Database.get_companies()
            return [{'name': c, 'user_count': 0} for c in companies]
        except Exception as e:
            print(f"Error getting conferences: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_all_users():
        """Получить всех пользователей с деталями"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            query = f"""
                SELECT 
                    up.user_id,
                    up.username,
                    up.full_name,
                    up.company,
                    up.position,
                    up.language,
                    up.registered_at,
                    (SELECT MAX(timestamp) FROM {DB_SCHEMA}.user_logs WHERE user_id = up.user_id) as last_active,
                    (SELECT COUNT(*) FROM {DB_SCHEMA}.user_logs WHERE user_id = up.user_id AND timestamp > NOW() - INTERVAL '5 minutes') > 0 as is_online
                FROM {DB_SCHEMA}.user_profiles up
                ORDER BY up.registered_at DESC
            """
            rows = await conn.fetch(query)
            users = [dict(row) for row in rows]

            # Добавляем конференции и количество заявок для каждого пользователя
            for user in users:
                # Конференции пользователя
                conf_query = f"""
                    SELECT conference_name
                    FROM {DB_SCHEMA}.user_conferences
                    WHERE username = $1
                """
                conferences = await conn.fetch(conf_query, user['username'])
                user['conferences'] = [c['conference_name'] for c in conferences]

                # Количество заявок
                requests_count = 0
                for table in ['pr_banner_requests', 'pr_business_cards', 'event_certificates', 'travel_visa_requests']:
                    try:
                        count = await conn.fetchval(f"""
                            SELECT COUNT(*) FROM {DB_SCHEMA}.{table}
                            WHERE username = $1
                        """, user['username'])
                        requests_count += count
                    except:
                        pass
                user['requests_count'] = requests_count

            return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_user_details(user_id):
        """Получить детальную информацию о пользователе"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            # Основная информация
            user = await conn.fetchrow(f"""
                SELECT 
                    up.*,
                    (SELECT MAX(timestamp) FROM {DB_SCHEMA}.user_logs WHERE user_id = up.user_id) as last_active
                FROM {DB_SCHEMA}.user_profiles up
                WHERE up.user_id = $1
            """, user_id)

            if not user:
                return None

            result = dict(user)

            # Конференции пользователя
            conf_query = f"""
                SELECT conference_name
                FROM {DB_SCHEMA}.user_conferences
                WHERE username = $1
            """
            conferences = await conn.fetch(conf_query, result['username'])
            result['conferences'] = [c['conference_name'] for c in conferences]

            # Заявки пользователя
            requests = []
            request_tables = [
                ('pr_banner_requests', 'Баннер'),
                ('pr_business_cards', 'Визитки'),
                ('event_certificates', 'Справка'),
                ('travel_visa_requests', 'Виза')
            ]

            for table, type_name in request_tables:
                try:
                    rows = await conn.fetch(f"""
                        SELECT id, created_at, 'pending' as status
                        FROM {DB_SCHEMA}.{table}
                        WHERE username = $1
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, result['username'])
                    for row in rows:
                        requests.append({
                            'type': type_name,
                            'created_at': row['created_at'].strftime('%d.%m.%Y %H:%M'),
                            'status': 'pending'
                        })
                except:
                    pass

            result['requests'] = requests
            return result

        except Exception as e:
            print(f"Error getting user details: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_recent_broadcasts(limit=10):
        """Получить последние рассылки"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)
            query = f"""
                SELECT 
                    details->>'type' as broadcast_type,
                    details->>'company' as company,
                    details->>'message_length' as length,
                    details->>'success' as success_count,
                    details->>'failed' as failed_count,
                    timestamp
                FROM {DB_SCHEMA}.user_logs
                WHERE action = 'broadcast_sent'
                ORDER BY timestamp DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting broadcasts: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def get_stats():
        """Получить статистику"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            # Общая статистика
            total_users = await conn.fetchval(f"""
                SELECT COUNT(DISTINCT user_id) 
                FROM {DB_SCHEMA}.user_profiles
            """)

            active_today = await conn.fetchval(f"""
                SELECT COUNT(DISTINCT user_id)
                FROM {DB_SCHEMA}.user_logs
                WHERE timestamp > NOW() - INTERVAL '1 day'
            """)

            # По компаниям
            companies_stats = await conn.fetch(f"""
                SELECT company, COUNT(DISTINCT user_id) as user_count
                FROM {DB_SCHEMA}.user_profiles
                WHERE company IS NOT NULL
                GROUP BY company
                ORDER BY user_count DESC
                LIMIT 5
            """)

            # Заявки
            banner_requests = 0
            visa_requests = 0
            try:
                banner_requests = await conn.fetchval(f"SELECT COUNT(*) FROM {DB_SCHEMA}.pr_banner_requests") or 0
                visa_requests = await conn.fetchval(f"SELECT COUNT(*) FROM {DB_SCHEMA}.travel_visa_requests") or 0
            except:
                pass

            # Активные конференции
            active_conferences = await conn.fetchval(f"""
                SELECT COUNT(DISTINCT conference_name)
                FROM {DB_SCHEMA}.user_conferences
            """) or 0

            # Всего рассылок
            total_broadcasts = await conn.fetchval(f"""
                SELECT COUNT(*)
                FROM {DB_SCHEMA}.user_logs
                WHERE action = 'broadcast_sent'
            """) or 0

            return {
                'total_users': total_users or 0,
                'active_today': active_today or 0,
                'companies_stats': [dict(row) for row in companies_stats],
                'banner_requests': banner_requests,
                'visa_requests': visa_requests,
                'active_conferences': active_conferences,
                'total_broadcasts': total_broadcasts
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def log_broadcast(username, broadcast_type, company, success, failed, message_length, file_count=0):
        """Логировать рассылку"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)
            details = {
                'type': broadcast_type,
                'company': company,
                'success': success,
                'failed': failed,
                'message_length': message_length,
                'file_count': file_count
            }
            await conn.execute(f"""
                INSERT INTO {DB_SCHEMA}.user_logs (user_id, username, action, details)
                VALUES ($1, $2, $3, $4)
            """, 0, username, 'broadcast_sent', details)
            return True
        except Exception as e:
            print(f"Error logging broadcast: {e}")
            return False
        finally:
            if conn:
                await conn.close()


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
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            flash('Вы успешно вошли в систему!', 'success')
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
    """Главная панель"""
    # Получаем статистику
    stats = run_async(Database.get_stats())
    broadcasts = run_async(Database.get_recent_broadcasts(5))

    # Получаем активные конференции
    conferences = run_async(Database.get_conferences())
    active_conferences = conferences[:5] if conferences else []

    # Получаем недавно активных пользователей
    users = run_async(Database.get_all_users())
    recent_users = sorted(users,
                          key=lambda x: x.get('last_active') or datetime.min,
                          reverse=True)[:5]

    return render_template('dashboard.html',
                           stats=stats,
                           broadcasts=broadcasts,
                           active_conferences=active_conferences,
                           recent_users=recent_users,
                           username=session.get('username'))


@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    """Страница рассылки"""
    companies = run_async(Database.get_companies())
    conferences = run_async(Database.get_conferences())
    users = run_async(Database.get_all_users())

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
            users_to_send = run_async(Database.get_users_by_company())
        elif target_type == 'company':
            companies_selected = request.form.getlist('companies')
            if not companies_selected:
                flash('Выберите хотя бы одну компанию', 'danger')
                return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)
            users_to_send = run_async(Database.get_users_by_company(companies_selected))
        elif target_type == 'specific':
            user_ids = request.form.getlist('selected_users')
            if not user_ids:
                flash('Выберите хотя бы одного пользователя', 'danger')
                return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)
            user_ids = [int(uid) for uid in user_ids]
            users_to_send = run_async(Database.get_users_by_ids(user_ids))
        elif target_type == 'conference':
            conferences_selected = request.form.getlist('conferences')
            if not conferences_selected:
                flash('Выберите хотя бы одну конференцию', 'danger')
                return render_template('broadcast.html', companies=companies, conferences=conferences, users=users)
            users_to_send = run_async(Database.get_users_by_conference(conferences_selected))

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
        run_async(Database.log_broadcast(
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
    conferences = run_async(Database.get_conferences())
    stats = {
        'total_conferences': len(conferences),
        'active_conferences': len([c for c in conferences if c.get('user_count', 0) > 0]),
        'upcoming_conferences': 0,  # TODO: добавить логику
        'total_participants': sum(c.get('user_count', 0) for c in conferences)
    }

    return render_template('conferences.html',
                           conferences=conferences,
                           stats=stats,
                           username=session.get('username'))


@app.route('/users')
@login_required
def users_page():
    """Страница активных пользователей"""
    users = run_async(Database.get_all_users())
    companies = run_async(Database.get_companies())
    conferences = run_async(Database.get_conferences())

    # Статистика
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


# ============================================
# API МАРШРУТЫ
# ============================================

@app.route('/api/users/count')
@login_required
def api_users_count():
    """API для подсчета пользователей по фильтрам"""
    companies = request.args.get('companies', '').split(',')
    conferences = request.args.get('conferences', '').split(',')

    if companies and companies[0]:
        users = run_async(Database.get_users_by_company(companies))
    elif conferences and conferences[0]:
        users = run_async(Database.get_users_by_conference(conferences))
    else:
        users = run_async(Database.get_users_by_company())

    return jsonify({'count': len(users)})


@app.route('/api/users/<int:user_id>')
@login_required
def api_user_details(user_id):
    """API для получения деталей пользователя"""
    user = run_async(Database.get_user_details(user_id))
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/users/export')
@login_required
def api_export_users():
    """Экспорт пользователей в CSV"""
    users = run_async(Database.get_all_users())

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


@app.route('/api/conferences/<path:conference_name>')
@login_required
def api_conference_details(conference_name):
    """API для получения деталей конференции"""
    # TODO: реализовать получение деталей конференции
    return jsonify({
        'name': conference_name,
        'city': 'Москва',
        'start_date': '2024-11-15',
        'end_date': '2024-11-17',
        'user_count': 0,
        'users': []
    })


@app.route('/api/conferences/add', methods=['POST'])
@login_required
def api_add_conference():
    """API для добавления конференции"""
    # TODO: реализовать добавление конференции
    flash('Конференция добавлена', 'success')
    return redirect(url_for('conferences_page'))


@app.route('/api/conferences/delete/<path:conference_name>', methods=['POST'])
@login_required
def api_delete_conference(conference_name):
    """API для удаления конференции"""
    # TODO: реализовать удаление конференции
    return jsonify({'success': True})


@app.route('/api/users/preview')
@login_required
def api_preview_recipients():
    """API для предпросмотра получателей"""
    # TODO: реализовать предпросмотр
    return jsonify({'count': 0})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)