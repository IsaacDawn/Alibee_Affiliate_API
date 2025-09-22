# backend/config/settings.py
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # Database Configuration
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'alibee_affiliate'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    # AliExpress API Configuration
    APP_KEY = os.getenv('APP_KEY')
    APP_SECRET = os.getenv('APP_SECRET')
    ALIEXPRESS_BASE_URL = "https://api-sg.aliexpress.com/sync"
    
    # CORS Configuration
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Application Configuration
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 20))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", 100))
    
    # Background Tasks Configuration
    DAILY_PRODUCTS_ENABLED = os.getenv('DAILY_PRODUCTS_ENABLED', 'false').lower() == 'true'
    
    # Exchange Rate Configuration (if needed)
    EXCHANGE_RATE_ENABLED = os.getenv('EXCHANGE_RATE_ENABLED', 'false').lower() == 'true'
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration"""
        return cls.DB_CONFIG.copy()
    
    @classmethod
    def is_aliexpress_configured(cls) -> bool:
        """Check if AliExpress API is properly configured"""
        return bool(cls.APP_KEY and cls.APP_SECRET)
    
    @classmethod
    def get_cors_config(cls) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            'allow_origins': cls.ALLOWED_ORIGINS,
            'allow_credentials': True,
            'allow_methods': ["*"],
            'allow_headers': ["*"],
        }

# Create global settings instance
settings = Settings()
