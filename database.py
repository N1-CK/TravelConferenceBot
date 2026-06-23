import logging
import os
from typing import List, Dict

import asyncpg
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'pool'):
            self.pool = None
            self.db_schema = os.getenv('DB_SCHEMA', 'travelconference_bot')
            self.db_schema_config = os.getenv('DB_SCHEMA_CONFIG', 'travelconference_config')
            self.db_schema_travel = os.getenv('DB_SCHEMA_TRAVEL', 'travelconference_travel')
            self.db_schema_pr = os.getenv('DB_SCHEMA_PR', 'travelconference_pr')
            self.db_schema_event = os.getenv('DB_SCHEMA_EVENT', 'travelconference_event')
            self.db_schema_admin = os.getenv('DB_SCHEMA_ADMIN', 'travelconference_admin')

    async def create_pool(self):
        """Создание пула подключений"""
        try:
            self.pool = await asyncpg.create_pool(
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME')
            )

            await self.create_all_tables()
            logger.info("Database pool created with all tables")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    async def create_all_tables(self):
        """Создаем все таблицы для обоих ботов"""
        try:
            async with self.pool.acquire() as conn:
                # Существующие таблицы Conference Bot
                tables = [
                    f'''
                        CREATE SCHEMA IF NOT EXISTS systemcheck_bot;
                    ''',
                    f'''
                        CREATE SCHEMA IF NOT EXISTS {self.db_schema};
                    ''',
                    f'''
                        CREATE SCHEMA IF NOT EXISTS {self.db_schema_config};
                    ''',
                    f'''
                        CREATE SCHEMA IF NOT EXISTS {self.db_schema_admin};
                    ''',
                    f'''
                        CREATE SCHEMA IF NOT EXISTS {self.db_schema_travel};
                    ''',
                    f'''
                        CREATE SCHEMA IF NOT EXISTS {self.db_schema_event};
                    ''',
                    f'''
                        CREATE SCHEMA IF NOT EXISTS {self.db_schema_pr};
                    ''',

                    # Белый список
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_config}.whitelist (
                        username TEXT PRIMARY KEY,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Список всех компаний
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.db_schema_config}.companies (
                            id SERIAL PRIMARY KEY,
                            company_name TEXT UNIQUE NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """),

                    f"""
                        CREATE TABLE IF NOT EXISTS {self.db_schema_config}.conferences (
                            id SERIAL PRIMARY KEY,
                            conference_name TEXT UNIQUE NOT NULL,
                            start_date TEXT,
                            end_date TEXT,
                            city TEXT,
                            bot_link TEXT,
                            additional_info TEXT,
                            sheet_name TEXT,
                            hotel TEXT,
                            hotel_address TEXT,
                            site_url TEXT,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """,

                    f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_config}.user_profiles (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT NOT NULL,
                        language TEXT DEFAULT 'en',
                        full_name TEXT,
                        position TEXT,
                        company TEXT,
                        selected_conference TEXT,
                        registered_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    """,

                    # User logs
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_logs (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        company TEXT,
                        action TEXT,
                        details JSONB,
                        timestamp TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # PR таблицы
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_pr}.pr_banner_requests (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        full_name TEXT,
                        position TEXT,
                        company TEXT,
                        language TEXT,
                        photo_required BOOLEAN,
                        photo_file_id TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        comments TEXT DEFAULT ''
                    )
                    ''',

                    # TRAVEL таблицы
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_travel}.travel_flight_request (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        visa_status TEXT,
                        passport_data TEXT,
                        city_from TEXT,
                        city_to TEXT,
                        needs_baggage BOOLEAN,
                        preferences TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # ===== ТАБЛИЦЫ AFFILIATE BOT =====

                    # Auth users (объединяем с whitelist)
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.affiliate_auth_users (
                        username TEXT PRIMARY KEY REFERENCES {self.db_schema_config}.whitelist(username),
                        flag BOOLEAN DEFAULT TRUE,
                        company TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Рестораны
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_pr}.affil_restaurants (
                        id SERIAL PRIMARY KEY,
                        city TEXT,
                        conference TEXT,
                        restaurant TEXT,
                        address TEXT,
                        cost TEXT,
                        link TEXT,
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Бронирования
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_pr}.affil_bookings (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        user_id BIGINT NOT NULL,
                        manager TEXT NOT NULL,
                        datetime TEXT NOT NULL,
                        company TEXT NOT NULL,
                        partner TEXT NOT NULL,
                        restaurant TEXT NOT NULL,
                        people TEXT NOT NULL,
                        payment_method TEXT NOT NULL,
                        partnertype TEXT NOT NULL,
                        status TEXT DEFAULT 'confirmed',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Отчеты
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_pr}.affil_reports (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        company TEXT NOT NULL,
                        meeting_date TEXT NOT NULL,
                        manager TEXT NOT NULL,
                        partner TEXT NOT NULL,
                        result TEXT,
                        budget TEXT DEFAULT '0',
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # После существующих таблиц добавить:

                    # Вопросы к EVENT
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_event}.event_questions (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        category TEXT,
                        question TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_event}.event_stands (
                        id SERIAL PRIMARY KEY,
                        company TEXT NOT NULL,
                        conference TEXT NOT NULL,
                        stand_style TEXT,
                        stand_number TEXT,
                        working_hours TEXT,
                        dress_code TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(company, conference)
                    )
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_event}.event_ticket_requests (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        full_name TEXT,
                        position TEXT,
                        company TEXT,
                        email TEXT,
                        phone TEXT,
                        country TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Вопросы к PR
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_pr}.pr_questions (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        category TEXT,
                        question TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_pr}.pr_business_cards (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        full_name TEXT,
                        position_en TEXT,
                        company TEXT,
                        contacts TEXT,
                        brand_style BOOLEAN DEFAULT FALSE,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Вопросы к Travel
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_travel}.travel_questions (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        category TEXT,
                        question TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    f'''
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.user_flights (
                                    id SERIAL PRIMARY KEY,
                                    username TEXT NOT NULL,
                                    conference TEXT NOT NULL,
                                    flight_number TEXT,
                                    book_number TEXT,
                                    departure_from TEXT,
                                    arrival_city TEXT,
                                    departure_date TEXT,
                                    departure_time TEXT,
                                    arrival_time TEXT,
                                    airline TEXT,
                                    luggage TEXT,
                                    carry_luggage TEXT,
                                    created_at TIMESTAMP DEFAULT NOW()
                                )
                                ''',


                    f'''
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.airlines (
                                    id SERIAL PRIMARY KEY,
                                    airline_name TEXT UNIQUE NOT NULL,
                                    checkin_url TEXT,
                                    created_at TIMESTAMP DEFAULT NOW()
                                )
                                ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_agreements (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT NOT NULL,
                        agreement_type TEXT NOT NULL DEFAULT 'terms',
                        version TEXT NOT NULL,
                        accepted_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(user_id, agreement_type)
                    )
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_conferences (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        conference_name TEXT NOT NULL,
                        trip_start_date TEXT,
                        trip_end_date TEXT,
                        conference_start_date TEXT,
                        conference_end_date TEXT,
                        city TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(username, conference_name)
                    )
                    ''',


                    f'''
                    CREATE TABLE IF NOT EXISTS systemcheck_bot.bots_status (
                        bot_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        components JSONB,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    '''
                ]

                await conn.execute(f"""
                                CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.admin_users (
                                    id SERIAL PRIMARY KEY,
                                    username TEXT UNIQUE NOT NULL,
                                    password_hash TEXT NOT NULL,
                                    full_name TEXT,
                                    role TEXT NOT NULL DEFAULT 'user',
                                    can_manage_users BOOLEAN DEFAULT FALSE,
                                    can_broadcast BOOLEAN DEFAULT TRUE,
                                    can_view_stats BOOLEAN DEFAULT TRUE,
                                    can_manage_conferences BOOLEAN DEFAULT FALSE,
                                    created_at TIMESTAMP DEFAULT NOW(),
                                    last_login TIMESTAMP,
                                    is_active BOOLEAN DEFAULT TRUE
                                )
                            """)


                # Таблица сессий админки
                await conn.execute(f"""
                                CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.admin_sessions (
                                    id SERIAL PRIMARY KEY,
                                    admin_id INTEGER REFERENCES {self.db_schema_admin}.admin_users(id),
                                    session_token TEXT UNIQUE,
                                    ip_address TEXT,
                                    user_agent TEXT,
                                    created_at TIMESTAMP DEFAULT NOW(),
                                    expires_at TIMESTAMP
                                )
                            """)

                # Таблица логов действий админов
                await conn.execute(f"""
                                CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.admin_logs (
                                    id SERIAL PRIMARY KEY,
                                    admin_id INTEGER REFERENCES {self.db_schema_admin}.admin_users(id),
                                    action TEXT NOT NULL,
                                    details JSONB,
                                    ip_address TEXT,
                                    created_at TIMESTAMP DEFAULT NOW()
                                )
                            """)

                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_messages (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT NOT NULL,
                        manager_id INTEGER,
                        direction TEXT NOT NULL, -- 'incoming' or 'outgoing'
                        message_text TEXT,
                        file_type TEXT,
                        file_id TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        read_at TIMESTAMP,
                        replied_at TIMESTAMP
                    )
                """)

                # Индексы для быстрого поиска
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_user_messages_user_id 
                    ON {self.db_schema}.user_messages(user_id)
                """)
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_user_messages_created_at 
                    ON {self.db_schema}.user_messages(created_at)
                """)

                # Создаем первого админа если нет
                from hashlib import sha256
                default_admin = os.getenv('ADMIN_USERNAME', 'admin')
                default_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
                password_hash = sha256(default_pass.encode()).hexdigest()

                await conn.execute(f"""
                                INSERT INTO {self.db_schema_admin}.admin_users 
                                (username, password_hash, full_name, role, can_manage_users, can_broadcast, can_view_stats, can_manage_conferences)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                                ON CONFLICT (username) DO NOTHING
                            """, default_admin, password_hash, 'Administrator', 'admin', True, True, True, True)

                for table_sql in tables:
                    try:
                        await conn.execute(table_sql)
                    except Exception as e:
                        logger.warning(f"Table might already exist: {e}")

                logger.info("All tables created successfully")
                return True

        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False

    # ===== AFFILIATE BOT МЕТОДЫ =====

    async def add_affiliate_user(self, username: str, company: str) -> bool:
        """Добавление пользователя Affiliate Bot"""
        try:
            async with self.pool.acquire() as conn:
                # Добавляем в whitelist
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_config}.whitelist (username, is_active)
                    VALUES ($1, TRUE)
                    ON CONFLICT (username) DO UPDATE
                    SET is_active = TRUE
                """, username)

                return True
        except Exception as e:
            logger.error(f"Error adding affiliate user: {e}")
            return False


    async def get_cities_from_restaurants(self) -> list:
        """Получение списка городов из ресторанов"""
        try:
            async with self.pool.acquire() as conn:
                records = await conn.fetch(f"""
                    select city
                    from (
                        SELECT distinct max(id) as idd, city
                        FROM {self.db_schema_pr}.affil_restaurants
                        WHERE created_at = (select max(created_at) from {self.db_schema_pr}.affil_restaurants)
                        group by city) t1
                """)
                print(records)
                return [record['city'] for record in records]
        except Exception as e:
            logger.error(f"Error getting cities: {e}")
            return []

    async def check_duplicate_booking(self, username: str, datetime_str: str, partner: str) -> bool:
        """Проверка на дубликат бронирования"""
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(
                    f"""
                    SELECT COUNT(*) FROM {self.db_schema_pr}.affil_bookings 
                    WHERE username = $1 AND datetime = $2 AND partner = $3
                    """,
                    username, datetime_str, partner
                )
                return count > 0
        except Exception as e:
            logger.error(f"Error checking duplicate booking: {e}")
            return False

    async def get_all_ticket_requests(self) -> list:
        """Получить все заявки на билеты"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_event}.event_ticket_requests 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting ticket requests: {e}")
            return []

    async def update_ticket_request_status(self, request_id: int, status: str) -> bool:
        """Обновить статус заявки на билет"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema_event}.event_ticket_requests 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating ticket request status: {e}")
            return False

    async def get_question_by_id(self, table_name: str, question_id: int) -> dict:
        """Получить вопрос по ID из указанной таблицы"""
        try:
            async with self.pool.acquire() as conn:
                # table_name уже содержит полное имя таблицы (например travelconference_pr.pr_questions)
                query = f'SELECT * FROM {table_name} WHERE id = $1'
                row = await conn.fetchrow(query, question_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting question by id from {table_name}: {e}")
            return {}

    async def save_forwarded_question(self, target_table: str, question_data: dict) -> bool:
        """Сохранить пересланный вопрос в целевую таблицу"""
        try:
            async with self.pool.acquire() as conn:
                # target_table уже содержит полное имя таблицы
                query = f"""
                    INSERT INTO {target_table} 
                    (username, user_id, category, question, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """
                await conn.execute(
                    query,
                    question_data.get('username'),
                    question_data.get('user_id'),
                    question_data.get('category'),
                    question_data.get('question'),
                    question_data.get('created_at')
                )
                return True
        except Exception as e:
            logger.error(f"Error saving forwarded question: {e}")
            return False

    async def get_ticket_request_stats(self) -> dict:
        """Получить статистику по заявкам на билеты"""
        try:
            async with self.pool.acquire() as conn:
                total = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests
                """) or 0
                pending = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE status = 'pending'
                """) or 0
                in_progress = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE status = 'in_progress'
                """) or 0
                ready = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE status = 'ready'
                """) or 0

                return {
                    'total': total,
                    'pending': pending,
                    'in_progress': in_progress,
                    'ready': ready
                }
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            return {'total': 0, 'pending': 0, 'in_progress': 0, 'ready': 0}

    async def get_restaurants_by_city(self, city: str) -> list:
        """Получение ресторанов по городу"""
        try:
            async with self.pool.acquire() as conn:
                records = await conn.fetch(f"""
                    SELECT id, restaurant, address, cost, link, comment
                    FROM {self.db_schema_pr}.affil_restaurants
                    WHERE city = $1 
                    AND created_at = (
                        SELECT MAX(created_at) FROM {self.db_schema_pr}.affil_restaurants
                    )
                    ORDER BY restaurant
                """, city)
                return records
        except Exception as e:
            logger.error(f"Error getting restaurants: {e}")
            return []

    async def get_restaurant_by_id(self, rest_id: int):
        """Получение информации о ресторане по ID"""
        try:
            async with self.pool.acquire() as conn:
                record = await conn.fetchrow(f"""
                    SELECT city, restaurant, address, cost, link, comment
                    FROM {self.db_schema_pr}.affil_restaurants
                    WHERE id = $1
                """, rest_id)
                return record
        except Exception as e:
            logger.error(f"Error getting restaurant: {e}")
            return None


    async def save_event_question(self, data: dict) -> bool:
        """Сохранение вопроса к EVENT-менеджеру"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_event}.event_questions 
                    (username, user_id, category, question)
                    VALUES ($1, $2, $3, $4)
                """,
                                   data['username'],
                                   data['user_id'],
                                   data.get('category', ''),
                                   data.get('question', '')
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving event question: {e}")
            return False

    async def get_event_stand(self, company: str, conference: str) -> dict:
        """Получить информацию о стенде компании на конференции"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT stand_style, stand_number, working_hours, dress_code 
                    FROM {self.db_schema_event}.event_stands 
                    WHERE company = $1 AND conference = $2
                """, company, conference)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting event stand: {e}")
            return None

    async def save_visa_request(self, data: dict) -> bool:
        """Сохранение заявки на визу"""
        try:
            async with self.pool.acquire() as conn:
                # Добавляем колонку status если нет
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS visa_request_status TEXT DEFAULT 'pending'
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS flight_request_status TEXT DEFAULT 'pending'
                    """)
                except:
                    pass

                await conn.execute(f"""
                    INSERT INTO {self.db_schema_travel}.travel_flight_request 
                    (username, user_id, visa_status, passport_data, city_from, city_to, needs_baggage, preferences, 
                     visa_request_status, flight_request_status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', 'pending')
                """,
                                   data['username'],
                                   data['user_id'],
                                   data.get('visa_status', ''),
                                   data.get('passport_data', ''),
                                   data.get('city_from', ''),
                                   data.get('city_to', ''),
                                   data.get('needs_baggage', False),
                                   data.get('preferences', '')
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving visa request: {e}")
            return False

    async def save_per_diem_request(self, data: dict) -> bool:
        """Сохранение заявки на суточные"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем таблицу с правильной структурой если её нет
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_travel}.travel_per_diem_requests (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        user_id BIGINT NOT NULL,
                        payment_type TEXT,
                        payment_details TEXT,
                        status TEXT DEFAULT 'pending',
                        consent_given BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Добавляем колонку payment_type если её нет
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_per_diem_requests 
                        ADD COLUMN IF NOT EXISTS payment_type TEXT
                    """)
                except:
                    pass

                # Добавляем колонку status если её нет
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_per_diem_requests 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'
                    """)
                except:
                    pass

                # Добавляем колонку updated_at если её нет
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_per_diem_requests 
                        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()
                    """)
                except:
                    pass

                # Вставляем данные
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_travel}.travel_per_diem_requests 
                    (username, user_id, payment_type, payment_details, consent_given, status)
                    VALUES ($1, $2, $3, $4, $5, 'pending')
                """,
                                   data['username'],
                                   data['user_id'],
                                   data.get('payment_type', ''),
                                   data.get('payment_details', ''),
                                   data.get('consent_given', False)
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving per diem request: {e}")
            return False

    # database.py - добавьте этот метод в класс Database

    async def get_questions_by_department(self, department: str, limit: int = 100) -> list:
        """Получить вопросы для конкретного отдела"""
        try:
            async with self.pool.acquire() as conn:
                tables = {
                    'pr': f'{self.db_schema_pr}.pr_questions',
                    'event': f'{self.db_schema_event}.event_questions',
                    'travel': f'{self.db_schema_travel}.travel_questions'
                }

                table = tables.get(department)
                if not table:
                    return []

                rows = await conn.fetch(f"""
                    SELECT * FROM {table}
                    ORDER BY created_at DESC
                    LIMIT $1
                """, limit)

                result = []
                for row in rows:
                    item = dict(row)
                    item['department'] = department
                    result.append(item)

                return result
        except Exception as e:
            logger.error(f"Error getting questions for {department}: {e}")
            return []

    async def get_all_per_diem_requests(self) -> list:
        """Получить все заявки на суточные"""
        try:
            async with self.pool.acquire() as conn:
                # Сначала убедимся, что таблица имеет правильную структуру
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_per_diem_requests 
                        ADD COLUMN IF NOT EXISTS payment_type TEXT
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_per_diem_requests 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_per_diem_requests 
                        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()
                    """)
                except Exception as e:
                    logger.warning(f"Error adding columns to per_diem table: {e}")

                # Обновляем старые записи, у которых нет payment_type
                try:
                    await conn.execute(f"""
                        UPDATE {self.db_schema_travel}.travel_per_diem_requests 
                        SET payment_type = 'card' 
                        WHERE payment_type IS NULL AND payment_details IS NOT NULL
                    """)
                except:
                    pass

                # Обновляем статус для старых записей
                try:
                    await conn.execute(f"""
                        UPDATE {self.db_schema_travel}.travel_per_diem_requests 
                        SET status = 'pending' 
                        WHERE status IS NULL
                    """)
                except:
                    pass

                rows = await conn.fetch(f"""
                    SELECT 
                        id, 
                        username, 
                        user_id, 
                        COALESCE(payment_type, 'card') as payment_type,
                        payment_details, 
                        COALESCE(status, 'pending') as status,
                        consent_given,
                        created_at,
                        updated_at
                    FROM {self.db_schema_travel}.travel_per_diem_requests 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting per diem requests: {e}")
            return []

    async def update_per_diem_status(self, request_id: int, status: str) -> bool:
        """Обновить статус заявки на суточные"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema_travel}.travel_per_diem_requests 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating per diem status: {e}")
            return False

    # database.py - Добавьте эти методы в класс Database

    async def get_all_travel_flight_requests(self) -> list:
        """Получить все заявки на билеты из travel_flight_request"""
        try:
            async with self.pool.acquire() as conn:
                # Убедимся, что нужные колонки существуют
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS visa_request_status TEXT DEFAULT 'pending'
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS flight_request_status TEXT DEFAULT 'pending'
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS first_name TEXT
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS last_name TEXT
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS phone TEXT
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS departure_from TEXT
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS return_to TEXT
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS hotel_needed BOOLEAN DEFAULT FALSE
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()
                    """)
                except Exception as e:
                    logger.warning(f"Error adding columns: {e}")

                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_travel}.travel_flight_request 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting travel flight requests: {e}")
            return []

    async def get_travel_flight_request_by_id(self, request_id: int) -> dict:
        """Получить заявку на билет по ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT * FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE id = $1
                """, request_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting travel flight request {request_id}: {e}")
            return {}

    async def update_travel_visa_request_status(self, request_id: int, status: str) -> bool:
        """Обновить статус визовой заявки"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema_travel}.travel_flight_request 
                    SET visa_request_status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating travel visa status: {e}")
            return False

    async def update_travel_flight_request_status(self, request_id: int, status: str) -> bool:
        """Обновить статус заявки на билет"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema_travel}.travel_flight_request 
                    SET flight_request_status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating travel flight status: {e}")
            return False

    async def get_travel_stats(self) -> dict:
        """Получить статистику для Travel панели"""
        try:
            async with self.pool.acquire() as conn:
                total_requests = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request
                """) or 0

                visa_pending = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE visa_request_status = 'pending'
                """) or 0

                flight_pending = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE flight_request_status = 'pending'
                """) or 0

                flight_purchased = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE flight_request_status = 'purchased'
                """) or 0

                return {
                    'total_requests': total_requests,
                    'visa_pending': visa_pending,
                    'flight_pending': flight_pending,
                    'flight_purchased': flight_purchased
                }
        except Exception as e:
            logger.error(f"Error getting travel stats: {e}")
            return {'total_requests': 0, 'visa_pending': 0, 'flight_pending': 0, 'flight_purchased': 0}

    async def save_banner_request(self, data: dict) -> bool:
        """Сохранение заявки на баннер"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_pr}.pr_banner_requests 
                    (username, user_id, full_name, position, company, language, photo_required, photo_file_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                                   data['username'],
                                   data['user_id'],
                                   data.get('full_name', ''),
                                   data.get('position', ''),
                                   data.get('company', ''),
                                   data.get('language', ''),
                                   data.get('photo_required', False),
                                   data.get('photo_file_id', '')
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving banner request: {e}")
            return False

    async def save_business_cards_request(self, data: dict) -> bool:
        """Сохранение заявки на визитки"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_pr}.pr_business_cards 
                    (username, user_id, full_name, position_en, company, contacts, brand_style)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                                   data['username'],
                                   data['user_id'],
                                   data.get('full_name', ''),
                                   data.get('position_en', ''),
                                   data.get('company', ''),
                                   data.get('contacts', ''),
                                   data.get('brand_style', False)
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving business cards: {e}")
            return False

    # Методы для бронирований
    async def save_booking(self, booking_data: dict) -> bool:
        """Сохранение бронирования"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_pr}.affil_bookings 
                    (username, user_id, manager, datetime, company, partner, 
                     restaurant, people, payment_method, partnertype)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                                   booking_data['username'],
                                   booking_data['user_id'],
                                   booking_data['manager'],
                                   booking_data['datetime'],
                                   booking_data['company'],
                                   booking_data['partner'],
                                   booking_data['restaurant'],
                                   booking_data['people'],
                                   booking_data['payment_method'],
                                   booking_data['partnertype'])
                return True
        except Exception as e:
            logger.error(f"Error saving booking: {e}")
            return False

    async def get_user_bookings(self, username: str) -> list:
        """Получить бронирования пользователя"""
        try:
            async with self.pool.acquire() as conn:
                records = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_pr}.affil_bookings 
                    WHERE username = $1 
                    ORDER BY created_at DESC
                """, username)
                return records
        except Exception as e:
            logger.error(f"Error getting bookings: {e}")
            return []

    async def save_pr_question(self, data: dict) -> tuple:
        """Сохранение вопроса и возврат ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    INSERT INTO {self.db_schema_pr}.pr_questions 
                    (username, user_id, category, question)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, data['username'], data['user_id'],
                                          data.get('category', ''), data.get('question', ''))
                return True, row['id'] if row else None
        except Exception as e:
            logger.error(f"Error saving PR question: {e}")
            return False, None

    async def save_travel_question(self, data: dict) -> bool:
        """Сохранение вопроса к тревел-менеджеру"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_travel}.travel_questions 
                    (username, user_id, category, question)
                    VALUES ($1, $2, $3, $4)
                """,
                                   data['username'],
                                   data['user_id'],
                                   data.get('category', ''),
                                   data.get('question', '')
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving travel question: {e}")
            return False

    # В класс Database добавить методы:

    async def check_user_agreement(self, user_id: int, agreement_type: str = 'terms') -> bool:
        """Проверяем, давал ли пользователь согласие"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    f"""
                    SELECT 1 FROM {self.db_schema}.user_agreements 
                    WHERE user_id = $1 AND agreement_type = $2
                    LIMIT 1
                    """,
                    user_id, agreement_type
                )
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking user agreement: {e}")
            return False

    async def save_user_agreement(self, user_id: int, username: str,
                                  version: str, agreement_type: str = 'terms') -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_agreements 
                    (user_id, username, agreement_type, version)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, agreement_type) DO UPDATE
                    SET version = EXCLUDED.version,
                        accepted_at = NOW()
                """, user_id, username, agreement_type, version)

                # Только username, без telegram_id и company
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_config}.whitelist (username, is_active)
                    VALUES ($1, TRUE)
                    ON CONFLICT (username) DO UPDATE
                    SET is_active = TRUE
                """, username)

                return True
        except Exception as e:
            logger.error(f"Error saving user agreement: {e}")
            return False

    async def save_ticket_request(self, data: dict) -> tuple:
        """Сохранение заявки на билет и возврат ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    INSERT INTO {self.db_schema_event}.event_ticket_requests 
                    (username, user_id, full_name, position, company, email, phone, country, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
                    RETURNING id
                """,
                                          data['username'],
                                          data['user_id'],
                                          data.get('full_name', ''),
                                          data.get('position', ''),
                                          data.get('company', ''),
                                          data.get('email', ''),
                                          data.get('phone', ''),
                                          data.get('country', '')
                                          )
                return True, row['id'] if row else None
        except Exception as e:
            logger.error(f"Error saving ticket request: {e}")
            return False, None

    async def save_user_language(self, user_id: int, username: str, language: str) -> bool:
        """Сохранить язык пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_config}.user_profiles (user_id, username, language, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (user_id) 
                    DO UPDATE SET language = EXCLUDED.language, updated_at = NOW()
                """, user_id, username, language)
            return True
        except Exception as e:
            logger.error(f"Error saving user language: {e}")
            return False

    async def save_flight_request(self, flight_data: Dict) -> bool:
        """Save flight request to database"""
        try:
            async with self.pool.acquire() as conn:
                # Проверяем, есть ли колонка status, если нет - добавляем
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'
                    """)
                except:
                    pass

                query = f"""
                    INSERT INTO {self.db_schema_travel}.travel_flight_request 
                    (username, user_id, visa_status, passport_data, city_from, city_to, needs_baggage, preferences, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
                """
                await conn.execute(
                    query,
                    flight_data['username'],
                    flight_data['user_id'],
                    flight_data.get('visa_status', 'not_have'),
                    flight_data.get('passport_data', ''),
                    flight_data.get('city_from', ''),
                    flight_data.get('city_to', ''),
                    flight_data.get('needs_baggage', False),
                    flight_data.get('preferences', '')
                )
                return True
        except Exception as e:
            logger.error(f"Error saving flight request: {e}")
            return False

    # Методы для отчетов
    async def save_report(self, report_data: dict) -> bool:
        """Сохранение отчета"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_pr}.affil_reports 
                    (username, company, meeting_date, manager, partner, result, budget)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                                   report_data['username'],
                                   report_data['company'],
                                   report_data['meeting_date'],
                                   report_data['manager'],
                                   report_data['partner'],
                                   report_data['result'],
                                   report_data['budget'])
                return True
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            return False


    async def sync_flights_data(self, flights_data: list):
        """Синхронизация данных о рейсах"""
        try:
            async with self.pool.acquire() as conn:
                # Удаляем старые данные для пользователей
                usernames = list(set([f['username'] for f in flights_data]))
                for username in usernames:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema}.user_flights 
                        WHERE username = $1
                    """, username)

                # Вставляем новые данные
                for flight in flights_data:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema}.user_flights 
                        (username, conference, flight_number, book_number, 
                         departure_from, arrival_city, departure_date, departure_time, 
                         arrival_time, airline, luggage, carry_luggage)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                                       flight['username'], flight['conference'], flight['flight_number'],
                                       flight['book_number'], flight['departure_from'], flight['arrival_city'],
                                       flight['departure_date'], flight['departure_time'], flight['arrival_time'],
                                       flight['airline'], flight['luggage'], flight['carry_luggage'])

                return True
        except Exception as e:
            logger.error(f"Error syncing flights data: {e}")
            return False


    async def check_whitelist(self, username: str) -> bool:
        """Проверка пользователя в whitelist"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    f"""
                    SELECT is_active 
                    FROM {self.db_schema_config}.whitelist 
                    WHERE username = $1
                    """,
                    username
                )
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking whitelist for {username}: {e}")
            return False

    async def get_selected_conference(self, user_id: int) -> str:
        """Получить выбранную конференцию пользователя"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(f"""
                    SELECT selected_conference 
                    FROM {self.db_schema_config}.user_profiles 
                    WHERE user_id = $1
                """, user_id)
                return result or ""
        except Exception as e:
            logger.error(f"Error getting selected conference: {e}")
            return ""

    # database.py
    async def log_user_action(self, user_id: int, username: str, action: str, details: dict = None) -> bool:
        """Логирование действий пользователя"""
        try:
            import json
            async with self.pool.acquire() as conn:
                # Преобразуем details в JSON строку если это словарь
                details_json = json.dumps(details, default=str) if details else None

                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_logs (user_id, username, action, details, timestamp)
                    VALUES ($1, $2, $3, $4, NOW())
                """, user_id, username, action, details_json)
                return True
        except Exception as e:
            logger.error(f"Error logging user action: {e}")
            return False

    async def update_bot_status(self, bot_id: str, status: str, components: dict) -> bool:
        """Обновление статуса бота"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO systemcheck_bot.bots_status (bot_id, status, components, updated_at)
                                   VALUES ($1, $2, $3, NOW())
                                   ON CONFLICT (bot_id) DO UPDATE
                                       SET status     = EXCLUDED.status,
                                           components = EXCLUDED.components,
                                           updated_at = EXCLUDED.updated_at
                                   """, bot_id, status, components)
                return True
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")
            return False


    async def get_flight_details_travel(self, username: str, conference: str) -> List[Dict]:
        """Получить детали рейсов из схемы travel_bot"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                        SELECT *
                        FROM travel_bot.flights
                        WHERE telegram_name ILIKE $1 AND conference ILIKE $2
                        ORDER BY departure_date, departure_time \
                        """
                result = await conn.fetch(query, f"%{username}%", f"%{conference}%")
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting flight details from travel_bot: {e}")
            return []

    async def get_hotel_info_travel(self, conference: str) -> Dict:
        """Получить информацию об отеле из новой таблицы (ранее из travel_bot.hotels)"""
        try:
            async with self.pool.acquire() as conn:
                # Используем алиасы, чтобы ответ словаря (address, site) соответствовал тому, что ожидает бот
                query = f"""
                        SELECT hotel, hotel_address as address, site_url as site
                        FROM {self.db_schema_config}.conferences
                        WHERE conference_name ILIKE $1
                        LIMIT 1
                        """
                result = await conn.fetchrow(query, f"%{conference}%")
                return dict(result) if result else {}
        except Exception as e:
            logger.error(f"Error getting hotel info from conferences: {e}")
            return {}

    async def get_airline_url_travel(self, airline: str) -> str:
        """Получить URL регистрации авиакомпании из схемы travel_bot"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                        SELECT link
                        FROM travel_bot.airlines
                        WHERE airline like '%{airline}%'
                        LIMIT 1 \
                        """
                result = await conn.fetchval(query)
                return result or ""
        except Exception as e:
            logger.error(f"Error getting airline URL from travel_bot: {e}")
            return ""


    async def get_user_company(self, user_id: int) -> str:
        """Получить компанию пользователя"""
        try:
            async with self.pool.acquire() as conn:
                company = await conn.fetchval(f"""
                    SELECT company FROM {self.db_schema_config}.user_profiles
                    WHERE user_id = $1
                """, user_id)
                return company or ""
        except Exception as e:
            logger.error(f"Error getting user company: {e}")
            return ""

    async def get_users_by_company(self, company: str = None) -> list:
        """Получить пользователей по компании"""
        try:
            async with self.pool.acquire() as conn:
                if company:
                    query = f"""
                        SELECT user_id, username, company 
                        FROM {self.db_schema_config}.user_profiles
                        WHERE company = $1
                    """
                    rows = await conn.fetch(query, company)
                else:
                    query = f"""
                        SELECT user_id, username, company 
                        FROM {self.db_schema_config}.user_profiles
                    """
                    rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users by company: {e}")
            return []

    async def get_all_companies(self) -> list:
        """Получить список всех компаний"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT DISTINCT company 
                    FROM {self.db_schema_config}.companies
                    ORDER BY company
                """)
                return [row['company'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return []

    async def get_all_affiliate_bookings(self) -> list:
        """Получить все бронирования из affil_bookings"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_pr}.affil_bookings 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting affiliate bookings: {e}")
            return []

    async def get_all_affiliate_reports(self) -> list:
        """Получить все отчеты из affil_reports"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_pr}.affil_reports 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting affiliate reports: {e}")
            return []

    async def update_affiliate_booking_status(self, booking_id: int, status: str) -> bool:
        """Обновить статус бронирования (добавляем колонку status если нет)"""
        try:
            async with self.pool.acquire() as conn:
                # Добавляем колонку status если её нет
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_pr}.affil_bookings 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'confirmed'
                    """)
                except:
                    pass

                await conn.execute(f"""
                    UPDATE {self.db_schema_pr}.affil_bookings 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, booking_id)
                return True
        except Exception as e:
            logger.error(f"Error updating affiliate booking status: {e}")
            return False

    async def update_affiliate_report_status(self, report_id: int, status: str) -> bool:
        """Обновить статус отчета (добавляем колонку status если нет)"""
        try:
            async with self.pool.acquire() as conn:
                # Добавляем колонку status если её нет
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_pr}.affil_reports 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'
                    """)
                except:
                    pass

                await conn.execute(f"""
                    UPDATE {self.db_schema_pr}.affil_reports 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, report_id)
                return True
        except Exception as e:
            logger.error(f"Error updating affiliate report status: {e}")
            return False

    async def save_user_registration(self, user_data: dict) -> bool:
        """Сохранение данных регистрации пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем таблицу если нет
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_config}.user_profiles (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT NOT NULL,
                        language TEXT DEFAULT 'ru',
                        full_name TEXT,
                        position TEXT,
                        company TEXT,
                        registered_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Вставляем или обновляем данные
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_config}.user_profiles 
                    (user_id, username, language, full_name, position, company, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET language = EXCLUDED.language,
                        full_name = EXCLUDED.full_name,
                        position = EXCLUDED.position,
                        company = EXCLUDED.company,
                        updated_at = NOW()
                """,
                   user_data['user_id'],
                   user_data['username'],
                   user_data.get('language', 'ru'),
                   user_data.get('full_name'),
                   user_data.get('position'),
                   user_data.get('company')
               )

                return True
        except Exception as e:
            logger.error(f"Error saving user registration: {e}")
            return False

    async def get_user_data(self, user_id: int) -> dict:
        """Получение данных пользователя с форматированием даты"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT user_id, username, language, full_name, position, company, 
                           registered_at, updated_at
                    FROM {self.db_schema_config}.user_profiles 
                    WHERE user_id = $1
                """, user_id)

                if row:
                    result = dict(row)
                    # Форматируем даты для отображения
                    if result.get('registered_at'):
                        result['registered_at'] = result['registered_at']
                    return result
                return {}
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return {}

    async def get_all_questions_by_table(self, table: str) -> list:
        """Получить все вопросы из таблицы"""
        try:
            async with self.pool.acquire() as conn:
                # table уже содержит полное имя таблицы (например travelconference_pr.pr_questions)
                # Не нужно добавлять схему повторно
                query = f'SELECT * FROM {table} ORDER BY created_at DESC'
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting questions from {table}: {e}")
            return []

    async def sync_whitelist_from_google_sheets(self, spreadsheet_name: str = "Whitelist",
                                                clear_existing: bool = True) -> bool:
        """
        Синхронизация whitelist и конференций из Google Sheets

        Args:
            spreadsheet_name: Название Google Sheets таблицы
            clear_existing: Очищать ли существующие данные перед синхронизацией
                           (True - полная перезагрузка, False - добавление новых)
        """
        if self.pool is None:
            logger.error("Database pool not initialized")
            return False

        try:
            from utility.sync import GoogleSheetsSync
            sync = GoogleSheetsSync()

            if not await sync.connect_to_google_sheets():
                logger.error("Failed to connect to Google Sheets")
                return False

            sh = sync.gc.open(spreadsheet_name)
            worksheets = sh.worksheets()

            async with self.pool.acquire() as conn:
                # Очищаем старые данные только если нужно
                if clear_existing:
                    await conn.execute(f"TRUNCATE TABLE {self.db_schema_config}.whitelist CASCADE")
                    await conn.execute(f"TRUNCATE TABLE {self.db_schema}.user_conferences CASCADE")
                    await conn.execute(f"TRUNCATE TABLE {self.db_schema_config}.conferences CASCADE")
                    logger.info("Cleared existing data before sync")

                total_users = 0
                total_conferences = 0
                total_companies = 0

                for worksheet in worksheets:
                    sheet_name = worksheet.title
                    records = worksheet.get_all_records()

                    if not records:
                        continue

                    # ============================================
                    # ЛИСТ "Общая информация" - компании
                    # ============================================
                    if sheet_name == "Общая информация":
                        for record in records:
                            company_name = None
                            for key, value in record.items():
                                if value and str(value).strip():
                                    company_name = str(value).strip()
                                    break

                            if not company_name:
                                continue

                            if company_name.lower() in ['список всех компаний и партнерок', 'company', 'companies']:
                                continue

                            await conn.execute(f"""
                                INSERT INTO {self.db_schema_config}.companies (company_name, is_active)
                                VALUES ($1, TRUE)
                                ON CONFLICT (company_name) DO UPDATE
                                SET is_active = TRUE
                            """, company_name)
                            total_companies += 1

                        logger.info(f"✅ Synced {total_companies} companies from 'Общая информация'")
                        continue

                    # ============================================
                    # ОСТАЛЬНЫЕ ЛИСТЫ - конференции и пользователи
                    # ============================================

                    # Получаем информацию о конференции
                    conference_info = {}
                    for row in records:
                        if row.get('Название конференции'):
                            conference_info = {
                                'conference_name': row.get('Название конференции', sheet_name),
                                'conf_start': row.get('Даты начала конференции', ''),
                                'conf_end': row.get('Дата окончания конференции', ''),
                                'city': row.get('Город конференции', ''),
                                'bot_link': row.get('Бот конференции', ''),
                                'additional_info': row.get('Дополнительная информация', '')
                            }
                            break

                    if not conference_info.get('conference_name'):
                        conference_info = {
                            'conference_name': sheet_name,
                            'conf_start': '',
                            'conf_end': '',
                            'city': '',
                            'bot_link': '',
                            'additional_info': ''
                        }

                    hotel, hotel_address, site_url = '', '', ''
                    try:
                        hotel_data = worksheet.get_values('E5', 'G5')
                        if hotel_data and len(hotel_data) > 0:
                            row_data = hotel_data[0]
                            hotel = str(row_data[0]).strip() if len(row_data) > 0 else ''
                            hotel_address = str(row_data[1]).strip() if len(row_data) > 1 else ''
                            site_url = str(row_data[2]).strip() if len(row_data) > 2 else ''
                    except Exception as e:
                        logger.warning(f"Could not get hotel data for {sheet_name}: {e}")

                    # Сохраняем конференцию
                    await conn.execute(f"""
                                            INSERT INTO {self.db_schema_config}.conferences 
                                            (conference_name, start_date, end_date, city, bot_link, additional_info, sheet_name, hotel, hotel_address, site_url)
                                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                                            ON CONFLICT (conference_name) DO UPDATE
                                            SET start_date = EXCLUDED.start_date,
                                                end_date = EXCLUDED.end_date,
                                                city = EXCLUDED.city,
                                                bot_link = EXCLUDED.bot_link,
                                                additional_info = EXCLUDED.additional_info,
                                                sheet_name = EXCLUDED.sheet_name,
                                                hotel = EXCLUDED.hotel,
                                                hotel_address = EXCLUDED.hotel_address,
                                                site_url = EXCLUDED.site_url
                                        """,
                                       conference_info['conference_name'],
                                       conference_info['conf_start'],
                                       conference_info['conf_end'],
                                       conference_info['city'],
                                       conference_info['bot_link'],
                                       conference_info['additional_info'],
                                       sheet_name,
                                       hotel,
                                       hotel_address,
                                       site_url
                                       )
                    total_conferences += 1

                    # Обрабатываем пользователей
                    for record in records:
                        username = record.get('TG_username', '').strip()
                        if not username or username.lower() == 'tg_username':
                            continue

                        # Сохраняем в whitelist (только username и is_active)
                        await conn.execute(f"""
                            INSERT INTO {self.db_schema_config}.whitelist (username, is_active)
                            VALUES ($1, TRUE)
                            ON CONFLICT (username) DO UPDATE
                            SET is_active = TRUE
                        """, username)

                        # Сохраняем конференцию пользователя
                        await conn.execute(f"""
                            INSERT INTO {self.db_schema}.user_conferences 
                            (username, conference_name, trip_start_date, trip_end_date, 
                             conference_start_date, conference_end_date, city, bot_link, additional_info)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (username, conference_name) DO UPDATE
                            SET trip_start_date = EXCLUDED.trip_start_date,
                                trip_end_date = EXCLUDED.trip_end_date,
                                conference_start_date = EXCLUDED.conference_start_date,
                                conference_end_date = EXCLUDED.conference_end_date,
                                city = EXCLUDED.city,
                                bot_link = EXCLUDED.bot_link,
                                additional_info = EXCLUDED.additional_info
                        """,
                                           username,
                                           conference_info['conference_name'],
                                           record.get('Дата начала поездки', ''),
                                           record.get('Дата окончания поездки', ''),
                                           conference_info['conf_start'],
                                           conference_info['conf_end'],
                                           conference_info['city'],
                                           conference_info['bot_link'],
                                           conference_info['additional_info']
                                           )
                        total_users += 1

                logger.info(
                    f"✅ Synced {total_users} users, {total_conferences} conferences, {total_companies} companies")

                # Логируем результат синхронизации
                await self.log_user_action(
                    user_id=0,
                    username="system",
                    action="whitelist_synced",
                    details={
                        "users": total_users,
                        "conferences": total_conferences,
                        "companies": total_companies,
                        "clear_existing": clear_existing
                    }
                )

                return True

        except Exception as e:
            logger.error(f"Error syncing whitelist from Google Sheets: {e}")
            return False

    async def get_user_conferences(self, username: str) -> List[Dict]:
        """Получить все конференции пользователя"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT conference_name, trip_start_date, trip_end_date,
                           conference_start_date, conference_end_date, city
                    FROM {self.db_schema}.user_conferences
                    WHERE username = $1
                    ORDER BY conference_start_date
                """, username)
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Error getting user conferences: {e}")
            return []

    async def get_user_active_conferences(self, username: str) -> List[Dict]:
        """Получить список активных конференций пользователя"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        conference_name,
                        trip_start_date,
                        trip_end_date,
                        conference_start_date,
                        conference_end_date,
                        city,
                        bot_link,
                        additional_info
                    FROM {self.db_schema}.user_conferences
                    WHERE username = $1
                    ORDER BY conference_start_date
                """, username)

                if rows:
                    result = []
                    for row in rows:
                        record = dict(row)
                        record['bot_link'] = record.get('bot_link') or ''
                        record['additional_info'] = record.get('additional_info') or ''
                        result.append(record)
                    return result
                return []
        except Exception as e:
            logger.error(f"Error getting user active conferences: {e}")
            return []


    async def check_user_conference_access(self, username: str, conference: str) -> bool:
        """
        Проверить, имеет ли пользователь доступ к конкретной конференции
        """
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(f"""
                    SELECT 1 FROM {self.db_schema}.user_conferences
                    WHERE username = $1 AND conference_name = $2
                """, username, conference)
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking conference access: {e}")
            # Fallback to whitelist check
            return await self.check_whitelist(username)

    async def get_travel_request_status(self, username: str, request_type: str) -> dict:
        """Получить статус travel-заявки пользователя"""
        try:
            async with self.pool.acquire() as conn:
                if request_type == "visa":
                    table = f"{self.db_schema_travel}.travel_flight_request"
                    status_col = "status"
                elif request_type == "flight":
                    table = f"{self.db_schema_travel}.travel_flight_request"  # временно, нужна отдельная таблица
                    status_col = "status"
                else:
                    return {"status": "unknown", "details": {}}

                # TODO: Добавить колонку status в таблицы
                # Пока проверяем наличие записей
                record = await conn.fetchrow(
                    f"SELECT created_at FROM {table} WHERE username = $1 ORDER BY created_at DESC LIMIT 1",
                    username
                )

                if record:
                    return {
                        "status": "pending",
                        "submitted": record['created_at'].strftime("%d.%m.%Y %H:%M"),
                        "message": "Your request is being processed"
                    }
                else:
                    return {"status": "no_requests", "details": {}}

        except Exception as e:
            logger.error(f"Error getting travel status: {e}")
            return {"status": "error", "details": {"error": str(e)}}

    async def add_admin_user(self, username: str, password: str, full_name: str = None,
                             role: str = 'user', permissions: dict = None) -> bool:
        """Добавление администратора"""
        try:
            from hashlib import sha256
            password_hash = sha256(password.encode()).hexdigest()

            async with self.pool.acquire() as conn:
                # Проверяем, существует ли уже
                exists = await conn.fetchval(f"""
                    SELECT id FROM {self.db_schema_admin}.admin_users WHERE username = $1
                """, username)

                if exists:
                    return False

                perms = permissions or {}
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_admin}.admin_users 
                    (username, password_hash, full_name, role, 
                     can_manage_users, can_broadcast, can_view_stats, can_manage_conferences)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, username, password_hash, full_name, role,
                                   perms.get('manage_users', False),
                                   perms.get('broadcast', True),
                                   perms.get('view_stats', True),
                                   perms.get('manage_conferences', False))

                return True
        except Exception as e:
            logger.error(f"Error adding admin user: {e}")
            return False

    async def verify_admin(self, username: str, password: str) -> dict:
        """Проверка учетных данных администратора"""
        try:
            from hashlib import sha256
            password_hash = sha256(password.encode()).hexdigest()

            async with self.pool.acquire() as conn:
                admin = await conn.fetchrow(f"""
                    SELECT id, username, full_name, role, 
                           can_manage_users, can_broadcast, can_view_stats, can_manage_conferences,
                           is_active
                    FROM {self.db_schema_admin}.admin_users 
                    WHERE username = $1 AND password_hash = $2 AND is_active = TRUE
                """, username, password_hash)

                if admin:
                    # Обновляем время последнего входа
                    await conn.execute(f"""
                        UPDATE {self.db_schema_admin}.admin_users 
                        SET last_login = NOW() 
                        WHERE id = $1
                    """, admin['id'])

                    # Возвращаем словарь со всеми полями
                    return {
                        'id': admin['id'],
                        'username': admin['username'],
                        'full_name': admin['full_name'],
                        'role': admin['role'],
                        'can_manage_users': admin['can_manage_users'],
                        'can_broadcast': admin['can_broadcast'],
                        'can_view_stats': admin['can_view_stats'],
                        'can_manage_conferences': admin['can_manage_conferences'],
                        'is_active': admin['is_active']
                    }
                return {}
        except Exception as e:
            logger.error(f"Error verifying admin: {e}")
            return {}

    async def get_all_admin_users(self) -> list:
        """Получить всех администраторов"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT id, username, full_name, role, 
                           can_manage_users, can_broadcast, can_view_stats, can_manage_conferences,
                           created_at, last_login, is_active
                    FROM {self.db_schema_admin}.admin_users
                    ORDER BY id
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            return []

    async def update_admin_user(self, admin_id: int, data: dict) -> bool:
        """Обновление данных администратора"""
        try:
            async with self.pool.acquire() as conn:
                set_clauses = []
                values = []
                i = 1

                for key, value in data.items():
                    if key != 'id' and key != 'password_hash':
                        set_clauses.append(f"{key} = ${i}")
                        values.append(value)
                        i += 1

                if 'password' in data and data['password']:
                    from hashlib import sha256
                    set_clauses.append(f"password_hash = ${i}")
                    values.append(sha256(data['password'].encode()).hexdigest())
                    i += 1

                if set_clauses:
                    values.append(admin_id)
                    query = f"""
                        UPDATE {self.db_schema_admin}.admin_users 
                        SET {', '.join(set_clauses)}
                        WHERE id = ${i}
                    """
                    await conn.execute(query, *values)

                return True
        except Exception as e:
            logger.error(f"Error updating admin user: {e}")
            return False

    async def delete_admin_user(self, admin_id: int) -> bool:
        """Удаление администратора"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    DELETE FROM {self.db_schema_admin}.admin_users WHERE id = $1
                """, admin_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting admin user: {e}")
            return False

    async def log_admin_action(self, admin_id: int, action: str, details: dict = None,
                               ip_address: str = None) -> bool:
        """Логирование действий администратора"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_admin}.admin_logs 
                    (admin_id, action, details, ip_address)
                    VALUES ($1, $2, $3, $4)
                """, admin_id, action, details or {}, ip_address)
                return True
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
            return False

    async def check_admin_permission(self, admin_id: int, permission: str) -> bool:
        """Проверка прав администратора"""
        try:
            async with self.pool.acquire() as conn:
                admin = await conn.fetchrow(f"""
                    SELECT role, can_manage_users, can_broadcast, can_view_stats, can_manage_conferences
                    FROM {self.db_schema_admin}.admin_users
                    WHERE id = $1 AND is_active = TRUE
                """, admin_id)

                if not admin:
                    return False

                # Админ имеет все права
                if admin['role'] == 'admin':
                    return True

                # Проверяем конкретное право
                perm_map = {
                    'manage_users': 'can_manage_users',
                    'broadcast': 'can_broadcast',
                    'view_stats': 'can_view_stats',
                    'manage_conferences': 'can_manage_conferences'
                }

                if permission in perm_map:
                    return admin[perm_map[permission]]

                return False
        except Exception as e:
            logger.error(f"Error checking admin permission: {e}")
            return False

    # ===== МЕТОДЫ ДЛЯ УПРАВЛЕНИЯ ГРУППАМИ И ФУНКЦИЯМИ =====

    # Добавить в класс Database:

    async def get_all_visa_requests(self) -> list:
        """Получить все визовые заявки"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_travel}.travel_flight_request 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting visa requests: {e}")
            return []

    async def get_all_banner_requests(self) -> list:
        """Получить все заявки на баннеры"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_pr}.pr_banner_requests 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting banner requests: {e}")
            return []


    async def get_all_companies_from_config(self) -> list:
        """Получить список всех компаний из конфига"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT company_name FROM {self.db_schema_config}.companies
                    WHERE is_active = TRUE
                    ORDER BY company_name
                """)
                return [row['company_name'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting companies from config: {e}")
            return []

    async def search_companies_by_prefix(self, prefix: str) -> list:
        """Поиск компаний по префиксу (для автодополнения)"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT company_name FROM {self.db_schema_config}.companies
                    WHERE is_active = TRUE AND company_name ILIKE $1
                    ORDER BY company_name
                    LIMIT 10
                """, f"{prefix}%")
                return [row['company_name'] for row in rows]
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []

    async def get_all_users_basic(self) -> list:
        """Получить базовую информацию о всех пользователях"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT user_id, username, full_name, company
                    FROM {self.db_schema_config}.user_profiles
                    ORDER BY username
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users basic: {e}")
            return []


    async def get_all_business_cards(self) -> list:
        """Получить все заявки на визитки"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema_pr}.pr_business_cards 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting business cards: {e}")
            return []

    async def get_all_flight_requests(self) -> list:
        """Получить все заявки на авиабилеты"""
        try:
            async with self.pool.acquire() as conn:
                # Если есть таблица flight_requests
                try:
                    rows = await conn.fetch(f"""
                        SELECT * FROM {self.db_schema}.user_flights 
                        ORDER BY created_at DESC
                    """)
                    return [dict(row) for row in rows]
                except:
                    # Если таблицы нет, возвращаем пустой список
                    return []
        except Exception as e:
            logger.error(f"Error getting flight requests: {e}")
            return []

    async def update_visa_status(self, request_id: int, status: str, comment: str = None) -> bool:
        """Обновить статус визовой заявки"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema_travel}.travel_flight_request 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating visa status: {e}")
            return False

    # database.py - добавить эти методы в класс Database

    async def get_stored_passport_data(self, user_id: int) -> dict:
        """Получить сохраненные паспортные данные пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем таблицу если нет
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.stored_passport_data (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        phone TEXT,
                        passport_number TEXT,
                        birth_date TEXT,
                        passport_country TEXT,
                        issue_date TEXT,
                        expiry_date TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                row = await conn.fetchrow(f"""
                    SELECT first_name, last_name, phone, passport_number, 
                           birth_date, passport_country, issue_date, expiry_date
                    FROM {self.db_schema}.stored_passport_data
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, user_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting stored passport data: {e}")
            return {}

    async def save_passport_data(self, user_id: int, username: str, passport_data: dict) -> bool:
        """Сохранить паспортные данные пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем таблицу если нет (уже создана в get_stored_passport_data)
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.stored_passport_data 
                    (user_id, username, first_name, last_name, phone, passport_number, 
                     birth_date, passport_country, issue_date, expiry_date)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, user_id, username,
                                   passport_data.get('first_name'), passport_data.get('last_name'),
                                   passport_data.get('phone'), passport_data.get('passport_number'),
                                   passport_data.get('birth_date'), passport_data.get('passport_country'),
                                   passport_data.get('issue_date'), passport_data.get('expiry_date'))
                return True
        except Exception as e:
            logger.error(f"Error saving passport data: {e}")
            return False

    async def get_available_flights(self, username: str, departure_from: str, return_to: str) -> List[Dict]:
        """Получить доступные рейсы для пользователя"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema}.user_flights
                    WHERE username = $1 
                    AND departure_from ILIKE $2
                    AND arrival_city ILIKE $3
                    ORDER BY departure_date, departure_time
                """, username, f"%{departure_from}%", f"%{return_to}%")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting available flights: {e}")
            return []

    async def get_banner_request_by_id(self, request_id: int) -> dict:
        """Получить заявку на баннер по ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT * FROM {self.db_schema_pr}.pr_banner_requests 
                    WHERE id = $1
                """, request_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting banner request by id: {e}")
            return {}

    async def get_business_card_request_by_id(self, request_id: int) -> dict:
        """Получить заявку на визитки по ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT * FROM {self.db_schema_pr}.pr_business_cards 
                    WHERE id = $1
                """, request_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting business card request by id: {e}")
            return {}

    async def update_banner_status(self, request_id: int, status: str) -> bool:
        """Обновить статус заявки на баннер"""
        try:
            async with self.pool.acquire() as conn:

                await conn.execute(f"""
                    UPDATE {self.db_schema_pr}.pr_banner_requests 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating banner status: {e}")
            return False

    async def update_business_card_status(self, request_id: int, status: str) -> bool:
        """Обновить статус заявки на визитки"""
        try:
            async with self.pool.acquire() as conn:

                await conn.execute(f"""
                    UPDATE {self.db_schema_pr}.pr_business_cards 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating business card status: {e}")
            return False


    async def get_recent_broadcasts(self, limit=10) -> list:
        """Получить последние рассылки"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        details->>'type' as broadcast_type,
                        details->>'company' as company,
                        (details->>'success')::int as success_count,
                        (details->>'failed')::int as failed_count,
                        timestamp
                    FROM {self.db_schema}.user_logs
                    WHERE action = 'broadcast_sent'
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting broadcasts: {e}")
            return []

    async def get_stats(self) -> dict:
        """Получить статистику"""
        try:
            async with self.pool.acquire() as conn:
                total_users = await conn.fetchval(f"""
                    SELECT COUNT(DISTINCT user_id) FROM {self.db_schema_config}.user_profiles
                """) or 0

                active_today = await conn.fetchval(f"""
                    SELECT COUNT(DISTINCT user_id)
                    FROM {self.db_schema}.user_logs
                    WHERE timestamp > NOW() - INTERVAL '1 day'
                """) or 0

                companies_stats = await conn.fetch(f"""
                    SELECT company, COUNT(DISTINCT user_id) as user_count
                    FROM {self.db_schema_config}.user_profiles
                    WHERE company IS NOT NULL AND company != ''
                    GROUP BY company
                    ORDER BY user_count DESC
                    LIMIT 5
                """)

                banner_requests = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_pr}.pr_banner_requests
                """) or 0

                visa_requests = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request
                """) or 0

                active_conferences = await conn.fetchval(f"""
                    SELECT COUNT(DISTINCT conference_name)
                    FROM {self.db_schema_config}.conferences
                """) or 0

                total_broadcasts = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.user_logs
                    WHERE action = 'broadcast_sent'
                """) or 0

                return {
                    'total_users': total_users,
                    'active_today': active_today,
                    'companies_stats': [dict(row) for row in companies_stats],
                    'banner_requests': banner_requests,
                    'visa_requests': visa_requests,
                    'active_conferences': active_conferences,
                    'total_broadcasts': total_broadcasts
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    async def log_broadcast(self, username: str, broadcast_type: str, company: str,
                            success: int, failed: int, message_length: int, file_count: int = 0) -> bool:
        """Логировать рассылку"""
        try:
            import json
            async with self.pool.acquire() as conn:
                details = {
                    'type': broadcast_type,
                    'company': company,
                    'success': success,
                    'failed': failed,
                    'message_length': message_length,
                    'file_count': file_count
                }
                details_json = json.dumps(details, default=str)

                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_logs (user_id, username, action, details, timestamp)
                    VALUES (0, $1, 'broadcast_sent', $2, NOW())
                """, username, details_json)
                return True
        except Exception as e:
            logger.error(f"Error logging broadcast: {e}")
            return False

    async def get_users_by_company_list(self, companies: list = None) -> list:
        """Получить пользователей по списку компаний"""
        try:
            async with self.pool.acquire() as conn:
                if companies:
                    query = f"""
                        SELECT user_id, username, company
                        FROM {self.db_schema_config}.user_profiles
                        WHERE company = ANY($1::text[])
                    """
                    rows = await conn.fetch(query, companies)
                else:
                    query = f"""
                        SELECT user_id, username, company
                        FROM {self.db_schema_config}.user_profiles
                    """
                    rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users by company: {e}")
            return []

    async def get_users_by_ids_list(self, user_ids: list) -> list:
        """Получить пользователей по списку ID"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT user_id, username, company
                    FROM {self.db_schema_config}.user_profiles
                    WHERE user_id = ANY($1::bigint[])
                """
                rows = await conn.fetch(query, user_ids)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users by ids: {e}")
            return []

    async def get_users_by_conference_list(self, conferences: list) -> list:
        """Получить пользователей по списку конференций с деталями"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT DISTINCT 
                        up.user_id, 
                        up.username, 
                        up.full_name, 
                        up.company,
                        up.position
                    FROM {self.db_schema_config}.user_profiles up
                    JOIN {self.db_schema}.user_conferences uconf ON up.username = uconf.username
                    WHERE uconf.conference_name = ANY($1::text[])
                """
                rows = await conn.fetch(query, conferences)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users by conference: {e}")
            return []

    async def get_companies_list(self) -> list:
        """Получить список компаний"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT DISTINCT company
                    FROM {self.db_schema_config}.user_profiles
                    WHERE company IS NOT NULL AND company != ''
                    ORDER BY company
                """)
                return [row['company'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return []

    async def get_conferences_list(self) -> list:
        """Получить список конференций с количеством участников"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        c.conference_name as name,
                        c.city,
                        c.start_date,
                        c.end_date,
                        COUNT(DISTINCT uc.username) as user_count
                    FROM {self.db_schema_config}.conferences c
                    LEFT JOIN {self.db_schema}.user_conferences uc ON c.conference_name = uc.conference_name
                    GROUP BY c.conference_name, c.city, c.start_date, c.end_date
                    ORDER BY c.start_date DESC
                """)
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Error getting conferences: {e}")
            return []

    async def get_ticket_request_by_id(self, request_id: int) -> dict:
        """Получить заявку на билет по ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT * FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE id = $1
                """, request_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting ticket request by id: {e}")
            return {}

    async def get_all_users_with_details(self) -> list:
        """Получить всех пользователей с деталями"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        up.user_id,
                        up.username,
                        up.full_name,
                        up.company,
                        up.position,
                        up.language,
                        up.registered_at,
                        (SELECT MAX(timestamp) FROM {self.db_schema}.user_logs WHERE user_id = up.user_id) as last_active,
                        (SELECT COUNT(*) FROM {self.db_schema}.user_logs WHERE user_id = up.user_id AND timestamp > NOW() - INTERVAL '5 minutes') > 0 as is_online
                    FROM {self.db_schema_config}.user_profiles up
                    ORDER BY up.registered_at DESC
                """)
                users = [dict(row) for row in rows]

                for user in users:
                    confs = await conn.fetch(f"""
                        SELECT conference_name
                        FROM {self.db_schema}.user_conferences
                        WHERE username = $1
                    """, user['username'])
                    user['conferences'] = [c['conference_name'] for c in confs]

                    requests_count = 0
                    for table in ['pr_banner_requests', 'pr_business_cards', 'travel_flight_request']:
                        try:
                            if table in ('pr_banner_requests', 'pr_business_cards'):
                                cnt = await conn.fetchval(f"""
                                    SELECT COUNT(*) FROM {self.db_schema_pr}.{table} WHERE username = $1
                                """, user['username'])
                                requests_count += cnt
                            else:
                                cnt = await conn.fetchval(f"""
                                    SELECT COUNT(*) FROM {self.db_schema_travel}.{table} WHERE username = $1
                                """, user['username'])
                                requests_count += cnt
                        except:
                            pass
                    user['requests_count'] = requests_count

                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    # Добавьте эти методы в класс Database

    async def get_user_messages_by_department(self, manager_groups: list, limit: int = 100) -> list:
        """Получить сообщения пользователей, доступные для групп менеджера"""
        try:
            async with self.pool.acquire() as conn:
                # Карта соответствия групп менеджеров и типов вопросов
                # travel_questions, pr_questions, event_questions
                department_map = {
                    'travel': 'travel_questions',
                    'pr': 'pr_questions',
                    'event': 'event_questions'
                }

                # Определяем, какие таблицы может видеть менеджер
                visible_tables = []
                for group in manager_groups:
                    if group in department_map:
                        visible_tables.append(department_map[group])

                if not visible_tables:
                    return []

                # Собираем вопросы из всех доступных таблиц
                all_questions = []
                for table in visible_tables:
                    rows = await conn.fetch(f"""
                        SELECT 
                            q.id,
                            q.username,
                            q.user_id,
                            q.category,
                            q.question,
                            q.created_at,
                            'question' as type,
                            '{table.replace('_questions', '')}' as department
                        FROM {self.db_schema}.{table} q
                        ORDER BY q.created_at DESC
                        LIMIT $1
                    """, limit)
                    all_questions.extend([dict(row) for row in rows])

                # Также добавляем обычные сообщения из чатов
                messages = await conn.fetch(f"""
                    SELECT 
                        m.id,
                        m.user_id,
                        m.username,
                        m.message_text,
                        m.direction,
                        m.created_at,
                        'message' as type,
                        NULL as department,
                        EXISTS(
                            SELECT 1 FROM {self.db_schema}.user_messages m2 
                            WHERE m2.user_id = m.user_id 
                            AND m2.direction = 'incoming' 
                            AND m2.read_at IS NULL
                        ) as has_unread
                    FROM {self.db_schema}.user_messages m
                    WHERE m.direction = 'incoming'
                    ORDER BY m.created_at DESC
                    LIMIT $1
                """, limit)

                all_questions.extend([dict(row) for row in messages])

                # Сортируем по дате
                all_questions.sort(key=lambda x: x['created_at'], reverse=True)

                return all_questions
        except Exception as e:
            logger.error(f"Error getting messages by department: {e}")
            return []

    async def share_question_with_department(self, question_id: int, question_type: str,
                                             source_department: str, target_department: str,
                                             shared_by: str) -> bool:
        """Переслать вопрос в другой отдел"""
        try:
            async with self.pool.acquire() as conn:
                # Определяем таблицы
                tables = {
                    'pr': f'{self.db_schema_pr}.pr_questions',
                    'event': f'{self.db_schema_event}.event_questions',
                    'travel': f'{self.db_schema_travel}.travel_questions'
                }

                # Получаем исходный вопрос
                source_table = tables.get(source_department)
                if not source_table:
                    return False

                question = await conn.fetchrow(f"""
                    SELECT username, user_id, category, question
                    FROM {source_table}
                    WHERE id = $1
                """, question_id)

                if not question:
                    return False

                # Создаем копию в таблице целевого отдела
                target_table = tables.get(target_department)
                if not target_table:
                    return False

                await conn.execute(f"""
                    INSERT INTO {target_table} 
                    (username, user_id, category, question, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                """, question['username'], question['user_id'],
                                   f"shared_from_{source_department}",
                                   f"[Переслано из {source_department}]\n\n{question['question']}")

                # Логируем действие
                await self.log_user_action(
                    user_id=0,
                    username=shared_by,
                    action="question_shared",
                    details={
                        "question_id": question_id,
                        "source": source_department,
                        "target": target_department
                    }
                )

                return True
        except Exception as e:
            logger.error(f"Error sharing question: {e}")
            return False

    async def get_question_details(self, question_id: int, question_type: str) -> dict:
        """Получить детали вопроса по ID и типу"""
        try:
            async with self.pool.acquire() as conn:
                tables = {
                    'pr': f'{self.db_schema_pr}.pr_questions',
                    'event': f'{self.db_schema_event}.event_questions',
                    'travel': f'{self.db_schema_travel}.travel_questions'
                }

                table = tables.get(question_type)
                if not table:
                    return {}

                row = await conn.fetchrow(f"""
                    SELECT id, username, user_id, category, question, created_at
                    FROM {table}
                    WHERE id = $1
                """, question_id)

                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting question details: {e}")
            return {}

    async def get_user_details_by_id(self, user_id: int) -> dict:
        """Получить детальную информацию о пользователе"""
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(f"""
                    SELECT 
                        up.*,
                        (SELECT MAX(timestamp) FROM {self.db_schema}.user_logs WHERE user_id = up.user_id) as last_active
                    FROM {self.db_schema_config}.user_profiles up
                    WHERE up.user_id = $1
                """, user_id)

                if not user:
                    return None

                result = dict(user)

                confs = await conn.fetch(f"""
                    SELECT conference_name
                    FROM {self.db_schema}.user_conferences
                    WHERE username = $1
                """, result['username'])
                result['conferences'] = [c['conference_name'] for c in confs]

                result['requests'] = []
                request_tables = [
                    ('pr_banner_requests', 'Баннер'),
                    ('pr_business_cards', 'Визитки'),
                    ('travel_flight_request', 'Виза')
                ]
                for table, type_name in request_tables:
                    try:
                        if table in ('pr_banner_requests', 'pr_business_cards'):
                            rows = await conn.fetch(f"""
                               SELECT id, created_at, 'pending' as status
                               FROM {self.db_schema_pr}.{table}
                               WHERE username = $1
                               ORDER BY created_at DESC
                               LIMIT 5
                           """, result['username'])
                        else:
                            rows = await conn.fetch(f"""
                                SELECT id, created_at, 'pending' as status
                                FROM {self.db_schema_travel}.{table}
                                WHERE username = $1
                                ORDER BY created_at DESC
                                LIMIT 5
                        """, result['username'])
                        for row in rows:
                            result['requests'].append({
                                'type': type_name,
                                'created_at': row['created_at'].strftime('%d.%m.%Y %H:%M'),
                                'status': 'pending'
                            })
                    except:
                        pass

                return result
        except Exception as e:
            logger.error(f"Error getting user details: {e}")
            return None

    # database.py - добавьте эти методы в класс Database

    async def create_managers_tables(self):
        """Создание таблиц для менеджеров и групп"""
        try:
            async with self.pool.acquire() as conn:
                # Таблица менеджеров
                await conn.execute(f"""
                                   CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.managers
                                   (
                                       id            SERIAL PRIMARY KEY,
                                       username      TEXT UNIQUE NOT NULL,
                                       password_hash TEXT        NOT NULL,
                                       full_name     TEXT,
                                       role          TEXT        NOT NULL DEFAULT 'manager',
                                       is_active     BOOLEAN              DEFAULT TRUE,
                                       created_at    TIMESTAMP            DEFAULT NOW(),
                                       last_login    TIMESTAMP
                                   )
                                   """)

                # Таблица групп
                await conn.execute(f"""
                                   CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_groups
                                   (
                                       id          SERIAL PRIMARY KEY,
                                       name        TEXT UNIQUE NOT NULL,
                                       description TEXT,
                                       created_at  TIMESTAMP DEFAULT NOW()
                                   )
                                   """)

                # Связь менеджеров с группами
                await conn.execute(f"""
                                   CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_group_membership
                                   (
                                       manager_id  INTEGER REFERENCES {self.db_schema_admin}.managers (id) ON DELETE CASCADE,
                                       group_id    INTEGER REFERENCES {self.db_schema_admin}.manager_groups (id) ON DELETE CASCADE,
                                       assigned_at TIMESTAMP DEFAULT NOW(),
                                       PRIMARY KEY (manager_id, group_id)
                                   )
                                   """)

                # Добавляем базовые группы
                base_groups = [
                    ('admin', 'Администраторы - полный доступ'),
                    ('pr', 'PR отдел - управление баннерами и визитками'),
                    ('event', 'Event отдел - управление справками и мероприятиями'),
                    ('travel', 'Travel отдел - управление визами и билетами')
                ]

                for name, desc in base_groups:
                    await conn.execute(f"""
                                       INSERT INTO {self.db_schema_admin}.manager_groups (name, description)
                                       VALUES ($1, $2)
                                       ON CONFLICT (name) DO NOTHING
                                       """, name, desc)

                # Создаем админа по умолчанию, если нет
                from hashlib import sha256
                admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
                admin_hash = sha256(admin_pass.encode()).hexdigest()

                # Добавляем админа
                admin_id = await conn.fetchval(f"""
                                               INSERT INTO {self.db_schema_admin}.managers (username, password_hash, full_name, role)
                                               VALUES ($1, $2, $3, $4)
                                               ON CONFLICT (username) DO NOTHING
                                               RETURNING id
                                               """, 'admin', admin_hash, 'Главный администратор', 'admin')

                # Если админ создан, добавляем его в группу admin
                if admin_id:
                    admin_group_id = await conn.fetchval(f"""
                                                         SELECT id
                                                         FROM {self.db_schema_admin}.manager_groups
                                                         WHERE name = 'admin'
                                                         """)
                    if admin_group_id:
                        await conn.execute(f"""
                                           INSERT INTO {self.db_schema_admin}.manager_group_membership (manager_id, group_id)
                                           VALUES ($1, $2)
                                           ON CONFLICT DO NOTHING
                                           """, admin_id, admin_group_id)

                print("✅ Managers tables created")
                return True

        except Exception as e:
            print(f"Error creating managers tables: {e}")
            return False

    async def verify_manager(self, username: str, password: str) -> dict:
        """Проверка учетных данных менеджера"""
        try:
            from hashlib import sha256
            password_hash = sha256(password.encode()).hexdigest()

            async with self.pool.acquire() as conn:
                manager = await conn.fetchrow(f"""
                                              SELECT id, username, full_name, role, is_active
                                              FROM {self.db_schema_admin}.managers
                                              WHERE username = $1
                                                AND password_hash = $2
                                                AND is_active = TRUE
                                              """, username, password_hash)

                if manager:
                    # Получаем группы менеджера
                    groups = await conn.fetch(f"""
                                              SELECT g.name, g.description
                                              FROM {self.db_schema_admin}.manager_groups g
                                                       JOIN {self.db_schema_admin}.manager_group_membership mgm ON g.id = mgm.group_id
                                              WHERE mgm.manager_id = $1
                                              """, manager['id'])

                    # Обновляем время последнего входа
                    await conn.execute(f"""
                                       UPDATE {self.db_schema_admin}.managers
                                       SET last_login = NOW()
                                       WHERE id = $1
                                       """, manager['id'])

                    return {
                        'id': manager['id'],
                        'username': manager['username'],
                        'full_name': manager['full_name'],
                        'role': manager['role'],
                        'groups': [dict(g) for g in groups],
                        'group_names': [g['name'] for g in groups]
                    }
                return {}
        except Exception as e:
            print(f"Error verifying manager: {e}")
            return {}


    async def add_manager(self, username: str, password: str, full_name: str = None, groups: list = None) -> bool:
        """Добавить нового менеджера"""
        try:
            from hashlib import sha256
            password_hash = sha256(password.encode()).hexdigest()

            async with self.pool.acquire() as conn:
                # Добавляем менеджера
                manager_id = await conn.fetchval(f"""
                                                 INSERT INTO {self.db_schema_admin}.managers (username, password_hash, full_name, role)
                                                 VALUES ($1, $2, $3, 'manager')
                                                 RETURNING id
                                                 """, username, password_hash, full_name)

                if manager_id and groups:
                    # Добавляем в группы
                    for group_name in groups:
                        group_id = await conn.fetchval(f"""
                                                       SELECT id
                                                       FROM {self.db_schema_admin}.manager_groups
                                                       WHERE name = $1
                                                       """, group_name)
                        if group_id:
                            await conn.execute(f"""
                                               INSERT INTO {self.db_schema_admin}.manager_group_membership (manager_id, group_id)
                                               VALUES ($1, $2)
                                               ON CONFLICT DO NOTHING
                                               """, manager_id, group_id)

                return bool(manager_id)
        except Exception as e:
            print(f"Error adding manager: {e}")
            return False

    async def delete_manager(self, manager_id: int) -> bool:
        """Удалить менеджера"""
        try:
            async with self.pool.acquire() as conn:
                # Не даем удалить последнего админа
                admin_count = await conn.fetchval(f"""
                                                  SELECT COUNT(*)
                                                  FROM {self.db_schema_admin}.managers
                                                  WHERE role = 'admin'
                                                  """)

                if admin_count <= 1:
                    manager = await conn.fetchval(f"""
                                                  SELECT role
                                                  FROM {self.db_schema_admin}.managers
                                                  WHERE id = $1
                                                  """, manager_id)
                    if manager == 'admin':
                        return False

                await conn.execute(f"DELETE FROM {self.db_schema_admin}.managers WHERE id = $1", manager_id)
                return True
        except Exception as e:
            print(f"Error deleting manager: {e}")
            return False

    async def get_manager_groups(self) -> list:
        """Получить все доступные группы"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                                        SELECT *
                                        FROM {self.db_schema_admin}.manager_groups
                                        ORDER BY id
                                        """)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting manager groups: {e}")
            return []

    async def update_manager_groups(self, manager_id: int, groups: list) -> bool:
        """Обновить группы менеджера"""
        try:
            async with self.pool.acquire() as conn:
                # Удаляем старые связи
                await conn.execute(f"""
                                   DELETE
                                   FROM {self.db_schema_admin}.manager_group_membership
                                   WHERE manager_id = $1
                                   """, manager_id)

                # Добавляем новые
                for group_name in groups:
                    group_id = await conn.fetchval(f"""
                                                   SELECT id
                                                   FROM {self.db_schema_admin}.manager_groups
                                                   WHERE name = $1
                                                   """, group_name)
                    if group_id:
                        await conn.execute(f"""
                                           INSERT INTO {self.db_schema_admin}.manager_group_membership (manager_id, group_id)
                                           VALUES ($1, $2)
                                           """, manager_id, group_id)

                return True
        except Exception as e:
            print(f"Error updating manager groups: {e}")
            return False

    async def update_manager(self, manager_id: int, full_name: str = None,
                             is_active: bool = None, groups: list = None) -> bool:
        """Обновление данных менеджера"""
        try:
            async with self.pool.acquire() as conn:
                # Обновляем основные данные
                if full_name is not None:
                    await conn.execute(f"""
                        UPDATE {self.db_schema_admin}.managers 
                        SET full_name = $1
                        WHERE id = $2
                    """, full_name, manager_id)

                if is_active is not None:
                    await conn.execute(f"""
                        UPDATE {self.db_schema_admin}.managers 
                        SET is_active = $1
                        WHERE id = $2
                    """, is_active, manager_id)

                # Обновляем группы
                if groups is not None:
                    # Удаляем старые связи
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema_admin}.manager_group_membership
                        WHERE manager_id = $1
                    """, manager_id)

                    # Добавляем новые
                    for group_name in groups:
                        group_id = await conn.fetchval(f"""
                            SELECT id FROM {self.db_schema_admin}.manager_groups 
                            WHERE name = $1
                        """, group_name)
                        if group_id:
                            await conn.execute(f"""
                                INSERT INTO {self.db_schema_admin}.manager_group_membership (manager_id, group_id)
                                VALUES ($1, $2)
                            """, manager_id, group_id)

                return True
        except Exception as e:
            logger.error(f"Error updating manager: {e}")
            return False

    async def update_manager_password(self, manager_id: int, new_password: str) -> bool:
        """Обновление пароля менеджера"""
        try:
            from hashlib import sha256
            password_hash = sha256(new_password.encode()).hexdigest()

            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema_admin}.managers 
                    SET password_hash = $1
                    WHERE id = $2
                """, password_hash, manager_id)
                return True
        except Exception as e:
            logger.error(f"Error updating manager password: {e}")
            return False

    async def get_all_managers(self) -> list:
        """Получить всех менеджеров с группами"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT m.*, array_agg(g.name) as groups
                    FROM {self.db_schema_admin}.managers m
                    LEFT JOIN {self.db_schema_admin}.manager_group_membership mgm ON m.id = mgm.manager_id
                    LEFT JOIN {self.db_schema_admin}.manager_groups g ON mgm.group_id = g.id
                    GROUP BY m.id
                    ORDER BY m.id
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting managers: {e}")
            return []

    # database.py - добавить в класс Database

    async def save_user_message(self, user_id: int, username: str,
                                message_text: str = None, file_type: str = None,
                                file_id: str = None, direction: str = 'incoming') -> int:
        """Сохранить сообщение пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Проверяем, существует ли таблица
                try:
                    msg_id = await conn.fetchval(f"""
                        INSERT INTO {self.db_schema}.user_messages 
                        (user_id, username, direction, message_text, file_type, file_id, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        RETURNING id
                    """, user_id, username, direction, message_text, file_type, file_id)
                    return msg_id
                except Exception as e:
                    # Если таблицы нет, создаем
                    if 'relation' in str(e) and 'does not exist' in str(e):
                        await conn.execute(f"""
                            CREATE TABLE IF NOT EXISTS {self.db_schema}.user_messages (
                                id SERIAL PRIMARY KEY,
                                user_id BIGINT NOT NULL,
                                username TEXT NOT NULL,
                                manager_id INTEGER,
                                direction TEXT NOT NULL,
                                message_text TEXT,
                                file_type TEXT,
                                file_id TEXT,
                                created_at TIMESTAMP DEFAULT NOW(),
                                read_at TIMESTAMP,
                                replied_at TIMESTAMP
                            )
                        """)
                        await conn.execute(f"""
                            CREATE INDEX IF NOT EXISTS idx_user_messages_user_id 
                            ON {self.db_schema}.user_messages(user_id)
                        """)
                        await conn.execute(f"""
                            CREATE INDEX IF NOT EXISTS idx_user_messages_created_at 
                            ON {self.db_schema}.user_messages(created_at)
                        """)
                        # Повторная вставка
                        msg_id = await conn.fetchval(f"""
                            INSERT INTO {self.db_schema}.user_messages 
                            (user_id, username, direction, message_text, file_type, file_id, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW())
                            RETURNING id
                        """, user_id, username, direction, message_text, file_type, file_id)
                        return msg_id
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error saving user message: {e}")
            return 0

    async def save_user_messages_bulk(self, messages_data: list) -> bool:
        """Массовое сохранение сообщений за один запрос к БД"""
        if not messages_data:
            return True

        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    INSERT INTO {self.db_schema}.user_messages 
                    (user_id, username, direction, message_text, file_type, file_id, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """
                await conn.executemany(query, messages_data)
                return True
        except Exception as e:
            logger.error(f"Error bulk saving messages: {e}")
            return False

    async def get_user_conversations(self) -> list:
        """Получить список всех активных чатов (включая вопросы)"""
        try:
            async with self.pool.acquire() as conn:
                # ИСПРАВЛЕНИЕ 2 и 4: Джоиним профили пользователей, чтобы получать реальные Имя и Ник
                messages = await conn.fetch(f"""
                    SELECT 
                        m.user_id,
                        MAX(COALESCE(p.username, m.username)) as username,
                        MAX(p.full_name) as full_name,
                        MAX(m.created_at) as last_message_time,
                        STRING_AGG(m.message_text, ' ') as all_messages,
                        COUNT(*) FILTER (WHERE m.direction = 'incoming' AND m.read_at IS NULL) as unread_count
                    FROM {self.db_schema}.user_messages m
                    LEFT JOIN {self.db_schema_config}.user_profiles p ON m.user_id = p.user_id
                    GROUP BY m.user_id
                """)

                pr_questions = await conn.fetch(f"""
                    SELECT 
                        q.user_id,
                        MAX(COALESCE(p.username, q.username)) as username,
                        MAX(p.full_name) as full_name,
                        MAX(q.created_at) as last_message_time,
                        STRING_AGG(q.question, ' ') as all_messages,
                        0 as unread_count
                    FROM {self.db_schema_pr}.pr_questions q
                    LEFT JOIN {self.db_schema_config}.user_profiles p ON q.user_id = p.user_id
                    GROUP BY q.user_id
                """)

                event_questions = await conn.fetch(f"""
                    SELECT 
                        q.user_id,
                        MAX(COALESCE(p.username, q.username)) as username,
                        MAX(p.full_name) as full_name,
                        MAX(q.created_at) as last_message_time,
                        STRING_AGG(q.question, ' ') as all_messages,
                        0 as unread_count
                    FROM {self.db_schema_event}.event_questions q
                    LEFT JOIN {self.db_schema_config}.user_profiles p ON q.user_id = p.user_id
                    GROUP BY q.user_id
                """)

                travel_questions = await conn.fetch(f"""
                    SELECT 
                        q.user_id,
                        MAX(COALESCE(p.username, q.username)) as username,
                        MAX(p.full_name) as full_name,
                        MAX(q.created_at) as last_message_time,
                        STRING_AGG(q.question, ' ') as all_messages,
                        0 as unread_count
                    FROM {self.db_schema_travel}.travel_questions q
                    LEFT JOIN {self.db_schema_config}.user_profiles p ON q.user_id = p.user_id
                    GROUP BY q.user_id
                """)

                all_users = {}

                def update_user_dict(row, prefix=""):
                    user_id = row['user_id']
                    msg_preview = f"{prefix} {row['all_messages'][:80]}" if prefix and row['all_messages'] else (
                        row['all_messages'][:100] if row['all_messages'] else '')

                    if user_id not in all_users:
                        all_users[user_id] = {
                            'user_id': user_id,
                            'username': row['username'],
                            'full_name': row['full_name'],
                            'last_message_time': row['last_message_time'],
                            'last_message': msg_preview,
                            'unread_count': row['unread_count']
                        }
                    else:
                        if row['last_message_time'] and (
                                not all_users[user_id]['last_message_time'] or row['last_message_time'] >
                                all_users[user_id]['last_message_time']):
                            all_users[user_id]['last_message_time'] = row['last_message_time']
                            all_users[user_id]['last_message'] = msg_preview
                        all_users[user_id]['unread_count'] += row['unread_count']

                for row in messages: update_user_dict(row)
                for row in pr_questions: update_user_dict(row, "[Вопрос PR]")
                for row in event_questions: update_user_dict(row, "[Вопрос EVENT]")
                for row in travel_questions: update_user_dict(row, "[Вопрос TRAVEL]")

                result = list(all_users.values())
                result.sort(key=lambda x: x.get('last_message_time') or datetime.min, reverse=True)

                return result
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []

    async def get_user_messages(self, user_id: int, limit: int = 50) -> list:
        """Получить историю сообщений пользователя (включая вопросы)"""
        try:
            async with self.pool.acquire() as conn:
                # Получаем обычные сообщения
                messages = await conn.fetch(f"""
                    SELECT 
                        id, user_id, username, manager_id, direction, 
                        message_text, file_type, file_id, created_at, read_at,
                        'message' as source_type, NULL as category
                    FROM {self.db_schema}.user_messages
                    WHERE user_id = $1
                """, user_id)

                # Получаем PR вопросы
                pr_questions = await conn.fetch(f"""
                    SELECT 
                        id, user_id, username, NULL as manager_id,
                        'incoming' as direction,
                        question as message_text,
                        NULL as file_type, NULL as file_id, created_at, NULL as read_at,
                        'pr_question' as source_type, category
                    FROM {self.db_schema_pr}.pr_questions
                    WHERE user_id = $1
                """, user_id)

                # Получаем EVENT вопросы
                event_questions = await conn.fetch(f"""
                    SELECT 
                        id, user_id, username, NULL as manager_id,
                        'incoming' as direction,
                        question as message_text,
                        NULL as file_type, NULL as file_id, created_at, NULL as read_at,
                        'event_question' as source_type, category
                    FROM {self.db_schema_event}.event_questions
                    WHERE user_id = $1
                """, user_id)

                # Получаем TRAVEL вопросы
                travel_questions = await conn.fetch(f"""
                    SELECT 
                        id, user_id, username, NULL as manager_id,
                        'incoming' as direction,
                        question as message_text,
                        NULL as file_type, NULL as file_id, created_at, NULL as read_at,
                        'travel_question' as source_type, category
                    FROM {self.db_schema_travel}.travel_questions
                    WHERE user_id = $1
                """, user_id)

                # Объединяем все
                all_messages = []
                for row in messages:
                    msg = dict(row)
                    msg['category'] = None
                    all_messages.append(msg)
                for row in pr_questions:
                    all_messages.append(dict(row))
                for row in event_questions:
                    all_messages.append(dict(row))
                for row in travel_questions:
                    all_messages.append(dict(row))

                # Сортируем по времени
                all_messages.sort(key=lambda x: x['created_at'], reverse=True)

                return all_messages[:limit]
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    async def mark_messages_read(self, user_id: int, manager_id: int) -> bool:
        """Отметить сообщения как прочитанные"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema}.user_messages
                    SET read_at = NOW(), manager_id = $1
                    WHERE user_id = $2 AND direction = 'incoming' AND read_at IS NULL
                """, manager_id, user_id)
                return True
        except Exception as e:
            logger.error(f"Error marking messages read: {e}")
            return False

    async def close(self):
        """Закрыть пул соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")


# Глобальный экземпляр
db = Database()