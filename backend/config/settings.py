# Application settings and configuration
import os
from dotenv import load_dotenv

load_dotenv()

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# AliExpress API Configuration
ALIEXPRESS_CONFIG = {
    'APP_KEY': os.getenv('ALIEXPRESS_APP_KEY'),
    'APP_SECRET': os.getenv('ALIEXPRESS_APP_SECRET'),
    'BASE_URL': 'https://api-sg.aliexpress.com/sync',
    'TIMEOUT': 30,
}

# Application Settings
APP_CONFIG = {
    'TITLE': 'Alibee Affiliator API',
    'VERSION': '1.0.0',
    'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
    'HOST': os.getenv('HOST', '0.0.0.0'),
    'PORT': int(os.getenv('PORT', 8080)),
}

# Cache Settings
CACHE_CONFIG = {
    'ENABLED': os.getenv('CACHE_ENABLED', 'True').lower() == 'true',
    'TTL': int(os.getenv('CACHE_TTL', 300)),  # 5 minutes
    'MAX_SIZE': int(os.getenv('CACHE_MAX_SIZE', 1000)),
}

# Logging Configuration
LOGGING_CONFIG = {
    'LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
    'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'FILE': os.getenv('LOG_FILE', 'app.log'),
}
