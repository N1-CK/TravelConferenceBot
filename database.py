from typing import List, Dict

import asyncpg
import logging
import os
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
    async def log_user_action(self, user_id: int, username: str, action: str, details: str = None) -> bool:
        """Логирование действий пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema}.user_logs (user_id, username, action, details)
                    VALUES ($1, $2, $3, $4)
                """, user_id, username, action, details)  # details уже должна быть строкой
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


# Глобальный экземпляр
db = Database()