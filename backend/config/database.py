# Database configuration
import os
from dotenv import load_dotenv

load_dotenv()

# MySQL Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'auth_plugin': 'mysql_native_password',
    'autocommit': True,
}

# Database table names
TABLES = {
    'PRODUCTS': 'aliexpress_products',
    'SAVED_PRODUCTS': 'saved_products',
    'CATEGORIES': 'categories',
    'AFFILIATE_LINKS': 'affiliate_links',
}

# Default pagination settings
DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', 20))
MAX_PAGE_SIZE = 100
