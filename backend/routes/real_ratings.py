"""
Real Ratings API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from services.real_rating_service import real_rating_service
import asyncio
import concurrent.futures

router = APIRouter()

@router.get("/real-rating/{product_id}")
async def get_real_rating(product_id: str):
    """
    دریافت ریت واقعی یک محصول
    
    Args:
        product_id (str): شناسه محصول
        
    Returns:
        Dict: اطلاعات ریت واقعی
    """
    try:
        # اجرای درخواست در thread pool برای جلوگیری از blocking
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            rating = await loop.run_in_executor(
                executor, 
                real_rating_service.get_rating_from_product_id, 
                product_id
            )
        
        if rating:
            return {
                "success": True,
                "product_id": product_id,
                "rating": rating.get('rating'),
                "review_count": rating.get('review_count'),
                "source": "aliexpress_website"
            }
        else:
            return {
                "success": False,
                "product_id": product_id,
                "message": "No rating found",
                "source": "aliexpress_website"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching real rating: {str(e)}")

@router.post("/real-ratings/batch")
async def get_batch_real_ratings(product_ids: List[str]):
    """
    دریافت ریت‌های واقعی چندین محصول
    
    Args:
        product_ids (List[str]): لیست شناسه محصولات
        
    Returns:
        Dict: ریت‌های محصولات
    """
    try:
        if len(product_ids) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 products allowed per batch")
        
        # اجرای درخواست در thread pool
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            ratings = await loop.run_in_executor(
                executor, 
                real_rating_service.batch_get_ratings, 
                product_ids
            )
        
        return {
            "success": True,
            "ratings": ratings,
            "total_processed": len(product_ids),
            "found_ratings": len(ratings),
            "source": "aliexpress_website"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching batch ratings: {str(e)}")

@router.get("/real-rating-url")
async def get_real_rating_from_url(product_url: str = Query(..., description="Product URL")):
    """
    دریافت ریت واقعی از URL محصول
    
    Args:
        product_url (str): URL محصول
        
    Returns:
        Dict: اطلاعات ریت واقعی
    """
    try:
        # اجرای درخواست در thread pool
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            rating = await loop.run_in_executor(
                executor, 
                real_rating_service.get_product_rating_from_url, 
                product_url
            )
        
        if rating:
            return {
                "success": True,
                "product_url": product_url,
                "rating": rating.get('rating'),
                "review_count": rating.get('review_count'),
                "source": "aliexpress_website"
            }
        else:
            return {
                "success": False,
                "product_url": product_url,
                "message": "No rating found",
                "source": "aliexpress_website"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching real rating: {str(e)}")

