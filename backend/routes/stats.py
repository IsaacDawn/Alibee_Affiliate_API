# backend/routes/stats.py
from fastapi import APIRouter
from database.connection import db_ops
from utils.helpers import create_success_response

router = APIRouter()

@router.get("/stats")
def get_stats():
    """Get application statistics"""
    try:
        # Get database stats
        db_stats = db_ops.get_stats()
        
        # Add additional stats
        stats = {
            "totalProducts": db_stats.get('totalProducts', 0),
            "savedProducts": db_stats.get('savedProducts', 0),
            "totalSearches": 0,  # This would need to be tracked separately
            "activeUsers": 0,    # This would need to be tracked separately
            "affiliate_links": 0, # This would need to be tracked separately
            "recent_searches": 0  # This would need to be tracked separately
        }
        
        return create_success_response(data=stats, message="Stats retrieved successfully")
        
    except Exception as e:
        return {
            "totalProducts": 0,
            "savedProducts": 0,
            "totalSearches": 0,
            "activeUsers": 0,
            "affiliate_links": 0,
            "recent_searches": 0,
            "error": str(e)
        }
