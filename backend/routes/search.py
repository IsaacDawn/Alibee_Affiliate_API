# backend/routes/search.py
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from services.aliexpress import aliexpress_service
from database.connection import db_ops
from utils.helpers import get_demo_products, validate_pagination_params, merge_product_with_saved_info, filter_products_by_video, sort_products
from config.settings import settings
import requests

router = APIRouter()

@router.get("/search")
def search_products_with_fallback(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    categoryId: Optional[str] = Query(None, description="Category ID"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
    hot: bool = Query(False, description="Hot products only"),
    target_currency: str = Query("USD", description="Target currency"),
    target_language: str = Query("EN", description="Target language"),
    demo: bool = Query(False, description="Use demo mode"),
    hasVideo: Optional[bool] = Query(None, description="Has video"),
    sort: str = Query(None, description="Sort order"),
    minPrice: Optional[float] = Query(None, description="Minimum price"),
    maxPrice: Optional[float] = Query(None, description="Maximum price"),
):
    """Search products with demo fallback - guaranteed to return results"""
    
    # Validate pagination
    page, page_size = validate_pagination_params(page, pageSize)
    
    # Demo mode or API not configured or use demo as fallback
    if demo or not settings.is_aliexpress_configured():
        sample_products = get_demo_products(q)  # Pass search query to demo products
        
        # Apply filters
        if hasVideo is not None:
            sample_products = filter_products_by_video(sample_products, hasVideo)
        
        # Apply sorting
        sample_products = sort_products(sample_products, sort)
        
        return {
            "items": sample_products,
            "page": page,
            "pageSize": page_size,
            "total": len(sample_products),
            "hasMore": len(sample_products) >= page_size,
            "method": "demo_search",
            "source": "demo_data",
            "demo_mode": True
        }
    
    # Always use regular search (not hot products)
    hot = False
    
    # Continue with real API call
    return search_products_real(request, q, categoryId, page, page_size, hot, target_currency, target_language, hasVideo, sort, minPrice, maxPrice)

@router.post("/set-api-keys")
async def set_api_keys(request: Request):
    """Set AliExpress API keys temporarily"""
    try:
        body = await request.json()
        app_key = body.get('app_key')
        app_secret = body.get('app_secret')
        
        if not app_key or not app_secret:
            return {
                "status": "error",
                "message": "app_key and app_secret are required"
            }
        
        import os
        os.environ['APP_KEY'] = app_key
        os.environ['APP_SECRET'] = app_secret
        
        # Update settings
        from config.settings import settings
        settings.APP_KEY = app_key
        settings.APP_SECRET = app_secret
        
        return {
            "status": "success",
            "message": "API keys set successfully",
            "configured": settings.is_aliexpress_configured()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to set API keys: {str(e)}"
        }

@router.get("/api-status")
def get_api_status():
    """Get AliExpress API status"""
    from config.settings import settings
    
    return {
        "aliexpress_configured": settings.is_aliexpress_configured(),
        "app_key_set": bool(settings.APP_KEY),
        "app_secret_set": bool(settings.APP_SECRET),
        "message": "AliExpress API is configured" if settings.is_aliexpress_configured() else "AliExpress API needs configuration"
    }

@router.get("/test-ali")
def test_aliexpress_api():
    """Test AliExpress API connection"""
    try:
        from services.aliexpress import AliExpressClient
        
        client = AliExpressClient()
        result = client.search_products(keywords="iphone", page=1, page_size=3)
        
        if result:
            return {
                "status": "success",
                "message": "AliExpress API is working",
                "result": result,
                "items_count": len(result.get('products', {}).get('product', [])) if result.get('products') else 0
            }
        else:
            return {
                "status": "error",
                "message": "AliExpress API returned no results",
                "result": None
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"AliExpress API error: {str(e)}",
            "result": None
        }

@router.get("/search-api")
def search_products_real(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    categoryId: Optional[str] = Query(None, description="Category ID"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
    hot: bool = Query(False, description="Hot products only"),
    target_currency: str = Query("USD", description="Target currency"),
    target_language: str = Query("EN", description="Target language"),
    hasVideo: Optional[bool] = Query(None, description="Has video"),
    sort: str = Query("volume_desc", description="Sort order"),
    minPrice: Optional[float] = Query(None, description="Minimum price"),
    maxPrice: Optional[float] = Query(None, description="Maximum price"),
):
    """Direct product search from AliExpress API"""
    
    if not settings.is_aliexpress_configured():
        raise HTTPException(
            status_code=400, 
            detail="AliExpress API not configured. Please set APP_KEY and APP_SECRET in .env file."
        )
    
    # Validate pagination
    page, page_size = validate_pagination_params(page, pageSize)
    
    # Always use regular search (not hot products)
    hot = False
    
    try:
        # Search products using AliExpress service
        result = aliexpress_service.search_products_with_filters(
            query=q,
            category_id=categoryId,
            page=page,
            page_size=page_size,
            hot=hot,
            sort=sort,
            min_price=minPrice,
            max_price=maxPrice,
            has_video=hasVideo
        )
        
        items = result.get('items', [])
        
        # If no items, try direct parsing from raw result
        if not items and result:
            try:
                # Get raw AliExpress result
                from services.aliexpress import AliExpressClient
                client = AliExpressClient()
                raw_result = client.search_products(keywords=q or "phone", page=page, page_size=page_size)
                
                if raw_result and 'aliexpress_affiliate_product_query_response' in raw_result:
                    resp = raw_result['aliexpress_affiliate_product_query_response']
                    if 'resp_result' in resp and 'result' in resp['resp_result']:
                        inner_result = resp['resp_result']['result']
                        if 'products' in inner_result and 'product' in inner_result['products']:
                            product_list = inner_result['products']['product']
                            if isinstance(product_list, list) and len(product_list) > 0:
                                items = []
                                for item in product_list:
                                    try:
                                        normalized_item = {
                                            'product_id': item.get('product_id', ''),
                                            'product_title': item.get('product_title', ''),
                                            'product_main_image_url': item.get('product_main_image_url', ''),
                                            'product_video_url': item.get('product_video_url', ''),
                                            'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                                            'sale_price_currency': item.get('sale_price_currency', 'USD'),
                                            'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                                            'original_price_currency': item.get('original_price_currency', 'USD'),
                                            'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                                            'rating_weighted': float(item.get('rating_weighted', 0)) if item.get('rating_weighted') else 0,
                                            'first_level_category_id': item.get('first_level_category_id', ''),
                                            'promotion_link': item.get('promotion_link', ''),
                                            'commission_rate': float(item.get('commission_rate', 0)) if item.get('commission_rate') else 0,
                                            'discount': int(item.get('discount', 0)) if item.get('discount') else 0,
                                            'saved_at': None
                                        }
                                        items.append(normalized_item)
                                    except Exception as e:
                                        print(f"Error normalizing product item: {e}")
                                        continue
            except Exception as e:
                print(f"Error in direct parsing: {e}")
        
        # If no items, try direct parsing
        if not items:
            # Get the raw AliExpress result from client
            from services.aliexpress import AliExpressClient
            client = AliExpressClient()
            raw_result = client.search_products(keywords=q, page=page, page_size=page_size)
            
            if raw_result and 'aliexpress_affiliate_product_query_response' in raw_result:
                resp = raw_result['aliexpress_affiliate_product_query_response']
                if 'resp_result' in resp and 'result' in resp['resp_result']:
                    inner_result = resp['resp_result']['result']
                    if 'products' in inner_result and 'product' in inner_result['products']:
                        product_list = inner_result['products']['product']
                        if isinstance(product_list, list):
                            items = []
                            for item in product_list:
                                try:
                                    normalized_item = {
                                        'product_id': item.get('product_id', ''),
                                        'product_title': item.get('product_title', ''),
                                        'product_main_image_url': item.get('product_main_image_url', ''),
                                        'product_video_url': item.get('product_video_url', ''),
                                        'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                                        'sale_price_currency': item.get('sale_price_currency', 'USD'),
                                        'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                                        'original_price_currency': item.get('original_price_currency', 'USD'),
                                        'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                                        'rating_weighted': float(item.get('rating_weighted', 0)) if item.get('rating_weighted') else 0,
                                        'first_level_category_id': item.get('first_level_category_id', ''),
                                        'promotion_link': item.get('promotion_link', ''),
                                        'commission_rate': float(item.get('commission_rate', 0)) if item.get('commission_rate') else 0,
                                        'discount': int(item.get('discount', 0)) if item.get('discount') else 0,
                                        'saved_at': None
                                    }
                                    items.append(normalized_item)
                                except Exception as e:
                                    print(f"Error normalizing product item: {e}")
                                    continue
        
        # If no products found from AliExpress API, return empty results
        if not items:
            print("No products found from AliExpress API")
            print(f"Search parameters: q={q}, categoryId={categoryId}, hot={hot}")
            
            # Try with different keywords
            if q:
                print(f"Trying with different keywords for: {q}")
                # Try with the original query but with broader search
                broad_result = aliexpress_service.search_products_with_filters(
                    query=q,  # Use original query instead of hardcoded "phone"
                    category_id=categoryId,
                    page=page,
                    page_size=page_size,
                    hot=hot,
                    sort=sort,
                    min_price=minPrice,
                    max_price=maxPrice,
                    has_video=hasVideo
                )
                items = broad_result.get('items', [])
                if items:
                    print(f"Found {len(items)} products with broader search for: {q}")
            
            # Try with hot products as fallback
            if not items:
                print("Trying with hot products as fallback")
                hot_result = aliexpress_service.search_products_with_filters(
                    query=None,
                    category_id=categoryId,
                    page=page,
                    page_size=page_size,
                    hot=True,
                    sort=sort,
                    min_price=minPrice,
                    max_price=maxPrice,
                    has_video=hasVideo
                )
                items = hot_result.get('items', [])
                if items:
                    print(f"Found {len(items)} hot products")
        
        # Check which products are saved and add saved_at info
        if items:
            try:
                product_ids = [str(item.get('product_id', '')) for item in items if item.get('product_id')]
                saved_products_info = db_ops.get_saved_products_info(product_ids)
                
                # Merge saved product info with items
                for item in items:
                    product_id = str(item.get('product_id', ''))
                    if product_id in saved_products_info:
                        item = merge_product_with_saved_info(item, saved_products_info[product_id])
                    else:
                        item['saved_at'] = None
                        
            except Exception as e:
                print(f"Warning: Could not check saved products: {e}")
                for item in items:
                    item['saved_at'] = None
        
        # Apply client-side sorting since AliExpress API sorting may not work as expected
        if sort and sort != "volume_desc":
            items = sort_products(items, sort)
        
        # Apply video filter if needed
        if hasVideo is not None:
            items = filter_products_by_video(items, hasVideo)
        
        return {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "hasMore": len(items) >= page_size,
            "method": result.get('method', 'aliexpress.affiliate.product.query'),
            "source": result.get('source', 'aliexpress_api'),
            "live": True
        }
        
    except Exception as e:
        print(f"Error in search_products_real: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search-demo")
def search_products_demo(
    request: Request,
    q: Optional[str] = None,
    categoryId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    hot: bool = False,
    target_currency: str = "USD",
    target_language: str = "EN",
    demo: bool = False
):
    """Search products with demo fallback"""
    
    # Validate pagination
    page, page_size = validate_pagination_params(page, pageSize)
    
    if demo or not settings.is_aliexpress_configured():
        sample_products = get_demo_products()
        
        return {
            "items": sample_products,
            "page": page,
            "pageSize": page_size,
            "total": len(sample_products),
            "hasMore": len(sample_products) >= page_size,
            "method": "demo_search",
            "source": "demo_data",
            "demo_mode": True
        }
    
    # Continue with real API call
    return search_products_real(request, q, categoryId, page, page_size, hot, target_currency, target_language, None, "volume_desc", None, None)

@router.get("/search-demo-v2")
def search_products_with_demo_fallback(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    categoryId: Optional[str] = Query(None, description="Category ID"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
    hot: bool = Query(False, description="Hot products only"),
    target_currency: str = Query("USD", description="Target currency"),
    target_language: str = Query("EN", description="Target language"),
    demo: bool = Query(False, description="Use demo mode"),
):
    """Search products with demo fallback v2"""
    
    # Validate pagination
    page, page_size = validate_pagination_params(page, pageSize)
    
    if demo or not settings.is_aliexpress_configured():
        sample_products = get_demo_products()
        
        return {
            "items": sample_products,
            "page": page,
            "pageSize": page_size,
            "total": len(sample_products),
            "hasMore": len(sample_products) >= page_size,
            "method": "demo_search",
            "source": "demo_data",
            "demo_mode": True
        }
    
    # Continue with real API call
    return search_products_real(request, q, categoryId, page, page_size, hot, target_currency, target_language, None, "volume_desc", None, None)
