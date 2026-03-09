from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import asyncio
import os
from datetime import datetime, timedelta
import secrets
import hashlib
import asyncpg
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

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
    async def get_users_by_company(company=None):
        """Получить пользователей из таблицы user_company"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)

            if company and company != 'all':
                query = f"""
                    SELECT user_id, username, company
                    FROM {DB_SCHEMA}.user_company
                    WHERE company = $1
                """
                rows = await conn.fetch(query, company)
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
    async def get_companies():
        """Получить список компаний из user_company"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)
            query = f"""
                SELECT DISTINCT company
                FROM {DB_SCHEMA}.user_profiles
                WHERE company IS NOT NULL
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
            total_users = await conn.fetchval(
                "SELECT COUNT(DISTINCT user_id) FROM travelconference_bot.user_logs WHERE user_id IS NOT NULL")

            active_today = await conn.fetchval("""
                                               SELECT COUNT(DISTINCT user_id)
                                               FROM travelconference_bot.user_logs
                                               WHERE timestamp > NOW() - INTERVAL '1 day'
                                               """)

            # По компаниям
            companies_stats = await conn.fetch("""
                                               SELECT company, COUNT(DISTINCT user_id) as user_count
                                               FROM travelconference_bot.user_logs
                                               WHERE company IS NOT NULL
                                               GROUP BY company
                                               ORDER BY user_count DESC
                                               LIMIT 5
                                               """)

            # Заявки
            banner_requests = await conn.fetchval("SELECT COUNT(*) FROM travelconference_bot.pr_banner_requests")
            visa_requests = await conn.fetchval("SELECT COUNT(*) FROM travelconference_bot.travel_visa_requests")

            return {
                'total_users': total_users or 0,
                'active_today': active_today or 0,
                'companies_stats': [dict(row) for row in companies_stats],
                'banner_requests': banner_requests or 0,
                'visa_requests': visa_requests or 0
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
        finally:
            if conn:
                await conn.close()

    @staticmethod
    async def log_broadcast(username, broadcast_type, company, success, failed, message_length):
        """Логировать рассылку"""
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)
            details = {
                'type': broadcast_type,
                'company': company,
                'success': success,
                'failed': failed,
                'message_length': message_length
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

    async def send_message(self, chat_id, text):
        """Отправить сообщение через Telegram API"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
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

    async def broadcast_to_users(self, users, message):
        """Массовая рассылка пользователям"""
        results = {'success': 0, 'failed': 0}

        for user in users:
            user_id = user.get('user_id')
            if not user_id:
                results['failed'] += 1
                continue

            success = await self.send_message(user_id, message)
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

            # Небольшая задержка чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.05)

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

    return render_template('dashboard.html',
                           stats=stats,
                           broadcasts=broadcasts,
                           username=session.get('username'))


@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    """Страница рассылки"""
    companies = run_async(Database.get_companies())

    if request.method == 'POST':
        message = request.form.get('message')
        target_type = request.form.get('target_type', 'all')
        company = request.form.get('company') if target_type == 'company' else None

        if not message:
            flash('Введите сообщение для рассылки', 'danger')
            return render_template('broadcast.html', companies=companies)

        if len(message) > 4000:
            flash('Сообщение слишком длинное (макс. 4000 символов)', 'danger')
            return render_template('broadcast.html', companies=companies)

        # Получаем пользователей
        users = run_async(Database.get_users_by_company(company))

        if not users:
            flash('Нет пользователей для рассылки', 'warning')
            return render_template('broadcast.html', companies=companies)

        # Отправляем сообщения
        results = run_async(bot.broadcast_to_users(users, message))

        # Логируем рассылку
        run_async(Database.log_broadcast(
            username=session.get('username', 'admin'),
            broadcast_type=target_type,
            company=company or 'all',
            success=results['success'],
            failed=results['failed'],
            message_length=len(message)
        ))

        flash(f'Рассылка завершена! Успешно: {results["success"]}, Ошибок: {results["failed"]}', 'success')
        return redirect(url_for('dashboard'))

    return render_template('broadcast.html', companies=companies)


@app.route('/api/users', methods=['GET'])
@login_required
def api_users():
    """API для получения списка пользователей"""
    company = request.args.get('company')
    users = run_async(Database.get_users_by_company(company))
    return jsonify({'users': users, 'count': len(users)})


@app.route('/api/stats', methods=['GET'])
@login_required
def api_stats():
    """API для получения статистики"""
    stats = run_async(Database.get_stats())
    return jsonify(stats)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)