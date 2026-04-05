import os
import logging
import asyncio
from datetime import datetime
import asyncpg
import pygsheets
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from database import db

load_dotenv()
logger = logging.getLogger(__name__)


class GoogleSheetsSync:
    def __init__(self):
        self.pg_pool = None
        self.gc = None

    async def connect_to_postgres(self, db_config):
        """Connect to PostgreSQL"""
        try:
            self.pg_pool = await asyncpg.create_pool(**db_config)
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False

    async def connect_to_google_sheets(self):
        """Authenticate to Google Sheets"""
        try:
            service_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', './configs/conferencebothelper-1134fe7c70c9.json')
            if os.path.exists(service_file):
                self.gc = pygsheets.authorize(service_account_file=service_file)
                return True
            else:
                logger.error(f"Google service account file not found: {service_file}")
                return False
        except Exception as e:
            logger.error(f"Google Sheets authentication failed: {e}")
            return False

    async def sync_restaurants_from_google_sheets(self, spreadsheet_name: str, worksheet_name: str):
        """Sync restaurants from Google Sheets to DB"""
        try:
            if not await self.connect_to_google_sheets():
                return False

            # Get data from Google Sheets
            sh = self.gc.open(spreadsheet_name)
            worksheet = sh.worksheet_by_title(worksheet_name)
            records = worksheet.get_all_records()
            df = pd.DataFrame(records)

            if df.empty:
                logger.warning("No data in Google Sheets")
                return False

            # Connect to PostgreSQL
            db_config = {
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT'),
                'database': os.getenv('DB_NAME')
            }

            if not await self.connect_to_postgres(db_config):
                return False

            # Save to DB
            async with self.pg_pool.acquire() as conn:
                # Create temp table
                await conn.execute(f"""
                    CREATE TEMP TABLE temp_restaurants (
                        city TEXT,
                        restaurant TEXT,
                        address TEXT,
                        cost TEXT,
                        link TEXT,
                        comment TEXT
                    )
                """)

                # Insert into temp table
                # for _, row in df.iterrows():
                #     await conn.execute("""
                #         INSERT INTO temp_restaurants
                #         (city, restaurant, address, cost, link, comment)
                #         VALUES ($1, $2, $3, $4, $5, $6)
                #     """,
                #         row.get('City', ''),
                #         row.get('Restaurant', ''),
                #         row.get('Address', ''),
                #         row.get('Cost', ''),
                #         row.get('Link', ''),
                #         row.get('Comment', ''))

                # Move to main table
                await conn.execute(f"""
                    INSERT INTO {db.db_schema}.restaurants 
                    (city, restaurant, address, cost, link, comment, created_at)
                    SELECT city, restaurant, address, cost, link, comment, NOW()
                    FROM temp_restaurants
                """)

                logger.info(f"Synced {len(df)} restaurants from Google Sheets")
                return True

        except Exception as e:
            logger.error(f"Error syncing restaurants: {e}")
            return False
        finally:
            if self.pg_pool:
                await self.pg_pool.close()

    async def sync_bookings_to_sheets(self):
        """Sync bookings to Google Sheets"""
        try:
            if not await self.connect_to_google_sheets():
                return False

            SPREADSHEET_NAME = os.getenv('GT_FILE_NAME', 'Restaurants')
            WORKSHEET_NAME = os.getenv('GT_BOOKINGS_FILE', 'Bookings')

            # Get data from DB
            async with db.pool.acquire() as conn:
                bookings = await conn.fetch(f"""
                    SELECT b.*, w.company as user_company
                    FROM {db.db_schema}.bookings b
                    LEFT JOIN {db.db_schema_config}.whitelist w ON b.username = w.username
                    ORDER BY b.created_at
                """)

            if not bookings:
                logger.info("No bookings to sync")
                return True

            # Prepare data for Google Sheets
            data = []
            for booking in bookings:
                data.append([
                    booking['datetime'],
                    booking['manager'],
                    booking.get('user_company', ''),
                    booking['company'],
                    booking['partner'],
                    booking['restaurant'],
                    booking['payment_method'],
                    f"@{booking['username']}",
                    booking['created_at'].strftime('%d.%m.%Y %H:%M') if booking['created_at'] else ''
                ])

            # Send to Google Sheets
            sh = self.gc.open(SPREADSHEET_NAME)
            try:
                worksheet = sh.worksheet_by_title(WORKSHEET_NAME)
            except:
                worksheet = sh.add_worksheet(WORKSHEET_NAME, rows=1000, cols=9)
                worksheet.update_values('A1', [['Date', 'Manager', 'ManagerCompany', 'PartnerCompany',
                                                'Partner', 'Restaurant', 'Payment', 'Nickname', 'Datetime']])

            # Clear and add new data
            worksheet.clear()
            worksheet.update_values('A1', [['Date', 'Manager', 'ManagerCompany', 'PartnerCompany',
                                            'Partner', 'Restaurant', 'Payment', 'Nickname', 'Datetime']])
            worksheet.update_values('A2', data)

            logger.info(f"Synced {len(bookings)} bookings to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Error syncing bookings: {e}")
            return False


async def scheduled_sync():
    """Main sync task"""
    sync = GoogleSheetsSync()
    if await sync.sync_restaurants_from_google_sheets(
        spreadsheet_name="Restaurants",
        worksheet_name="RestaurantsList"
    ):
        logger.info("✅ Restaurants sync completed")
    else:
        logger.error("❌ Restaurants sync error")


async def start_sync_scheduler():
    """Start sync scheduler"""
    scheduler = AsyncIOScheduler()

    # Sync every 5 minutes
    scheduler.add_job(
        scheduled_sync,
        'interval',
        minutes=5,
        next_run_time=datetime.now()
    )

    scheduler.start()
    logger.info("🔄 Affiliate sync scheduler started")

    await scheduled_sync()