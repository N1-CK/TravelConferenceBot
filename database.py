import logging
import os
from typing import List, Dict

import asyncpg
from dotenv import load_dotenv

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
            self.db_schema = os.getenv('DB_SCHEMA', 'conference')

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
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.whitelist (
                        username TEXT PRIMARY KEY,
                        telegram_id BIGINT,
                        company TEXT,
                        role TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

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
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.pr_banner_requests (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        full_name TEXT,
                        position TEXT,
                        company TEXT,
                        language TEXT,
                        photo_required BOOLEAN,
                        photo_file_id TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # EVENT таблицы
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.event_certificates (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        full_name TEXT,
                        position TEXT,
                        company TEXT,
                        company_legal TEXT,
                        addressee TEXT,
                        dates TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # TRAVEL таблицы
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.travel_visa_requests (
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
                        username TEXT PRIMARY KEY REFERENCES {self.db_schema}.whitelist(username),
                        flag BOOLEAN DEFAULT TRUE,
                        company TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Рестораны
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.restaurants (
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
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.bookings (
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
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Отчеты
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.reports (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL,
                        company TEXT NOT NULL,
                        meeting_date TEXT NOT NULL,
                        manager TEXT NOT NULL,
                        partner TEXT NOT NULL,
                        result TEXT,
                        budget TEXT DEFAULT '0',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # После существующих таблиц добавить:

                    # Вопросы к EVENT
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.event_questions (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        category TEXT,
                        question TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Вопросы к PR
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.pr_questions (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        category TEXT,
                        question TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.pr_business_cards (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        full_name TEXT,
                        position_en TEXT,
                        company TEXT,
                        contacts TEXT,
                        brand_style BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    # Вопросы к Travel
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.travel_questions (
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
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.user_hotels (
                                    id SERIAL PRIMARY KEY,
                                    username TEXT NOT NULL,
                                    conference TEXT NOT NULL,
                                    hotel_name TEXT,
                                    hotel_address TEXT,
                                    hotel_link TEXT,
                                    hotel_dates TEXT,
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
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_company (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT NOT NULL,
                        company TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT NOW()
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

                    # Логи статуса бота
                    f'''
                    CREATE SCHEMA IF NOT EXISTS systemcheck_bot;
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
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.admin_users (
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

                # Таблица ролей для обычных пользователей
                await conn.execute(f"""
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.user_roles (
                                    user_id BIGINT PRIMARY KEY,
                                    username TEXT NOT NULL,
                                    role TEXT NOT NULL DEFAULT 'user',
                                    permissions JSONB DEFAULT '{{}}'::jsonb,
                                    assigned_by TEXT,
                                    assigned_at TIMESTAMP DEFAULT NOW(),
                                    updated_at TIMESTAMP DEFAULT NOW()
                                )
                            """)

                # Таблица сессий админки
                await conn.execute(f"""
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.admin_sessions (
                                    id SERIAL PRIMARY KEY,
                                    admin_id INTEGER REFERENCES {self.db_schema}.admin_users(id),
                                    session_token TEXT UNIQUE,
                                    ip_address TEXT,
                                    user_agent TEXT,
                                    created_at TIMESTAMP DEFAULT NOW(),
                                    expires_at TIMESTAMP
                                )
                            """)

                # Таблица логов действий админов
                await conn.execute(f"""
                                CREATE TABLE IF NOT EXISTS {self.db_schema}.admin_logs (
                                    id SERIAL PRIMARY KEY,
                                    admin_id INTEGER REFERENCES {self.db_schema}.admin_users(id),
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
                                INSERT INTO {self.db_schema}.admin_users 
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

    async def check_affiliate_auth(self, username: str) -> bool:
        """Проверка авторизации Affiliate Bot с временем жизни"""
        try:
            async with self.pool.acquire() as conn:
                # Проверяем, есть ли пользователь в whitelist и активен ли он
                result = await conn.fetchval(
                    f"""
                    SELECT au.flag 
                    FROM {self.db_schema}.affiliate_auth_users au
                    JOIN {self.db_schema}.whitelist w ON au.username = w.username
                    WHERE au.username = $1 AND w.is_active = TRUE
                    """,
                    username
                )
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking affiliate auth: {e}")
            return False

    async def add_affiliate_user(self, username: str, company: str) -> bool:
        """Добавление пользователя Affiliate Bot"""
        try:
            async with self.pool.acquire() as conn:
                # Добавляем в whitelist если нет
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.whitelist (username, company)
                    VALUES ($1, $2)
                    ON CONFLICT (username) DO UPDATE
                    SET is_active = TRUE, company = EXCLUDED.company
                """, username, company)

                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.affiliate_auth_users (username, company, flag)
                    VALUES ($1, $2, TRUE)
                    ON CONFLICT (username) DO UPDATE
                    SET flag = TRUE, company = EXCLUDED.company
                """, username, company)

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
                        FROM {db.db_schema}.restaurants
                        WHERE created_at = (select max(created_at) from {db.db_schema}.restaurants)
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
                    SELECT COUNT(*) FROM {self.db_schema}.bookings 
                    WHERE username = $1 AND datetime = $2 AND partner = $3
                    """,
                    username, datetime_str, partner
                )
                return count > 0
        except Exception as e:
            logger.error(f"Error checking duplicate booking: {e}")
            return False

    async def get_restaurants_by_city(self, city: str) -> list:
        """Получение ресторанов по городу"""
        try:
            async with self.pool.acquire() as conn:
                records = await conn.fetch(f"""
                    SELECT id, restaurant, address, cost, link, comment
                    FROM {db.db_schema}.restaurants
                    WHERE city = $1 
                    AND created_at = (
                        SELECT MAX(created_at) FROM {db.db_schema}.restaurants
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
                    FROM {self.db_schema}.restaurants
                    WHERE id = $1
                """, rest_id)
                return record
        except Exception as e:
            logger.error(f"Error getting restaurant: {e}")
            return None

    # Добавить в класс Database после существующих методов

    async def save_certificate_request(self, data: dict) -> bool:
        """Сохранение заявки на справку-вызов"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.event_certificates 
                    (username, user_id, full_name, position, company, company_legal, addressee, dates)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                                   data['username'],
                                   data['user_id'],
                                   data['full_name'],
                                   data.get('position', ''),
                                   data.get('company', ''),
                                   data.get('company_legal', ''),
                                   data.get('addressee', ''),
                                   data.get('dates', '')
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving certificate: {e}")
            return False

    async def save_event_question(self, data: dict) -> bool:
        """Сохранение вопроса к EVENT-менеджеру"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.event_questions 
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

    async def save_visa_request(self, data: dict) -> bool:
        """Сохранение заявки на визу"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.travel_visa_requests 
                    (username, user_id, visa_status, passport_data, city_from, city_to, needs_baggage, preferences)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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

    async def save_banner_request(self, data: dict) -> bool:
        """Сохранение заявки на баннер"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.pr_banner_requests 
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
                    INSERT INTO {self.db_schema}.pr_business_cards 
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
                    INSERT INTO {self.db_schema}.bookings 
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
                    SELECT * FROM {self.db_schema}.bookings 
                    WHERE username = $1 
                    ORDER BY created_at DESC
                """, username)
                return records
        except Exception as e:
            logger.error(f"Error getting bookings: {e}")
            return []

    async def save_pr_question(self, data: dict) -> bool:
        """Сохранение вопроса к PR-менеджеру"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.pr_questions 
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
            logger.error(f"Error saving PR question: {e}")
            return False

    async def save_travel_question(self, data: dict) -> bool:
        """Сохранение вопроса к тревел-менеджеру"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.travel_questions 
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
        """Сохранение согласия пользователя"""
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

                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.whitelist (username, telegram_id, is_active)
                    VALUES ($1, $2, TRUE)
                    ON CONFLICT (username) DO UPDATE
                    SET telegram_id = EXCLUDED.telegram_id,
                        is_active = TRUE,
                        updated_at = NOW()
                """, username, user_id)

                return True
        except Exception as e:
            logger.error(f"Error saving user agreement: {e}")
            return False

    async def get_incomplete_forms(self):
        """Получение пользователей с незаполненными формами (для напоминаний)"""
        try:
            async with self.pool.acquire() as conn:
                # Здесь логика для проверки незаполненных форм
                return []
        except Exception as e:
            logger.error(f"Error getting incomplete forms: {e}")
            return []


    async def get_user_flights(self, username: str) -> List[str]:
        """Get user's conferences from database (using travelconference_bot schema)"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT DISTINCT conference 
                    FROM travel_bot.flights 
                    WHERE telegram_name = $1
                    ORDER BY conference
                """
                result = await conn.fetch(query, username)
                return [row['conference'] for row in result]
        except Exception as e:
            logger.error(f"Error getting user flights: {e}")
            return []

    async def get_flight_details(self, username: str, conference: str) -> List[Dict]:
        """Get flight details for specific conference"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT * 
                    FROM travel_bot.flights 
                    WHERE telegram_name = $1 AND conference = $2
                    ORDER BY departure_date, departure_time
                """
                result = await conn.fetch(query, username, conference)
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting flight details: {e}")
            return []

    async def save_flight_request(self, flight_data: Dict) -> bool:
        """Save flight request to database"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    INSERT INTO {self.db_schema}.travel_visa_requests 
                    (username, user_id, visa_status, passport_data, city_from, city_to, needs_baggage, preferences)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """
                await conn.execute(
                    query,
                    flight_data['username'],
                    flight_data['user_id'],
                    flight_data.get('visa_status'),
                    flight_data['passport_data'],
                    flight_data['city_from'],
                    flight_data['city_to'],
                    flight_data['needs_baggage'],
                    flight_data['preferences']
                )
                return True
        except Exception as e:
            logger.error(f"Error saving flight request: {e}")
            return False

    async def get_hotel_info(self, conference: str) -> Dict:
        """Get hotel information for conference"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT hotel, address, site 
                    FROM travel_bot.hotels 
                    WHERE conference = $1
                """
                result = await conn.fetchrow(query, conference)
                return dict(result) if result else {}
        except Exception as e:
            logger.error(f"Error getting hotel info: {e}")
            return {}

    async def get_airline_url(self, airline: str) -> str:
        """Get check-in URL for airline"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT link 
                    FROM travel_bot.airlines 
                    WHERE airline= $1
                """
                result = await conn.fetchval(query, airline)
                return result or ""
        except Exception as e:
            logger.error(f"Error getting airline URL: {e}")
            return ""

    # Методы для отчетов
    async def save_report(self, report_data: dict) -> bool:
        """Сохранение отчета"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.reports 
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

    async def sync_hotels_data(self, hotels_data: list):
        """Синхронизация данных об отелях"""
        try:
            async with self.pool.acquire() as conn:
                # Удаляем старые данные для пользователей
                usernames = list(set([h['username'] for h in hotels_data]))
                for username in usernames:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema}.user_hotels 
                        WHERE username = $1
                    """, username)

                # Вставляем новые данные
                for hotel in hotels_data:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema}.user_hotels 
                        (username, conference, hotel_name, hotel_address, hotel_link, hotel_dates)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                                       hotel['username'], hotel['conference'], hotel['hotel_name'],
                                       hotel['hotel_address'], hotel['hotel_link'], hotel['hotel_dates'])

                return True
        except Exception as e:
            logger.error(f"Error syncing hotels data: {e}")
            return False

    async def check_whitelist(self, username: str) -> bool:
        """Проверка пользователя в whitelist"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    f"""
                    SELECT is_active 
                    FROM {self.db_schema}.whitelist 
                    WHERE username = $1
                    """,
                    username
                )
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking whitelist for {username}: {e}")
            return False

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

    # ===== МЕТОДЫ ДЛЯ GROUP TRAVEL BOT (схема travel_bot) =====

    async def get_user_flights_travel(self, username: str) -> List[str]:
        """Получить конференции пользователя из схемы travel_bot"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                        SELECT DISTINCT conference
                        FROM travel_bot.flights
                        WHERE telegram_name like '%{username}%'
                        ORDER BY conference \
                        """
                print(f"Executing query for username: {username}")
                result = await conn.fetch(query)
                print(f"Query result: {result}")
                return [row['conference'] for row in result]
        except Exception as e:
            print(f"Error getting user flights from travel_bot: {e}")
            return []

    async def get_flight_details_travel(self, username: str, conference: str) -> List[Dict]:
        """Получить детали рейсов из схемы travel_bot"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                        SELECT *
                        FROM travel_bot.flights
                        WHERE telegram_name like '%{username}%' \
                          AND conference like '%{conference}%'
                        ORDER BY departure_date, departure_time \
                        """
                result = await conn.fetch(query)
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting flight details from travel_bot: {e}")
            return []

    async def get_hotel_info_travel(self, conference: str) -> Dict:
        """Получить информацию об отеле из схемы travel_bot"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                        SELECT hotel, address, site
                        FROM travel_bot.hotels
                        WHERE conference like '%{conference}%'
                        LIMIT 1 \
                        """
                result = await conn.fetchrow(query)
                return dict(result) if result else {}
        except Exception as e:
            logger.error(f"Error getting hotel info from travel_bot: {e}")
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

    async def save_per_diem_request(self, data: dict) -> bool:
        """Сохранение заявки на суточные"""
        try:
            async with self.pool.acquire() as conn:
                # Сначала создайте таблицу если её нет
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.travel_per_diem_requests (
                        id SERIAL PRIMARY KEY,
                        username TEXT,
                        user_id BIGINT,
                        payment_details TEXT,
                        currency TEXT,
                        comments TEXT,
                        consent_given BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.travel_per_diem_requests 
                    (username, user_id, payment_details, currency, comments, consent_given)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                                   data['username'], data['user_id'],
                                   data.get('payment_details'),
                                   data.get('currency'),
                                   data.get('comments', '-'),
                                   data.get('consent_given', False)
                                   )
                return True
        except Exception as e:
            logger.error(f"Error saving per diem request: {e}")
            return False

    async def set_user_company(self, user_id: int, username: str, company: str) -> bool:
        """Установить компанию пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_company (user_id, username, company, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET company = EXCLUDED.company,
                        username = EXCLUDED.username,
                        updated_at = NOW()
                """, user_id, username, company)
                return True
        except Exception as e:
            logger.error(f"Error setting user company: {e}")
            return False

    async def get_user_company(self, user_id: int) -> str:
        """Получить компанию пользователя"""
        try:
            async with self.pool.acquire() as conn:
                company = await conn.fetchval(f"""
                    SELECT company FROM {self.db_schema}.user_profiles
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
                        FROM {self.db_schema}.user_company
                        WHERE company = $1
                    """
                    rows = await conn.fetch(query, company)
                else:
                    query = f"""
                        SELECT user_id, username, company 
                        FROM {self.db_schema}.user_company
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
                    FROM {self.db_schema}.user_company
                    ORDER BY company
                """)
                return [row['company'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return []

    # Добавить в класс Database:

    async def save_user_registration(self, user_data: dict) -> bool:
        """Сохранение данных регистрации пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем таблицу если нет
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_profiles (
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
                    INSERT INTO {self.db_schema}.user_profiles 
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

                # Также обновляем user_company для совместимости
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_company (user_id, username, company, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET company = EXCLUDED.company,
                        username = EXCLUDED.username,
                        updated_at = NOW()
                """, user_data['user_id'], user_data['username'], user_data.get('company'))

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
                    FROM {self.db_schema}.user_profiles 
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

    async def sync_whitelist_from_google_sheets(self, spreadsheet_name: str = "Whitelist") -> bool:
        """
        Синхронизация whitelist из Google Sheets
        """
        try:
            from utility.sync import GoogleSheetsSync
            sync = GoogleSheetsSync()

            if not await sync.connect_to_google_sheets():
                logger.error("Failed to connect to Google Sheets")
                return False


            # Открываем таблицу
            sh = sync.gc.open(spreadsheet_name)
            worksheets = sh.worksheets()

            async with self.pool.acquire() as conn:
                # Очищаем существующие записи для обновляемых пользователей
                await conn.execute(f"TRUNCATE TABLE {self.db_schema}.whitelist RESTART IDENTITY CASCADE")

                all_users = []

                # Проходим по всем листам (конференциям)
                for worksheet in worksheets:
                    conference_name = worksheet.title
                    records = worksheet.get_all_records()

                    for record in records:
                        username = record.get('TG_username', '').strip()
                        if not username or username.lower() == 'tg_username':
                            continue

                        # Собираем данные пользователя
                        user_data = {
                            'username': username,
                            'conference': conference_name,
                            'trip_start': record.get('Дата начала поездки', ''),
                            'trip_end': record.get('Дата окончания поездки', ''),
                            'conf_start': record.get('Даты начала конференции', ''),
                            'conf_end': record.get('Дата окончания конференции', ''),
                            'city': record.get('Город конференции', '')
                        }

                        all_users.append(user_data)

                        # Добавляем/обновляем пользователя в whitelist
                        await conn.execute(f"""
                            INSERT INTO {self.db_schema}.whitelist 
                            (username, company, is_active, created_at, updated_at)
                            VALUES ($1, $2, TRUE, NOW(), NOW())
                            ON CONFLICT (username) DO UPDATE
                            SET is_active = TRUE,
                                company = EXCLUDED.company,
                                updated_at = NOW()
                        """, username, conference_name)

                        # Сохраняем конференции пользователя
                        await conn.execute(f"""
                            INSERT INTO {self.db_schema}.user_conferences 
                            (username, conference_name, trip_start_date, trip_end_date, 
                             conference_start_date, conference_end_date, city)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            ON CONFLICT (username, conference_name) DO UPDATE
                            SET trip_start_date = EXCLUDED.trip_start_date,
                                trip_end_date = EXCLUDED.trip_end_date,
                                conference_start_date = EXCLUDED.conference_start_date,
                                conference_end_date = EXCLUDED.conference_end_date,
                                city = EXCLUDED.city,
                                updated_at = NOW()
                        """,
                                           username,
                                           conference_name,
                                           user_data['trip_start'],
                                           user_data['trip_end'],
                                           user_data['conf_start'],
                                           user_data['conf_end'],
                                           user_data['city']
                                           )

                logger.info(f"✅ Synced {len(all_users)} users from {len(worksheets)} conferences")
                return True

        except Exception as e:
            logger.error(f"Error syncing whitelist from Google Sheets: {e}")
            return False

    async def get_user_conferences(self, username: str) -> List[Dict]:
        """
        Получить все конференции пользователя из whitelist
        """
        try:
            async with self.pool.acquire() as conn:
                try:
                    rows = await conn.fetch(f"""
                        SELECT conference_name, trip_start_date, trip_end_date,
                               conference_start_date, conference_end_date, city
                        FROM {self.db_schema}.user_conferences
                        WHERE username = $1
                        ORDER BY conference_start_date
                    """, username)

                    if rows:
                        return [dict(row) for row in rows]
                except Exception as e:
                    logger.warning(f"user_conferences table might not exist: {e}")

                # Fallback: получаем из whitelist по company (для обратной совместимости)
                company = await conn.fetchval(f"""
                    SELECT company FROM {self.db_schema}.whitelist WHERE username = $1
                """, username)

                if company:
                    return [{
                        'conference_name': company,
                        'city': '',
                        'conference_start_date': '',
                        'conference_end_date': ''
                    }]

                return []

        except Exception as e:
            logger.error(f"Error getting user conferences: {e}")
            return []

    async def get_user_active_conferences(self, username: str) -> List[str]:
        """
        Получить список названий активных конференций пользователя
        """
        conferences = await self.get_user_conferences(username)
        return [conf['conference_name'] for conf in conferences if conf.get('conference_name')]

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
                    table = f"{self.db_schema}.travel_visa_requests"
                    status_col = "status"
                elif request_type == "flight":
                    table = f"{self.db_schema}.travel_visa_requests"  # временно, нужна отдельная таблица
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
                    SELECT id FROM {self.db_schema}.admin_users WHERE username = $1
                """, username)

                if exists:
                    return False

                perms = permissions or {}
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.admin_users 
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
                    FROM {self.db_schema}.admin_users 
                    WHERE username = $1 AND password_hash = $2 AND is_active = TRUE
                """, username, password_hash)

                if admin:
                    # Обновляем время последнего входа
                    await conn.execute(f"""
                        UPDATE {self.db_schema}.admin_users 
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
                    FROM {self.db_schema}.admin_users
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
                        UPDATE {self.db_schema}.admin_users 
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
                    DELETE FROM {self.db_schema}.admin_users WHERE id = $1
                """, admin_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting admin user: {e}")
            return False

    async def set_user_role(self, user_id: int, username: str, role: str,
                            permissions: dict = None, assigned_by: str = None) -> bool:
        """Установка роли для пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_roles 
                    (user_id, username, role, permissions, assigned_by, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET role = EXCLUDED.role,
                        permissions = EXCLUDED.permissions,
                        assigned_by = EXCLUDED.assigned_by,
                        updated_at = NOW()
                """, user_id, username, role, permissions or {}, assigned_by)

                return True
        except Exception as e:
            logger.error(f"Error setting user role: {e}")
            return False

    async def get_user_role(self, user_id: int) -> dict:
        """Получить роль пользователя"""
        try:
            async with self.pool.acquire() as conn:
                role = await conn.fetchrow(f"""
                    SELECT role, permissions, assigned_at
                    FROM {self.db_schema}.user_roles
                    WHERE user_id = $1
                """, user_id)

                if role:
                    return dict(role)
                return {'role': 'user', 'permissions': {}}
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return {'role': 'user', 'permissions': {}}

    async def log_admin_action(self, admin_id: int, action: str, details: dict = None,
                               ip_address: str = None) -> bool:
        """Логирование действий администратора"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.admin_logs 
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
                    FROM {self.db_schema}.admin_users
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
                    SELECT * FROM {self.db_schema}.travel_visa_requests 
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
                    SELECT * FROM {self.db_schema}.pr_banner_requests 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting banner requests: {e}")
            return []

    async def get_all_certificates(self) -> list:
        """Получить все заявки на справки"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema}.event_certificates 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting certificates: {e}")
            return []

    async def create_groups_tables(self):
        """Создание таблиц для групп и функций"""
        try:
            async with self.pool.acquire() as conn:
                # Таблица групп
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_groups (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        color TEXT DEFAULT '#667eea',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Таблица функций
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.features (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        code TEXT NOT NULL UNIQUE,
                        description TEXT,
                        icon TEXT DEFAULT 'bi-grid',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Таблица связи пользователей с группами
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.user_group_membership (
                        user_id BIGINT NOT NULL,
                        group_id INTEGER NOT NULL REFERENCES {self.db_schema}.user_groups(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (user_id, group_id)
                    )
                """)

                # Таблица связи групп с функциями
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema}.group_features (
                        group_id INTEGER NOT NULL REFERENCES {self.db_schema}.user_groups(id) ON DELETE CASCADE,
                        feature_id INTEGER NOT NULL REFERENCES {self.db_schema}.features(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (group_id, feature_id)
                    )
                """)

                # Добавить базовые функции, если их нет
                basic_features = [
                    ('PR-баннеры', 'pr_banner', 'Заказ баннеров для конференций', 'bi-megaphone'),
                    ('PR-визитки', 'pr_business_cards', 'Заказ визиток', 'bi-card-text'),
                    ('Справки-вызовы', 'event_certificate', 'Заказ справок для участия', 'bi-file-text'),
                    ('Визы', 'travel_visa', 'Оформление виз', 'bi-passport'),
                    ('Авиабилеты', 'travel_flights', 'Бронирование авиабилетов', 'bi-airplane'),
                    ('Отели', 'travel_hotels', 'Бронирование отелей', 'bi-building'),
                    ('Суточные', 'travel_per_diem', 'Оформление суточных', 'bi-cash'),
                    ('Бронирование столиков', 'affiliate_bookings', 'Бронь в ресторанах', 'bi-calendar-check'),
                    ('Отчеты', 'affiliate_reports', 'Отчеты о встречах', 'bi-file-earmark-text')
                ]

                for name, code, desc, icon in basic_features:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema}.features (name, code, description, icon)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (code) DO NOTHING
                    """, name, code, desc, icon)

                return True
        except Exception as e:
            logger.error(f"Error creating groups tables: {e}")
            return False

    async def get_all_groups(self) -> list:
        """Получить все группы с количеством пользователей и функций"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        g.*,
                        COUNT(DISTINCT ugm.user_id) as users_count,
                        COUNT(DISTINCT gf.feature_id) as features_count
                    FROM {self.db_schema}.user_groups g
                    LEFT JOIN {self.db_schema}.user_group_membership ugm ON g.id = ugm.group_id
                    LEFT JOIN {self.db_schema}.group_features gf ON g.id = gf.group_id
                    GROUP BY g.id
                    ORDER BY g.name
                """)

                groups = []
                for row in rows:
                    group = dict(row)
                    # Получаем функции группы
                    features = await conn.fetch(f"""
                        SELECT f.* 
                        FROM {self.db_schema}.features f
                        JOIN {self.db_schema}.group_features gf ON f.id = gf.feature_id
                        WHERE gf.group_id = $1
                    """, row['id'])
                    group['features'] = [dict(f) for f in features]
                    groups.append(group)

                return groups
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []

    async def get_group(self, group_id: int) -> dict:
        """Получить информацию о группе"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT * FROM {self.db_schema}.user_groups WHERE id = $1
                """, group_id)
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error getting group: {e}")
            return {}

    async def add_group(self, name: str, description: str = None, color: str = '#667eea') -> bool:
        """Добавить новую группу"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_groups (name, description, color)
                    VALUES ($1, $2, $3)
                """, name, description, color)
                return True
        except Exception as e:
            logger.error(f"Error adding group: {e}")
            return False

    async def update_group(self, group_id: int, name: str = None,
                           description: str = None, color: str = None) -> bool:
        """Обновить информацию о группе"""
        try:
            async with self.pool.acquire() as conn:
                updates = []
                values = []
                i = 1

                if name is not None:
                    updates.append(f"name = ${i}")
                    values.append(name)
                    i += 1
                if description is not None:
                    updates.append(f"description = ${i}")
                    values.append(description)
                    i += 1
                if color is not None:
                    updates.append(f"color = ${i}")
                    values.append(color)
                    i += 1

                updates.append("updated_at = NOW()")

                if updates:
                    values.append(group_id)
                    query = f"""
                        UPDATE {self.db_schema}.user_groups 
                        SET {', '.join(updates)}
                        WHERE id = ${i}
                    """
                    await conn.execute(query, *values)

                return True
        except Exception as e:
            logger.error(f"Error updating group: {e}")
            return False

    async def delete_group(self, group_id: int) -> bool:
        """Удалить группу"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    DELETE FROM {self.db_schema}.user_groups WHERE id = $1
                """, group_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return False

    async def get_group_users(self, group_id: int) -> list:
        """Получить пользователей группы"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT up.user_id, up.username, up.full_name, up.company
                    FROM {self.db_schema}.user_profiles up
                    JOIN {self.db_schema}.user_group_membership ugm ON up.user_id = ugm.user_id
                    WHERE ugm.group_id = $1
                    ORDER BY up.username
                """, group_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting group users: {e}")
            return []

    async def add_user_to_group(self, user_id: int, group_id: int) -> bool:
        """Добавить пользователя в группу"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_group_membership (user_id, group_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                """, user_id, group_id)
                return True
        except Exception as e:
            logger.error(f"Error adding user to group: {e}")
            return False

    async def remove_user_from_group(self, user_id: int, group_id: int) -> bool:
        """Удалить пользователя из группы"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    DELETE FROM {self.db_schema}.user_group_membership
                    WHERE user_id = $1 AND group_id = $2
                """, user_id, group_id)
                return True
        except Exception as e:
            logger.error(f"Error removing user from group: {e}")
            return False

    async def get_user_groups(self, user_id: int) -> list:
        """Получить группы пользователя"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT g.*
                    FROM {self.db_schema}.user_groups g
                    JOIN {self.db_schema}.user_group_membership ugm ON g.id = ugm.group_id
                    WHERE ugm.user_id = $1
                """, user_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []

    async def get_all_features(self) -> list:
        """Получить все доступные функции"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema}.features
                    ORDER BY name
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting features: {e}")
            return []

    async def add_feature(self, name: str, code: str, description: str = None,
                          icon: str = 'bi-grid') -> bool:
        """Добавить новую функцию"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.features (name, code, description, icon)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        icon = EXCLUDED.icon
                """, name, code, description, icon)
                return True
        except Exception as e:
            logger.error(f"Error adding feature: {e}")
            return False

    async def delete_feature(self, feature_id: int) -> bool:
        """Удалить функцию"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    DELETE FROM {self.db_schema}.features WHERE id = $1
                """, feature_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting feature: {e}")
            return False

    async def assign_features_to_group(self, group_id: int, feature_ids: list) -> bool:
        """Назначить функции группе"""
        try:
            async with self.pool.acquire() as conn:
                # Удаляем старые связи
                await conn.execute(f"""
                    DELETE FROM {self.db_schema}.group_features
                    WHERE group_id = $1
                """, group_id)

                # Добавляем новые
                for feature_id in feature_ids:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema}.group_features (group_id, feature_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, group_id, feature_id)

                return True
        except Exception as e:
            logger.error(f"Error assigning features to group: {e}")
            return False

    async def get_group_features(self, group_id: int) -> list:
        """Получить функции группы"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT f.*
                    FROM {self.db_schema}.features f
                    JOIN {self.db_schema}.group_features gf ON f.id = gf.feature_id
                    WHERE gf.group_id = $1
                """, group_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting group features: {e}")
            return []

    async def get_all_users_with_groups(self) -> list:
        """Получить всех пользователей с их группами и функциями"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        up.user_id,
                        up.username,
                        up.full_name,
                        up.company,
                        up.position
                    FROM {self.db_schema}.user_profiles up
                    ORDER BY up.username
                """)

                users = []
                for row in rows:
                    user = dict(row)

                    # Получаем группы пользователя
                    groups = await conn.fetch(f"""
                        SELECT g.*
                        FROM {self.db_schema}.user_groups g
                        JOIN {self.db_schema}.user_group_membership ugm ON g.id = ugm.group_id
                        WHERE ugm.user_id = $1
                    """, user['user_id'])
                    user['groups'] = [dict(g) for g in groups]
                    user['group_ids'] = [g['id'] for g in groups]

                    # Получаем функции пользователя (через группы)
                    features = await conn.fetch(f"""
                        SELECT DISTINCT f.*
                        FROM {self.db_schema}.features f
                        JOIN {self.db_schema}.group_features gf ON f.id = gf.feature_id
                        JOIN {self.db_schema}.user_group_membership ugm ON gf.group_id = ugm.group_id
                        WHERE ugm.user_id = $1
                    """, user['user_id'])
                    user['features'] = [dict(f) for f in features]

                    users.append(user)

                return users
        except Exception as e:
            logger.error(f"Error getting users with groups: {e}")
            return []

    async def get_all_users_basic(self) -> list:
        """Получить базовую информацию о всех пользователях"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT user_id, username, full_name, company
                    FROM {self.db_schema}.user_profiles
                    ORDER BY username
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users basic: {e}")
            return []

    async def user_has_feature(self, user_id: int, feature_code: str) -> bool:
        """Проверить, имеет ли пользователь доступ к функции"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(f"""
                    SELECT 1
                    FROM {self.db_schema}.user_group_membership ugm
                    JOIN {self.db_schema}.group_features gf ON ugm.group_id = gf.group_id
                    JOIN {self.db_schema}.features f ON gf.feature_id = f.id
                    WHERE ugm.user_id = $1 AND f.code = $2
                    LIMIT 1
                """, user_id, feature_code)
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking user feature: {e}")
            return False

    # Добавить в класс Database после метода get_all_certificates():

    async def get_all_business_cards(self) -> list:
        """Получить все заявки на визитки"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema}.pr_business_cards 
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
                    UPDATE {self.db_schema}.travel_visa_requests 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating visa status: {e}")
            return False

    async def update_banner_status(self, request_id: int, status: str) -> bool:
        """Обновить статус заявки на баннер"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema}.pr_banner_requests 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating banner status: {e}")
            return False

    async def update_certificate_status(self, request_id: int, status: str) -> bool:
        """Обновить статус справки"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.db_schema}.event_certificates 
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                """, status, request_id)
                return True
        except Exception as e:
            logger.error(f"Error updating certificate status: {e}")
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
                    SELECT COUNT(DISTINCT user_id) FROM {self.db_schema}.user_profiles
                """) or 0

                active_today = await conn.fetchval(f"""
                    SELECT COUNT(DISTINCT user_id)
                    FROM {self.db_schema}.user_logs
                    WHERE timestamp > NOW() - INTERVAL '1 day'
                """) or 0

                companies_stats = await conn.fetch(f"""
                    SELECT company, COUNT(DISTINCT user_id) as user_count
                    FROM {self.db_schema}.user_profiles
                    WHERE company IS NOT NULL AND company != ''
                    GROUP BY company
                    ORDER BY user_count DESC
                    LIMIT 5
                """)

                banner_requests = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.pr_banner_requests
                """) or 0

                visa_requests = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema}.travel_visa_requests
                """) or 0

                active_conferences = await conn.fetchval(f"""
                    SELECT COUNT(DISTINCT conference_name)
                    FROM {self.db_schema}.user_conferences
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
                        FROM {self.db_schema}.user_company
                        WHERE company = ANY($1::text[])
                    """
                    rows = await conn.fetch(query, companies)
                else:
                    query = f"""
                        SELECT user_id, username, company
                        FROM {self.db_schema}.user_company
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
                    FROM {self.db_schema}.user_company
                    WHERE user_id = ANY($1::bigint[])
                """
                rows = await conn.fetch(query, user_ids)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users by ids: {e}")
            return []

    async def get_users_by_conference_list(self, conferences: list) -> list:
        """Получить пользователей по списку конференций"""
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT DISTINCT uc.user_id, uc.username, uc.company
                    FROM {self.db_schema}.user_company uc
                    JOIN {self.db_schema}.user_conferences uconf ON uc.username = uconf.username
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
                    FROM {self.db_schema}.user_profiles
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
                    SELECT DISTINCT conference_name as name,
                           COUNT(DISTINCT username) as user_count
                    FROM {self.db_schema}.user_conferences
                    GROUP BY conference_name
                    ORDER BY conference_name
                """)
                if rows:
                    return [dict(row) for row in rows]

                # Fallback: из company
                companies = await self.get_companies_list()
                return [{'name': c, 'user_count': 0} for c in companies]
        except Exception as e:
            logger.error(f"Error getting conferences: {e}")
            return []

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
                    FROM {self.db_schema}.user_profiles up
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
                    for table in ['pr_banner_requests', 'pr_business_cards', 'event_certificates',
                                  'travel_visa_requests']:
                        try:
                            cnt = await conn.fetchval(f"""
                                SELECT COUNT(*) FROM {self.db_schema}.{table} WHERE username = $1
                            """, user['username'])
                            requests_count += cnt
                        except:
                            pass
                    user['requests_count'] = requests_count

                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_user_details_by_id(self, user_id: int) -> dict:
        """Получить детальную информацию о пользователе"""
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(f"""
                    SELECT 
                        up.*,
                        (SELECT MAX(timestamp) FROM {self.db_schema}.user_logs WHERE user_id = up.user_id) as last_active
                    FROM {self.db_schema}.user_profiles up
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
                    ('event_certificates', 'Справка'),
                    ('travel_visa_requests', 'Виза')
                ]
                for table, type_name in request_tables:
                    try:
                        rows = await conn.fetch(f"""
                            SELECT id, created_at, 'pending' as status
                            FROM {self.db_schema}.{table}
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
                                   CREATE TABLE IF NOT EXISTS {self.db_schema}.managers
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
                                   CREATE TABLE IF NOT EXISTS {self.db_schema}.manager_groups
                                   (
                                       id          SERIAL PRIMARY KEY,
                                       name        TEXT UNIQUE NOT NULL,
                                       description TEXT,
                                       created_at  TIMESTAMP DEFAULT NOW()
                                   )
                                   """)

                # Связь менеджеров с группами
                await conn.execute(f"""
                                   CREATE TABLE IF NOT EXISTS {self.db_schema}.manager_group_membership
                                   (
                                       manager_id  INTEGER REFERENCES {self.db_schema}.managers (id) ON DELETE CASCADE,
                                       group_id    INTEGER REFERENCES {self.db_schema}.manager_groups (id) ON DELETE CASCADE,
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
                                       INSERT INTO {self.db_schema}.manager_groups (name, description)
                                       VALUES ($1, $2)
                                       ON CONFLICT (name) DO NOTHING
                                       """, name, desc)

                # Создаем админа по умолчанию, если нет
                from hashlib import sha256
                admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
                admin_hash = sha256(admin_pass.encode()).hexdigest()

                # Добавляем админа
                admin_id = await conn.fetchval(f"""
                                               INSERT INTO {self.db_schema}.managers (username, password_hash, full_name, role)
                                               VALUES ($1, $2, $3, $4)
                                               ON CONFLICT (username) DO NOTHING
                                               RETURNING id
                                               """, 'admin', admin_hash, 'Главный администратор', 'admin')

                # Если админ создан, добавляем его в группу admin
                if admin_id:
                    admin_group_id = await conn.fetchval(f"""
                                                         SELECT id
                                                         FROM {self.db_schema}.manager_groups
                                                         WHERE name = 'admin'
                                                         """)
                    if admin_group_id:
                        await conn.execute(f"""
                                           INSERT INTO {self.db_schema}.manager_group_membership (manager_id, group_id)
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
                                              FROM {self.db_schema}.managers
                                              WHERE username = $1
                                                AND password_hash = $2
                                                AND is_active = TRUE
                                              """, username, password_hash)

                if manager:
                    # Получаем группы менеджера
                    groups = await conn.fetch(f"""
                                              SELECT g.name, g.description
                                              FROM {self.db_schema}.manager_groups g
                                                       JOIN {self.db_schema}.manager_group_membership mgm ON g.id = mgm.group_id
                                              WHERE mgm.manager_id = $1
                                              """, manager['id'])

                    # Обновляем время последнего входа
                    await conn.execute(f"""
                                       UPDATE {self.db_schema}.managers
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
                                                 INSERT INTO {self.db_schema}.managers (username, password_hash, full_name, role)
                                                 VALUES ($1, $2, $3, 'manager')
                                                 RETURNING id
                                                 """, username, password_hash, full_name)

                if manager_id and groups:
                    # Добавляем в группы
                    for group_name in groups:
                        group_id = await conn.fetchval(f"""
                                                       SELECT id
                                                       FROM {self.db_schema}.manager_groups
                                                       WHERE name = $1
                                                       """, group_name)
                        if group_id:
                            await conn.execute(f"""
                                               INSERT INTO {self.db_schema}.manager_group_membership (manager_id, group_id)
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
                                                  FROM {self.db_schema}.managers
                                                  WHERE role = 'admin'
                                                  """)

                if admin_count <= 1:
                    manager = await conn.fetchval(f"""
                                                  SELECT role
                                                  FROM {self.db_schema}.managers
                                                  WHERE id = $1
                                                  """, manager_id)
                    if manager == 'admin':
                        return False

                await conn.execute(f"DELETE FROM {self.db_schema}.managers WHERE id = $1", manager_id)
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
                                        FROM {self.db_schema}.manager_groups
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
                                   FROM {self.db_schema}.manager_group_membership
                                   WHERE manager_id = $1
                                   """, manager_id)

                # Добавляем новые
                for group_name in groups:
                    group_id = await conn.fetchval(f"""
                                                   SELECT id
                                                   FROM {self.db_schema}.manager_groups
                                                   WHERE name = $1
                                                   """, group_name)
                    if group_id:
                        await conn.execute(f"""
                                           INSERT INTO {self.db_schema}.manager_group_membership (manager_id, group_id)
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
                        UPDATE {self.db_schema}.managers 
                        SET full_name = $1
                        WHERE id = $2
                    """, full_name, manager_id)

                if is_active is not None:
                    await conn.execute(f"""
                        UPDATE {self.db_schema}.managers 
                        SET is_active = $1
                        WHERE id = $2
                    """, is_active, manager_id)

                # Обновляем группы
                if groups is not None:
                    # Удаляем старые связи
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema}.manager_group_membership
                        WHERE manager_id = $1
                    """, manager_id)

                    # Добавляем новые
                    for group_name in groups:
                        group_id = await conn.fetchval(f"""
                            SELECT id FROM {self.db_schema}.manager_groups 
                            WHERE name = $1
                        """, group_name)
                        if group_id:
                            await conn.execute(f"""
                                INSERT INTO {self.db_schema}.manager_group_membership (manager_id, group_id)
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
                    UPDATE {self.db_schema}.managers 
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
                    FROM {self.db_schema}.managers m
                    LEFT JOIN {self.db_schema}.manager_group_membership mgm ON m.id = mgm.manager_id
                    LEFT JOIN {self.db_schema}.manager_groups g ON mgm.group_id = g.id
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

    async def get_user_conversations(self) -> list:
        """Получить список всех активных чатов"""
        try:
            async with self.pool.acquire() as conn:
                # Сначала получаем последнее сообщение для каждого пользователя
                rows = await conn.fetch(f"""
                    SELECT 
                        user_id,
                        username,
                        last_message,
                        last_message_time,
                        unread_count
                    FROM (
                        SELECT 
                            user_id,
                            username,
                            FIRST_VALUE(message_text) OVER (
                                PARTITION BY user_id 
                                ORDER BY created_at DESC
                            ) as last_message,
                            FIRST_VALUE(created_at) OVER (
                                PARTITION BY user_id 
                                ORDER BY created_at DESC
                            ) as last_message_time,
                            COUNT(*) FILTER (WHERE direction = 'incoming' AND read_at IS NULL) 
                                OVER (PARTITION BY user_id) as unread_count,
                            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
                        FROM {self.db_schema}.user_messages
                    ) t
                    WHERE rn = 1
                    ORDER BY last_message_time DESC NULLS LAST
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []

    async def get_user_messages(self, user_id: int, limit: int = 50) -> list:
        """Получить историю сообщений пользователя"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT id, user_id, username, manager_id, direction, 
                           message_text, file_type, file_id, created_at, read_at
                    FROM {self.db_schema}.user_messages
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, user_id, limit)
                return [dict(row) for row in rows]
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


# Глобальный экземпляр
db = Database()