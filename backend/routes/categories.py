# backend/routes/categories.py
from fastapi import APIRouter
from utils.helpers import get_categories

router = APIRouter()

@router.get("/categories")
def get_categories_endpoint():
    """Get available categories"""
    try:
        categories = get_categories()
        return {
            "categories": categories,
            "total": len(categories),
            "message": "Categories retrieved successfully"
        }
    except Exception as e:
        return {
            "categories": [],
            "total": 0,
            "error": str(e),
            "message": "Failed to retrieve categories"
        }

@router.get("/test-categories")
def test_categories():
    """Test categories endpoint"""
    categories = get_categories()
    return {
        "status": "success",
        "categories": categories,
        "count": len(categories),
        "message": "Categories test successful"
    }
