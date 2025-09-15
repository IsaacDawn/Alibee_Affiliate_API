# Product-related routes
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from backend.services.database import db_service
from backend.services.aliexpress import aliexpress_service
from backend.models.product import SaveProductRequest, ApiResponse, PaginatedResponse, ProductResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=PaginatedResponse)
async def get_products(
    q: Optional[str] = None,
    categoryId: Optional[str] = None,
    hasVideo: Optional[bool] = None,
    sort: str = Query("volume_desc", pattern="^(volume_desc|discount_desc|rating_desc)$"),
    page: int = 1,
    pageSize: int = 20,
):
    """Get saved products from database"""
    try:
        filters = {
            'q': q,
            'categoryId': categoryId,
            'hasVideo': hasVideo,
            'sort': sort,
        }
        
        items, has_more = db_service.get_products(filters, page, pageSize)
        
        return PaginatedResponse(
            items=[ProductResponse(**item) for item in items],
            page=page,
            pageSize=pageSize,
            hasMore=has_more
        )
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=PaginatedResponse)
async def search_products(
    q: Optional[str] = None,
    categoryId: Optional[str] = None,
    hasVideo: Optional[bool] = None,
    sort: str = Query("volume_desc", pattern="^(volume_desc|discount_desc|rating_desc)$"),
    page: int = 1,
    pageSize: int = 20,
):
    """Search products using AliExpress API"""
    try:
        if not aliexpress_service.is_configured():
            raise HTTPException(status_code=503, detail="AliExpress API not configured")
        
        # Search using AliExpress API
        raw_response = aliexpress_service.search_products(
            query=q or "phone",
            page=page,
            page_size=pageSize,
            category_id=categoryId,
            has_video=hasVideo,
            sort=sort
        )
        
        items = aliexpress_service.normalize_products(raw_response)
        
        # Check which products are saved
        if items:
            product_ids = [item.get('product_id', '') for item in items if item.get('product_id')]
            saved_products = db_service.get_saved_products_for_items(product_ids)
            
            for item in items:
                product_id = str(item.get('product_id', ''))
                if product_id in saved_products:
                    item['saved_at'] = saved_products[product_id].isoformat() if saved_products[product_id] else None
                else:
                    item['saved_at'] = None
        
        return PaginatedResponse(
            items=[ProductResponse(**item) for item in items],
            page=page,
            pageSize=pageSize,
            hasMore=len(items) == pageSize
        )
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/demo", response_model=PaginatedResponse)
async def get_demo_products():
    """Get demo products for presentation"""
    try:
        if not aliexpress_service.is_configured():
            raise HTTPException(status_code=503, detail="AliExpress API not configured")
        
        # Get hot products as demo
        raw_response = aliexpress_service.get_hot_products(page=1, page_size=20)
        items = aliexpress_service.normalize_products(raw_response)
        
        # Check which products are saved
        if items:
            product_ids = [item.get('product_id', '') for item in items if item.get('product_id')]
            saved_products = db_service.get_saved_products_for_items(product_ids)
            
            for item in items:
                product_id = str(item.get('product_id', ''))
                if product_id in saved_products:
                    item['saved_at'] = saved_products[product_id].isoformat() if saved_products[product_id] else None
                else:
                    item['saved_at'] = None
        
        return PaginatedResponse(
            items=[ProductResponse(**item) for item in items],
            page=1,
            pageSize=20,
            hasMore=False
        )
    except Exception as e:
        logger.error(f"Error getting demo products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save", response_model=ApiResponse)
async def save_product(product: SaveProductRequest):
    """Save a product to saved_products table"""
    try:
        product_data = product.dict()
        success = db_service.save_product(product.product_id, product_data)
        
        if success:
            return ApiResponse(success=True, message="Product saved successfully")
        else:
            return ApiResponse(success=False, error="Failed to save product")
    except Exception as e:
        logger.error(f"Error saving product: {e}")
        return ApiResponse(success=False, error=str(e))

@router.delete("/unsave/{product_id}", response_model=ApiResponse)
async def unsave_product(product_id: str):
    """Remove a product from saved_products table"""
    try:
        success = db_service.unsave_product(product_id)
        
        if success:
            return ApiResponse(success=True, message="Product unsaved successfully")
        else:
            return ApiResponse(success=False, error="Product not found in saved list")
    except Exception as e:
        logger.error(f"Error unsaving product: {e}")
        return ApiResponse(success=False, error=str(e))
