import logging
from peewee import SqliteDatabase

# налаштування логера
logger = logging.getLogger(__name__)

# підключення до SQLite з WAL-журналом
db = SqliteDatabase('products.db', pragmas={'journal_mode': 'wal'})

def initialize_database():
    """
    Ініціалізує з'єднання з базою та створює таблиці.
    Викликається при старті додатку.
    """
    from backend.data.models import Product  # щоб уникнути циклічних імпортів
    db.connect()
    db.create_tables([Product])
    logger.info("База даних ініціалізована, таблиці створені.")

