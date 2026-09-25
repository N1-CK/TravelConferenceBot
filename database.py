import hashlib
import hmac
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

import asyncpg
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    """Создать стойкий хеш пароля для новых и обновлённых учётных записей."""
    return generate_password_hash(password)


def _is_legacy_password_hash(password_hash: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", password_hash or ""))


def _verify_password(password_hash: str, password: str) -> bool:
    """Поддержать старые SHA-256 хеши до их автоматического обновления."""
    if _is_legacy_password_hash(password_hash):
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(password_hash, legacy_hash)

    try:
        return check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        return False


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

    def parse_passport_data(self, row_dict: dict) -> dict:
        raw = row_dict.get('passport_data') or ''

        # Регулярные выражения для построчного парсинга всех полей
        fields_map = {
            'first_name': r'First Name:\s*([^\n\r]+)',
            'last_name': r'Last Name:\s*([^\n\r]+)',
            'phone': r'Phone:\s*([^\n\r]+)',
            'passport_number': r'Passport Number:\s*([^\n\r]+)',
            'birth_date': r'Birth Date:\s*([^\n\r]+)',
            'passport_country': r'Passport Country:\s*([^\n\r]+)',
            'issue_date': r'Issue Date:\s*([^\n\r]+)',
            'expiry_date': r'Expiry Date:\s*([^\n\r]+)'
        }

        for key, pattern in fields_map.items():
            if not row_dict.get(key):
                m = re.search(pattern, raw, re.IGNORECASE)
                if m:
                    row_dict[key] = m.group(1).strip()

        # Алиасы для городов
        city_from = row_dict.get('city_from') or row_dict.get('departure_from') or '-'
        city_to = row_dict.get('city_to') or row_dict.get('return_to') or '-'

        row_dict['city_from'] = city_from
        row_dict['departure_from'] = city_from
        row_dict['city_to'] = city_to
        row_dict['return_to'] = city_to

        return row_dict

    async def create_pool(self):
        """Создание пула подключений"""
        try:
            self.pool = await asyncpg.create_pool(
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME'),
                min_size=5,
                max_size=25
            )

            if not await self.create_all_tables():
                raise RuntimeError("Database schema initialization failed")
            logger.info("Database pool created with all tables")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    async def create_all_tables(self):
        """Создаем все таблицы для обоих ботов"""
        try:
            async with self.pool.acquire() as conn:
                tables = [
                    f'CREATE SCHEMA IF NOT EXISTS systemcheck_bot;',
                    f'CREATE SCHEMA IF NOT EXISTS {self.db_schema};',
                    f'CREATE SCHEMA IF NOT EXISTS {self.db_schema_config};',
                    f'CREATE SCHEMA IF NOT EXISTS {self.db_schema_admin};',
                    f'CREATE SCHEMA IF NOT EXISTS {self.db_schema_travel};',
                    f'CREATE SCHEMA IF NOT EXISTS {self.db_schema_event};',
                    f'CREATE SCHEMA IF NOT EXISTS {self.db_schema_pr};',

                    # Белый список
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_config}.whitelist (
                        username TEXT PRIMARY KEY,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_config}.companies (
                        id SERIAL PRIMARY KEY,
                        company_name TEXT UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    """,

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
                        status TEXT DEFAULT 'pending',
                        visa_request_status TEXT DEFAULT 'pending',
                        flight_request_status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        is_archived BOOLEAN NOT NULL DEFAULT FALSE
                    )
                    ''',

                    # ===== ТАБЛИЦЫ AFFILIATE BOT =====
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
                        photo_path TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
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
                        is_archived BOOLEAN NOT NULL DEFAULT FALSE,
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
                        bot_link TEXT,
                        additional_info TEXT,
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
                    ''',

                    # Папки менеджеров
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_folders (
                        id SERIAL PRIMARY KEY,
                        manager_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_folder_items (
                        folder_id INTEGER NOT NULL REFERENCES {self.db_schema_admin}.manager_folders(id) ON DELETE CASCADE,
                        user_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (folder_id, user_id)
                    )
                    ''',

                    # Персональные отметки непрочитанного менеджерами
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_unread_chats (
                        manager_id INTEGER NOT NULL,
                        user_id BIGINT NOT NULL,
                        marked_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (manager_id, user_id)
                    );
                    ''',

                    # Персональный архив чатов менеджера
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_archived_chats (
                        manager_id INTEGER NOT NULL,
                        user_id BIGINT NOT NULL,
                        archived_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (manager_id, user_id)
                    );
                    ''',

                    f'''
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_muted_chats (
                        manager_id INTEGER NOT NULL,
                        user_id BIGINT NOT NULL,
                        muted_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (manager_id, user_id)
                    );
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
                        direction TEXT NOT NULL,
                        message_text TEXT,
                        file_type TEXT,
                        file_id TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        read_at TIMESTAMP,
                        replied_at TIMESTAMP
                    )
                """)

                async with conn.transaction():
                    await conn.execute("SELECT pg_advisory_xact_lock(hashtext('chat_department_migration'))")
                    # Старые сообщения не имеют достоверного отдела: оставляем их в
                    # отдельной истории для администратора, не приписывая менеджерам.
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema}.user_messages
                        ADD COLUMN IF NOT EXISTS department TEXT
                    """)
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.db_schema}.user_chat_departments (
                            user_id BIGINT PRIMARY KEY,
                            department TEXT NOT NULL CHECK (department IN ('pr', 'event', 'travel')),
                            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                        )
                    """)
                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_user_messages_department_user_time
                        ON {self.db_schema}.user_messages(department, user_id, created_at DESC)
                    """)

                    # Персональные настройки также относятся к диалогу, а не ко всем
                    # перепискам пользователя сразу. NULL legacy-строки не копируем.
                    for table, pk in (
                        ('manager_folder_items', 'folder_id'),
                        ('manager_unread_chats', 'manager_id'),
                        ('manager_archived_chats', 'manager_id'),
                        ('manager_muted_chats', 'manager_id'),
                    ):
                        await conn.execute(f"""
                            ALTER TABLE {self.db_schema_admin}.{table}
                            ADD COLUMN IF NOT EXISTS department TEXT NOT NULL DEFAULT 'legacy'
                        """)
                        await conn.execute(f"""
                            DO $$ BEGIN
                                IF (SELECT array_length(conkey, 1) FROM pg_constraint
                                    WHERE conrelid = '{self.db_schema_admin}.{table}'::regclass
                                      AND contype = 'p') = 2 THEN
                                    ALTER TABLE {self.db_schema_admin}.{table}
                                    DROP CONSTRAINT {table}_pkey;
                                    ALTER TABLE {self.db_schema_admin}.{table}
                                    ADD PRIMARY KEY ({pk}, user_id, department);
                                END IF;
                            END $$
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
                default_admin = os.getenv('ADMIN_USERNAME', 'admin')
                default_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
                password_hash = _hash_password(default_pass)

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

                await conn.execute(f"""
                    ALTER TABLE {self.db_schema_travel}.travel_flight_request
                    ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE
                """)
                await conn.execute(f"""
                    ALTER TABLE {self.db_schema_event}.event_ticket_requests
                    ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE
                """)

                logger.info("All tables created successfully")
                return True

        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False

    # ===== МЕТОДЫ ДЛЯ ПАПОК ЧАТОВ =====

    async def get_manager_folders(self, manager_id: int) -> list:
        """Получить папки менеджера с количеством диалогов"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        f.id,
                        f.name,
                        f.created_at,
                        COUNT(fi.user_id) as count
                    FROM {self.db_schema_admin}.manager_folders f
                    LEFT JOIN {self.db_schema_admin}.manager_folder_items fi ON f.id = fi.folder_id
                    WHERE f.manager_id = $1
                    GROUP BY f.id, f.name, f.created_at
                    ORDER BY f.created_at ASC
                """, manager_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting manager folders: {e}")
            return []

    async def create_manager_folder(self, manager_id: int, name: str) -> dict:
        """Создать папку менеджера"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    INSERT INTO {self.db_schema_admin}.manager_folders (manager_id, name)
                    VALUES ($1, $2)
                    RETURNING id, name, created_at
                """, manager_id, name)
                if row:
                    res = dict(row)
                    res['count'] = 0
                    return res
                return None
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return None

    async def delete_manager_folder(self, manager_id: int, folder_id: int) -> bool:
        """Удалить папку менеджера"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    DELETE FROM {self.db_schema_admin}.manager_folders
                    WHERE id = $1 AND manager_id = $2
                """, folder_id, manager_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting folder: {e}")
            return False

    async def toggle_user_in_folder(self, manager_id: int, folder_id: int, user_id: int, department: str) -> dict:
        """Добавить/удалить чат пользователя из папки менеджера"""
        try:
            async with self.pool.acquire() as conn:
                owner = await conn.fetchval(f"""
                    SELECT 1 FROM {self.db_schema_admin}.manager_folders
                    WHERE id = $1 AND manager_id = $2
                """, folder_id, manager_id)
                if not owner:
                    return {'error': 'Folder not found or access denied'}

                exists = await conn.fetchval(f"""
                    SELECT 1 FROM {self.db_schema_admin}.manager_folder_items
                    WHERE folder_id = $1 AND user_id = $2 AND department = $3
                """, folder_id, user_id, department)

                if exists:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema_admin}.manager_folder_items
                        WHERE folder_id = $1 AND user_id = $2 AND department = $3
                    """, folder_id, user_id, department)
                    in_folder = False
                else:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema_admin}.manager_folder_items (folder_id, user_id, department)
                        VALUES ($1, $2, $3)
                    """, folder_id, user_id, department)
                    in_folder = True

                folders = await conn.fetch(f"""
                    SELECT fi.folder_id
                    FROM {self.db_schema_admin}.manager_folder_items fi
                    JOIN {self.db_schema_admin}.manager_folders f ON fi.folder_id = f.id
                    WHERE f.manager_id = $1 AND fi.user_id = $2 AND fi.department = $3
                """, manager_id, user_id, department)

                return {
                    'in_folder': in_folder,
                    'user_id': user_id,
                    'folder_id': folder_id,
                    'user_folders': [r['folder_id'] for r in folders]
                }
        except Exception as e:
            logger.error(f"Error toggling folder item: {e}")
            return {'error': str(e)}

    async def toggle_chat_unread(self, manager_id: int, user_id: int, department: str) -> bool:
        """Переключить статус 'Пометить как непрочитанное' для менеджера"""
        try:
            async with self.pool.acquire() as conn:
                exists = await conn.fetchval(f"""
                    SELECT 1 FROM {self.db_schema_admin}.manager_unread_chats
                    WHERE manager_id = $1 AND user_id = $2 AND department = $3
                """, manager_id, user_id, department)
                if exists:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema_admin}.manager_unread_chats
                        WHERE manager_id = $1 AND user_id = $2 AND department = $3
                    """, manager_id, user_id, department)
                    return False  # Снята отметка
                else:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema_admin}.manager_unread_chats (manager_id, user_id, department)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING
                    """, manager_id, user_id, department)
                    return True  # Помечено как непрочитанное
        except Exception as e:
            logger.error(f"Error toggling chat unread: {e}")
            return False

    async def toggle_chat_archive(self, manager_id: int, user_id: int, department: str) -> bool:
        """Переключить архивный статус чата для менеджера"""
        try:
            async with self.pool.acquire() as conn:
                exists = await conn.fetchval(f"""
                    SELECT 1 FROM {self.db_schema_admin}.manager_archived_chats
                    WHERE manager_id = $1 AND user_id = $2 AND department = $3
                """, manager_id, user_id, department)
                if exists:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema_admin}.manager_archived_chats
                        WHERE manager_id = $1 AND user_id = $2 AND department = $3
                    """, manager_id, user_id, department)
                    return False  # Разархивирован
                else:
                    await conn.execute(f"""
                        INSERT INTO {self.db_schema_admin}.manager_archived_chats (manager_id, user_id, department)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING
                    """, manager_id, user_id, department)
                    return True  # Архивирован
        except Exception as e:
            logger.error(f"Error toggling chat archive: {e}")
            return False

    async def get_manager_user_folders_map(self, manager_id: int, department: str) -> dict:
        """Получить карту {user_id: [folder_id, ...]} для текущего менеджера"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT fi.user_id, fi.folder_id
                    FROM {self.db_schema_admin}.manager_folder_items fi
                    JOIN {self.db_schema_admin}.manager_folders f ON fi.folder_id = f.id
                    WHERE f.manager_id = $1 AND fi.department = $2
                """, manager_id, department)
                res = {}
                for r in rows:
                    uid = r['user_id']
                    res.setdefault(uid, []).append(r['folder_id'])
                return res
        except Exception as e:
            logger.error(f"Error getting user folders map: {e}")
            return {}

    # ===== AFFILIATE BOT МЕТОДЫ =====

    async def add_affiliate_user(self, username: str, company: str) -> bool:
        """Добавление пользователя Affiliate Bot"""
        if not username:
            return False
        clean_username = username.lstrip('@').strip()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_config}.whitelist (username, is_active)
                    VALUES ($1, TRUE)
                    ON CONFLICT (username) DO UPDATE
                    SET is_active = TRUE
                """, clean_username)
                return True
        except Exception as e:
            logger.error(f"Error adding affiliate user: {e}")
            return False

    async def get_cities_from_restaurants(self) -> list:
        """Получение списка городов из ресторанов"""
        try:
            async with self.pool.acquire() as conn:
                records = await conn.fetch(f"""
                    SELECT city
                    FROM (
                        SELECT DISTINCT max(id) as idd, city
                        FROM {self.db_schema_pr}.affil_restaurants
                        WHERE created_at = (SELECT max(created_at) FROM {self.db_schema_pr}.affil_restaurants)
                        GROUP BY city) t1
                """)
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

    async def toggle_ticket_request_archive(self, request_id: int):
        """Return the new archive state, or None if the ticket request is absent."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(f"""
                UPDATE {self.db_schema_event}.event_ticket_requests
                SET is_archived = NOT is_archived, updated_at = NOW()
                WHERE id = $1
                RETURNING is_archived
            """, request_id)

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
                    WHERE is_archived = FALSE
                """) or 0
                pending = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE status = 'pending' AND is_archived = FALSE
                """) or 0
                in_progress = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE status = 'in_progress' AND is_archived = FALSE
                """) or 0
                ready = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_event}.event_ticket_requests 
                    WHERE status = 'ready' AND is_archived = FALSE
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

    async def get_all_event_stands(self) -> list:
        """Получить список всех стендов для панели управления"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT id, company, conference, stand_style, stand_number, 
                           working_hours, dress_code, photo_path, created_at, updated_at
                    FROM {self.db_schema_event}.event_stands
                    ORDER BY conference, company
                """)
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting event stands: {e}")
            return []

    async def upsert_event_stand(self, data: dict) -> bool:
        """Создать или обновить стенд компании на конференции"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.db_schema_event}.event_stands 
                    (company, conference, stand_style, stand_number, working_hours, dress_code, photo_path, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (company, conference) DO UPDATE SET
                        stand_style = EXCLUDED.stand_style,
                        stand_number = EXCLUDED.stand_number,
                        working_hours = EXCLUDED.working_hours,
                        dress_code = EXCLUDED.dress_code,
                        photo_path = COALESCE(EXCLUDED.photo_path, {self.db_schema_event}.event_stands.photo_path),
                        updated_at = NOW()
                """,
                                   data['company'],
                                   data['conference'],
                                   data.get('stand_style'),
                                   data.get('stand_number'),
                                   data.get('working_hours'),
                                   data.get('dress_code'),
                                   data.get('photo_path')
                                   )
                return True
        except Exception as e:
            logger.error(f"Error upserting event stand: {e}")
            return False

    async def delete_event_stand(self, stand_id: int) -> str:
        """Удалить стенд и вернуть photo_path для удаления файла с диска"""
        try:
            async with self.pool.acquire() as conn:
                photo_path = await conn.fetchval(f"""
                    DELETE FROM {self.db_schema_event}.event_stands
                    WHERE id = $1
                    RETURNING photo_path
                """, stand_id)
                return photo_path
        except Exception as e:
            logger.error(f"Error deleting event stand: {e}")
            return None

    async def get_event_stand(self, company: str, conference: str) -> dict:
        """Получить информацию о стенде компании на конференции (включая фото)"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT id, stand_style, stand_number, working_hours, dress_code, photo_path 
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
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS visa_request_status TEXT DEFAULT 'pending'
                    """)
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_travel}.travel_flight_request 
                        ADD COLUMN IF NOT EXISTS flight_request_status TEXT DEFAULT 'pending'
                    """)
                except Exception:
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

    async def get_all_travel_flight_requests(self) -> list:
        """Получить все заявки на билеты вместе с данными суточных"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT 
                        tfr.*,
                        pdr.id as per_diem_id,
                        pdr.payment_type,
                        pdr.payment_details,
                        COALESCE(pdr.status, 'pending') as per_diem_status
                    FROM {self.db_schema_travel}.travel_flight_request tfr
                    LEFT JOIN LATERAL (
                        SELECT id, payment_type, payment_details, status
                        FROM {self.db_schema_travel}.travel_per_diem_requests
                        WHERE user_id = tfr.user_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) pdr ON true
                    ORDER BY tfr.created_at DESC
                """)
                return [self.parse_passport_data(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting travel flight requests: {e}")
            return []

    async def toggle_travel_request_archive(self, request_id: int):
        """Return the new archive state, or None when the request does not exist."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(f"""
                UPDATE {self.db_schema_travel}.travel_flight_request
                SET is_archived = NOT is_archived, updated_at = NOW()
                WHERE id = $1
                RETURNING is_archived
            """, request_id)

    async def get_travel_flight_request_by_id(self, request_id: int) -> dict:
        """Получить заявку на билет по ID вместе с данными суточных"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT 
                        tfr.*,
                        pdr.id as per_diem_id,
                        pdr.payment_type,
                        pdr.payment_details,
                        COALESCE(pdr.status, 'pending') as per_diem_status
                    FROM {self.db_schema_travel}.travel_flight_request tfr
                    LEFT JOIN LATERAL (
                        SELECT id, payment_type, payment_details, status
                        FROM {self.db_schema_travel}.travel_per_diem_requests
                        WHERE user_id = tfr.user_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) pdr ON true
                    WHERE tfr.id = $1
                """, request_id)
                return self.parse_passport_data(dict(row)) if row else {}
        except Exception as e:
            logger.error(f"Error getting travel flight request {request_id}: {e}")
            return {}

    async def get_visa_request(self, request_id: int) -> dict:
        """Получить визовую заявку по ID (алиас для совместимости API)"""
        return await self.get_travel_flight_request_by_id(request_id)

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
                    WHERE is_archived = FALSE
                """) or 0

                visa_pending = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE visa_request_status = 'pending' AND is_archived = FALSE
                """) or 0

                flight_pending = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE flight_request_status = 'pending' AND is_archived = FALSE
                """) or 0

                flight_purchased = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.db_schema_travel}.travel_flight_request 
                    WHERE flight_request_status = 'purchased' AND is_archived = FALSE
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
                usernames = list(set([f['username'] for f in flights_data]))
                for username in usernames:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema}.user_flights 
                        WHERE username = $1
                    """, username)

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
        """Проверка пользователя в whitelist (без учета наличия @ и регистра)"""
        if not username:
            return False
        clean_username = username.lstrip('@').strip()
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    f"""
                    SELECT is_active 
                    FROM {self.db_schema_config}.whitelist 
                    WHERE LOWER(username) = LOWER($1)
                    """,
                    clean_username
                )
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking whitelist for {clean_username}: {e}")
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

    async def log_user_action(self, user_id: int, username: str, action: str, details: dict = None) -> bool:
        """Логирование действий пользователя"""
        try:
            import json
            async with self.pool.acquire() as conn:
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
                await conn.execute(f"""
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
                    ORDER BY departure_date, departure_time
                """
                result = await conn.fetch(query, f"%{username}%", f"%{conference}%")
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting flight details from travel_bot: {e}")
            return []

    async def get_hotel_info_travel(self, conference: str) -> Dict:
        """Получить информацию об отеле"""
        try:
            async with self.pool.acquire() as conn:
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
                    LIMIT 1
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
        """Обновить статус бронирования"""
        try:
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_pr}.affil_bookings 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'confirmed'
                    """)
                except Exception:
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
        """Обновить статус отчета"""
        try:
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute(f"""
                        ALTER TABLE {self.db_schema_pr}.affil_reports 
                        ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'
                    """)
                except Exception:
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
        """Получение данных пользователя"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT user_id, username, language, full_name, position, company, 
                           registered_at, updated_at
                    FROM {self.db_schema_config}.user_profiles 
                    WHERE user_id = $1
                """, user_id)

                if row:
                    return dict(row)
                return {}
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return {}

    async def get_all_questions_by_table(self, table: str) -> list:
        """Получить все вопросы из таблицы"""
        try:
            async with self.pool.acquire() as conn:
                query = f'SELECT * FROM {table} ORDER BY created_at DESC'
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting questions from {table}: {e}")
            return []

    async def sync_whitelist_from_google_sheets(self, spreadsheet_name: str = "Whitelist",
                                                clear_existing: bool = True) -> bool:
        """Синхронизация whitelist и конференций из Google Sheets"""
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

                    for record in records:
                        raw_username = record.get('TG_username', '').strip()
                        if not raw_username or raw_username.lower() == 'tg_username':
                            continue

                        username = raw_username.lstrip('@').strip()
                        if not username:
                            continue

                        await conn.execute(f"""
                            INSERT INTO {self.db_schema_config}.whitelist (username, is_active)
                            VALUES ($1, TRUE)
                            ON CONFLICT (username) DO UPDATE
                            SET is_active = TRUE
                        """, username)

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

                logger.info(f"✅ Synced {total_users} users, {total_conferences} conferences, {total_companies} companies")
                return True

        except Exception as e:
            logger.error(f"Error syncing whitelist from Google Sheets: {e}")
            return False

    async def get_user_conferences(self, username: str) -> List[Dict]:
        """Получить все конференции пользователя"""
        if not username:
            return []
        clean_username = username.lstrip('@').strip()
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT conference_name, trip_start_date, trip_end_date,
                           conference_start_date, conference_end_date, city
                    FROM {self.db_schema}.user_conferences
                    WHERE LOWER(username) = LOWER($1)
                    ORDER BY conference_start_date
                """, clean_username)
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Error getting user conferences: {e}")
            return []

    async def get_user_active_conferences(self, username: str) -> List[Dict]:
        """Получить список активных конференций пользователя"""
        if not username:
            return []
        clean_username = username.lstrip('@').strip()
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
                    WHERE LOWER(username) = LOWER($1)
                    ORDER BY conference_start_date
                """, clean_username)

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
        """Проверить, имеет ли пользователь доступ к конкретной конференции"""
        if not username:
            return False
        clean_username = username.lstrip('@').strip()
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(f"""
                    SELECT 1 FROM {self.db_schema}.user_conferences
                    WHERE LOWER(username) = LOWER($1) AND conference_name = $2
                """, clean_username, conference)
                return bool(result)
        except Exception as e:
            logger.error(f"Error checking conference access: {e}")
            return await self.check_whitelist(clean_username)

    async def get_travel_request_status(self, username: str, request_type: str) -> dict:
        """Получить статус travel-заявки пользователя"""
        try:
            async with self.pool.acquire() as conn:
                table = f"{self.db_schema_travel}.travel_flight_request"
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
            password_hash = _hash_password(password)

            async with self.pool.acquire() as conn:
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
            async with self.pool.acquire() as conn:
                admin = await conn.fetchrow(f"""
                    SELECT id, username, full_name, role, 
                           can_manage_users, can_broadcast, can_view_stats, can_manage_conferences,
                           is_active, password_hash
                    FROM {self.db_schema_admin}.admin_users 
                    WHERE username = $1 AND is_active = TRUE
                """, username)

                if admin and _verify_password(admin['password_hash'], password):
                    if _is_legacy_password_hash(admin['password_hash']):
                        await conn.execute(f"""
                            UPDATE {self.db_schema_admin}.admin_users
                            SET password_hash = $1
                            WHERE id = $2
                        """, _hash_password(password), admin['id'])

                    await conn.execute(f"""
                        UPDATE {self.db_schema_admin}.admin_users 
                        SET last_login = NOW() 
                        WHERE id = $1
                    """, admin['id'])

                    result = dict(admin)
                    result.pop('password_hash', None)
                    return result
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
                allowed_columns = {
                    'username', 'full_name', 'role', 'can_manage_users',
                    'can_broadcast', 'can_view_stats',
                    'can_manage_conferences', 'is_active',
                }

                for key, value in data.items():
                    if key in allowed_columns:
                        set_clauses.append(f"{key} = ${i}")
                        values.append(value)
                        i += 1

                if 'password' in data and data['password']:
                    set_clauses.append(f"password_hash = ${i}")
                    values.append(_hash_password(data['password']))
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

                if admin['role'] == 'admin':
                    return True

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
                rows = await conn.fetch(f"""
                    SELECT * FROM {self.db_schema}.user_flights 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting flight requests: {e}")
            return []

    async def update_visa_status(self, request_id: int, status: str) -> bool:
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

    async def get_stored_passport_data(self, user_id: int) -> dict:
        """Получить сохраненные паспортные данные пользователя"""
        try:
            async with self.pool.acquire() as conn:
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
                        id,
                        username,
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

    async def get_broadcast_details_by_id(self, log_id: int) -> dict:
        """Получить полные детали рассылки по ID лога"""
        try:
            import json
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT 
                        id,
                        username,
                        details,
                        timestamp
                    FROM {self.db_schema}.user_logs
                    WHERE id = $1 AND action = 'broadcast_sent'
                """, log_id)

                if not row:
                    return None

                data = dict(row)
                details = data.get('details')
                if isinstance(details, str):
                    details = json.loads(details)
                elif not details:
                    details = {}

                return {
                    'id': data['id'],
                    'sender': data['username'],
                    'timestamp': data['timestamp'].strftime('%d.%m.%Y %H:%M:%S') if data.get('timestamp') else '',
                    'broadcast_type': details.get('type', 'all'),
                    'company': details.get('company', ''),
                    'success_count': details.get('success', 0),
                    'failed_count': details.get('failed', 0),
                    'file_count': details.get('file_count', 0),
                    'success_users': details.get('success_users', []),
                    'failed_users': details.get('failed_users', [])
                }
        except Exception as e:
            logger.error(f"Error getting broadcast details: {e}")
            return None

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
                            success: int, failed: int, message_length: int, file_count: int = 0,
                            success_users: list = None, failed_users: list = None) -> bool:
        """Логировать рассылку с деталями по пользователям"""
        try:
            import json
            async with self.pool.acquire() as conn:
                details = {
                    'type': broadcast_type,
                    'company': company,
                    'success': success,
                    'failed': failed,
                    'message_length': message_length,
                    'file_count': file_count,
                    'success_users': success_users or [],
                    'failed_users': failed_users or []
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
            return []

    async def get_all_users_with_details(self) -> list:
        """Получить всех пользователей с деталями без N+1 запросов"""
        try:
            async with self.pool.acquire() as conn:
                # Получаем пользователей и статус онлайн/активности
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
                if not users:
                    return []

                # 1 запрос: сразу собираем все конференции пользователей
                conf_rows = await conn.fetch(f"""
                    SELECT username, array_agg(conference_name) as confs
                    FROM {self.db_schema}.user_conferences
                    GROUP BY username
                """)
                conf_map = {r['username']: r['confs'] for r in conf_rows}

                # 1 запрос: агрегированный подсчет заявок пользователей
                req_rows = await conn.fetch(f"""
                    SELECT username, COUNT(*) as cnt FROM (
                        SELECT username FROM {self.db_schema_pr}.pr_banner_requests
                        UNION ALL
                        SELECT username FROM {self.db_schema_pr}.pr_business_cards
                        UNION ALL
                        SELECT username FROM {self.db_schema_travel}.travel_flight_request
                    ) all_reqs
                    GROUP BY username
                """)
                req_map = {r['username']: r['cnt'] for r in req_rows}

                for user in users:
                    uname = user.get('username')
                    user['conferences'] = conf_map.get(uname, [])
                    user['requests_count'] = req_map.get(uname, 0)

                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def get_user_messages_by_department(self, manager_groups: list, limit: int = 100) -> list:
        """Получить сообщения пользователей, доступные для групп менеджера"""
        try:
            async with self.pool.acquire() as conn:
                department_map = {
                    'travel': 'travel_questions',
                    'pr': 'pr_questions',
                    'event': 'event_questions'
                }

                visible_tables = []
                for group in manager_groups:
                    if group in department_map:
                        visible_tables.append(department_map[group])

                if not visible_tables:
                    return []

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

                messages = await conn.fetch(f"""
                    SELECT 
                        m.id,
                        m.user_id,
                        m.username,
                        m.message_text,
                        m.direction,
                        m.created_at,
                        'message' as type,
                        m.department as department,
                        EXISTS(
                            SELECT 1 FROM {self.db_schema}.user_messages m2 
                            WHERE m2.user_id = m.user_id AND m2.department = m.department
                            AND m2.direction = 'incoming' 
                            AND m2.read_at IS NULL
                        ) as has_unread
                    FROM {self.db_schema}.user_messages m
                    WHERE m.direction = 'incoming' AND m.department = ANY($2::text[])
                    ORDER BY m.created_at DESC
                    LIMIT $1
                """, limit, manager_groups)

                all_questions.extend([dict(row) for row in messages])
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
                tables = {
                    'pr': f'{self.db_schema_pr}.pr_questions',
                    'event': f'{self.db_schema_event}.event_questions',
                    'travel': f'{self.db_schema_travel}.travel_questions'
                }

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
        """Получить детальную информацию о пользователе, включая Travel данные"""
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
                    except Exception:
                        pass

                travel_row = await conn.fetchrow(f"""
                    SELECT 
                        tfr.*,
                        pdr.payment_type,
                        pdr.payment_details,
                        COALESCE(pdr.status, 'pending') as per_diem_status
                    FROM {self.db_schema_travel}.travel_flight_request tfr
                    LEFT JOIN LATERAL (
                        SELECT payment_type, payment_details, status
                        FROM {self.db_schema_travel}.travel_per_diem_requests
                        WHERE user_id = tfr.user_id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) pdr ON true
                    WHERE tfr.user_id = $1
                    ORDER BY tfr.created_at DESC
                    LIMIT 1
                """, user_id)

                if travel_row:
                    parsed_travel = self.parse_passport_data(dict(travel_row))
                    result['travel'] = parsed_travel
                else:
                    passport_data = await self.get_stored_passport_data(user_id)
                    per_diem = await conn.fetchrow(f"""
                        SELECT payment_type, payment_details, status
                        FROM {self.db_schema_travel}.travel_per_diem_requests
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, user_id)

                    result['travel'] = {
                        'first_name': passport_data.get('first_name'),
                        'last_name': passport_data.get('last_name'),
                        'phone': passport_data.get('phone'),
                        'passport_number': passport_data.get('passport_number'),
                        'birth_date': passport_data.get('birth_date'),
                        'passport_country': passport_data.get('passport_country'),
                        'issue_date': passport_data.get('issue_date'),
                        'expiry_date': passport_data.get('expiry_date'),
                        'payment_type': per_diem.get('payment_type') if per_diem else None,
                        'payment_details': per_diem.get('payment_details') if per_diem else None,
                        'per_diem_status': per_diem.get('status') if per_diem else None
                    }

                return result
        except Exception as e:
            logger.error(f"Error getting user details: {e}")
            return None

    async def create_managers_tables(self):
        """Создание таблиц для менеджеров и групп"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.managers (
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

                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_groups (
                        id          SERIAL PRIMARY KEY,
                        name        TEXT UNIQUE NOT NULL,
                        description TEXT,
                        created_at  TIMESTAMP DEFAULT NOW()
                    )
                """)

                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.db_schema_admin}.manager_group_membership (
                        manager_id  INTEGER REFERENCES {self.db_schema_admin}.managers (id) ON DELETE CASCADE,
                        group_id    INTEGER REFERENCES {self.db_schema_admin}.manager_groups (id) ON DELETE CASCADE,
                        assigned_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (manager_id, group_id)
                    )
                """)

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

                admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
                admin_hash = _hash_password(admin_pass)

                admin_id = await conn.fetchval(f"""
                    INSERT INTO {self.db_schema_admin}.managers (username, password_hash, full_name, role)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id
                """, 'admin', admin_hash, 'Главный администратор', 'admin')

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

                logger.info("Managers tables created")
                return True

        except Exception as e:
            logger.error(f"Error creating managers tables: {e}")
            return False

    async def verify_manager(self, username: str, password: str) -> dict:
        """Проверка учетных данных менеджера"""
        try:
            async with self.pool.acquire() as conn:
                manager = await conn.fetchrow(f"""
                    SELECT id, username, full_name, role, is_active, password_hash
                    FROM {self.db_schema_admin}.managers
                    WHERE username = $1
                      AND is_active = TRUE
                """, username)

                if manager and _verify_password(manager['password_hash'], password):
                    if _is_legacy_password_hash(manager['password_hash']):
                        await conn.execute(f"""
                            UPDATE {self.db_schema_admin}.managers
                            SET password_hash = $1
                            WHERE id = $2
                        """, _hash_password(password), manager['id'])

                    groups = await conn.fetch(f"""
                        SELECT g.name, g.description
                        FROM {self.db_schema_admin}.manager_groups g
                        JOIN {self.db_schema_admin}.manager_group_membership mgm ON g.id = mgm.group_id
                        WHERE mgm.manager_id = $1
                    """, manager['id'])

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
            logger.error(f"Error verifying manager: {e}")
            return {}

    async def add_manager(self, username: str, password: str, full_name: str = None, groups: list = None) -> bool:
        """Добавить нового менеджера"""
        try:
            password_hash = _hash_password(password)

            async with self.pool.acquire() as conn:
                manager_id = await conn.fetchval(f"""
                    INSERT INTO {self.db_schema_admin}.managers (username, password_hash, full_name, role)
                    VALUES ($1, $2, $3, 'manager')
                    RETURNING id
                """, username, password_hash, full_name)

                if manager_id and groups:
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
            logger.error(f"Error adding manager: {e}")
            return False

    async def delete_manager(self, manager_id: int) -> bool:
        """Удалить менеджера"""
        try:
            async with self.pool.acquire() as conn:
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
            logger.error(f"Error deleting manager: {e}")
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
            logger.error(f"Error getting manager groups: {e}")
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

                if groups is not None:
                    await conn.execute(f"""
                        DELETE FROM {self.db_schema_admin}.manager_group_membership
                        WHERE manager_id = $1
                    """, manager_id)

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
            password_hash = _hash_password(new_password)

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

    async def set_chat_department(self, user_id: int, department: str) -> None:
        if department not in ('pr', 'event', 'travel'):
            raise ValueError('Invalid department')
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self.db_schema}.user_chat_departments (user_id, department)
                VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE
                SET department = EXCLUDED.department, updated_at = NOW()
            """, user_id, department)

    async def get_chat_department(self, user_id: int) -> Optional[str]:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(f"""
                SELECT department FROM {self.db_schema}.user_chat_departments WHERE user_id = $1
            """, user_id)

    async def has_chat(self, user_id: int, department: str) -> bool:
        """Require an existing department conversation before a manager opens it."""
        async with self.pool.acquire() as conn:
            return bool(await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT 1 FROM {self.db_schema}.user_messages
                    WHERE user_id = $1 AND COALESCE(department, 'legacy') = $2
                    UNION ALL
                    SELECT 1 FROM {self.db_schema_pr}.pr_questions WHERE user_id = $1 AND $2 = 'pr'
                    UNION ALL
                    SELECT 1 FROM {self.db_schema_event}.event_questions WHERE user_id = $1 AND $2 = 'event'
                    UNION ALL
                    SELECT 1 FROM {self.db_schema_travel}.travel_questions WHERE user_id = $1 AND $2 = 'travel'
                )
            """, user_id, department))

    async def file_in_departments(self, file_id: str, departments: list[str]) -> bool:
        async with self.pool.acquire() as conn:
            return bool(await conn.fetchval(f"""
                SELECT EXISTS (SELECT 1 FROM {self.db_schema}.user_messages
                               WHERE file_id = $1 AND COALESCE(department, 'legacy') = ANY($2::text[]))
            """, file_id, departments))

    async def save_user_message(self, user_id: int, username: str,
                                message_text: str = None, file_type: str = None,
                                file_id: str = None, direction: str = 'incoming',
                                department: Optional[str] = None, manager_id: Optional[int] = None) -> int:
        if department not in (None, 'pr', 'event', 'travel'):
            raise ValueError('Invalid department')
        async with self.pool.acquire() as conn:
            return await conn.fetchval(f"""
                INSERT INTO {self.db_schema}.user_messages
                (user_id, username, direction, message_text, file_type, file_id,
                 department, manager_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW()) RETURNING id
            """, user_id, username or str(user_id), direction, message_text,
                 file_type, file_id, department, manager_id)

    async def save_user_messages_bulk(self, messages_data: list, department: Optional[str] = None) -> bool:
        if not messages_data:
            return True
        if department not in (None, 'pr', 'event', 'travel'):
            raise ValueError('Invalid department')
        async with self.pool.acquire() as conn:
            await conn.executemany(f"""
                INSERT INTO {self.db_schema}.user_messages
                (user_id, username, direction, message_text, file_type, file_id,
                 department, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """, [tuple(row) + (department,) for row in messages_data])
        return True

    async def toggle_chat_mute(self, manager_id: int, user_id: int, department: str) -> bool:
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(f"""
                SELECT 1 FROM {self.db_schema_admin}.manager_muted_chats
                WHERE manager_id = $1 AND user_id = $2 AND department = $3
            """, manager_id, user_id, department)
            if exists:
                await conn.execute(f"""
                    DELETE FROM {self.db_schema_admin}.manager_muted_chats
                    WHERE manager_id = $1 AND user_id = $2 AND department = $3
                """, manager_id, user_id, department)
                return False
            await conn.execute(f"""
                INSERT INTO {self.db_schema_admin}.manager_muted_chats
                (manager_id, user_id, department) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """, manager_id, user_id, department)
            return True

    async def get_user_conversations(self, manager_id: int = None,
                                     departments: list[str] = None) -> list:
        """One independent chat for each user and department; legacy is admin only."""
        departments = departments or []
        if not departments:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                WITH activity AS (
                    SELECT user_id, username, department, message_text AS body, created_at
                    FROM {self.db_schema}.user_messages
                    WHERE COALESCE(department, 'legacy') = ANY($1::text[])
                    UNION ALL
                    SELECT user_id, username, 'pr', question, created_at
                    FROM {self.db_schema_pr}.pr_questions WHERE 'pr' = ANY($1::text[])
                    UNION ALL
                    SELECT user_id, username, 'event', question, created_at
                    FROM {self.db_schema_event}.event_questions WHERE 'event' = ANY($1::text[])
                    UNION ALL
                    SELECT user_id, username, 'travel', question, created_at
                    FROM {self.db_schema_travel}.travel_questions WHERE 'travel' = ANY($1::text[])
                ), latest AS (
                    SELECT DISTINCT ON (user_id, COALESCE(department, 'legacy'))
                        user_id, username, COALESCE(department, 'legacy') AS department,
                        body, created_at
                    FROM activity
                    ORDER BY user_id, COALESCE(department, 'legacy'), created_at DESC
                )
                SELECT l.user_id, l.department,
                       COALESCE(p.username, l.username) AS username,
                       p.full_name, l.body AS last_message, l.created_at AS last_message_time,
                       (SELECT COUNT(*) FROM {self.db_schema}.user_messages m
                        WHERE m.user_id = l.user_id AND COALESCE(m.department, 'legacy') = l.department
                          AND m.direction = 'incoming' AND m.read_at IS NULL) AS unread_count,
                       EXISTS (SELECT 1 FROM {self.db_schema_admin}.manager_archived_chats a
                               WHERE a.manager_id = $2 AND a.user_id = l.user_id
                                 AND a.department = l.department) AS is_archived,
                       EXISTS (SELECT 1 FROM {self.db_schema_admin}.manager_unread_chats u
                               WHERE u.manager_id = $2 AND u.user_id = l.user_id
                                 AND u.department = l.department) AS is_manual_unread,
                       EXISTS (SELECT 1 FROM {self.db_schema_admin}.manager_muted_chats mu
                               WHERE mu.manager_id = $2 AND mu.user_id = l.user_id
                                 AND mu.department = l.department) AS is_muted,
                       ARRAY(SELECT fi.folder_id FROM {self.db_schema_admin}.manager_folder_items fi
                             JOIN {self.db_schema_admin}.manager_folders f ON f.id = fi.folder_id
                             WHERE f.manager_id = $2 AND fi.user_id = l.user_id
                               AND fi.department = l.department) AS folder_ids
                FROM latest l
                LEFT JOIN {self.db_schema_config}.user_profiles p ON p.user_id = l.user_id
                ORDER BY l.created_at DESC
            """, departments, manager_id or 0)
            result = [dict(row) for row in rows]
            for row in result:
                if row['is_manual_unread'] and row['unread_count'] == 0:
                    row['unread_count'] = 1
                row['last_message'] = (row['last_message'] or '')[:100]
            return result

    async def get_user_messages(self, user_id: int, department: str, limit: int = 100) -> list:
        if department not in ('pr', 'event', 'travel', 'legacy'):
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT * FROM (
                    SELECT id, user_id, username, manager_id, direction,
                           message_text, file_type, file_id, created_at, read_at,
                           'message' AS source_type, NULL::text AS category
                    FROM {self.db_schema}.user_messages
                    WHERE user_id = $1 AND COALESCE(department, 'legacy') = $2
                    UNION ALL
                    SELECT id, user_id, username, NULL::integer, 'incoming', question,
                           NULL::text, NULL::text, created_at, NULL::timestamp,
                           'pr_question', category
                    FROM {self.db_schema_pr}.pr_questions WHERE user_id = $1 AND $2 = 'pr'
                    UNION ALL
                    SELECT id, user_id, username, NULL::integer, 'incoming', question,
                           NULL::text, NULL::text, created_at, NULL::timestamp,
                           'event_question', category
                    FROM {self.db_schema_event}.event_questions WHERE user_id = $1 AND $2 = 'event'
                    UNION ALL
                    SELECT id, user_id, username, NULL::integer, 'incoming', question,
                           NULL::text, NULL::text, created_at, NULL::timestamp,
                           'travel_question', category
                    FROM {self.db_schema_travel}.travel_questions WHERE user_id = $1 AND $2 = 'travel'
                ) history ORDER BY created_at DESC LIMIT $3
            """, user_id, department, limit)
            return [dict(row) for row in rows]

    async def mark_messages_read(self, user_id: int, manager_id: int, department: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {self.db_schema}.user_messages SET read_at = NOW(), manager_id = $1
                WHERE user_id = $2 AND COALESCE(department, 'legacy') = $3
                  AND direction = 'incoming' AND read_at IS NULL
            """, manager_id, user_id, department)
            await conn.execute(f"""
                DELETE FROM {self.db_schema_admin}.manager_unread_chats
                WHERE manager_id = $1 AND user_id = $2 AND department = $3
            """, manager_id, user_id, department)
            return True

    async def close(self):
        """Закрыть пул соединений"""
        if self.pool:
            pool = self.pool
            self.pool = None
            await pool.close()
            logger.info("Database pool closed")


# Глобальный экземпляр
db = Database()
