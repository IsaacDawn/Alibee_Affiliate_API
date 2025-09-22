# backend/routes/health.py
from fastapi import APIRouter
from datetime import datetime
from config.settings import settings
from database.connection import db_ops

router = APIRouter()

@router.get("/health")
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db_status = "connected"
        try:
            stats = db_ops.get_stats()
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Check AliExpress API configuration
        aliexpress_status = "configured" if settings.is_aliexpress_configured() else "not_configured"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": db_status,
            "aliexpress_api": aliexpress_status,
            "environment": {
                "daily_products_enabled": settings.DAILY_PRODUCTS_ENABLED,
                "exchange_rate_enabled": settings.EXCHANGE_RATE_ENABLED
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/status")
def health_simple():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "Alibee Affiliator API is running"
    }
