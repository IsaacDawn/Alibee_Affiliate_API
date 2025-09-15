# Statistics and health routes
from fastapi import APIRouter, HTTPException
from backend.services.database import db_service
from backend.services.aliexpress import aliexpress_service
from backend.models.stats import StatsResponse, SystemStatusResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/", response_model=StatsResponse)
async def get_stats():
    """Get application statistics"""
    try:
        saved_products = db_service.get_saved_products_count()
        total_products = db_service.get_total_products_count()
        
        # TODO: Implement actual search count
        total_searches = 0
        
        return StatsResponse(
            totalProducts=total_products,
            savedProducts=saved_products,
            totalSearches=total_searches
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=SystemStatusResponse)
async def get_health():
    """Get system health status"""
    try:
        # Check database connection
        try:
            db_service.get_total_products_count()  # Just check connection
            db_status = "ok"
        except Exception as e:
            db_status = "error"
            logger.error(f"Database health check failed: {e}")
        
        # Check AliExpress API
        if aliexpress_service.is_configured():
            ali_client = "ok"
            ali_api_status = "آماده برای جستجو"
        else:
            ali_client = "not_configured"
            ali_api_status = "نیاز به تنظیم APP_KEY و APP_SECRET"
        
        return SystemStatusResponse(
            db=db_status,
            ali_client=ali_client,
            ali_api_status=ali_api_status
        )
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
