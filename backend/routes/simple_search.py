# backend/routes/simple_search.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
import requests
import os
from datetime import datetime
import hashlib

router = APIRouter()

# AliExpress API Configuration
ALI_APP_KEY = os.getenv("APP_KEY", "514064")
ALI_APP_SECRET = os.getenv("APP_SECRET", "p8rJNLXoolmZKskeUrshCCbs45y4eWS9")
ALI_BASE_URL = os.getenv("ALI_SYNC_BASE", "https://api-sg.aliexpress.com/sync")
TRACKING_ID = os.getenv("TRACKING_ID", "Alibee")

def create_ali_sign(params: dict, secret: str) -> str:
    """Create AliExpress API signature"""
    sorted_params = sorted(params.items())
    base_string = secret
    for key, value in sorted_params:
        if value is not None and value != '':
            base_string += f"{key}{value}"
    base_string += secret
    return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()

async def search_aliexpress_products(query: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Search products from AliExpress API"""
    try:
        params = {
            'method': 'aliexpress.affiliate.product.query',
            'app_key': ALI_APP_KEY,
            'sign_method': 'md5',
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'json',
            'v': '2.0',
            'keywords': query,
            'page_no': page,
            'page_size': page_size,
            'target_language': 'en',
            'target_currency': 'USD',
            'trackingId': TRACKING_ID
        }
        
        sign = create_ali_sign(params, ALI_APP_SECRET)
        params['sign'] = sign
        
        response = requests.get(ALI_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        products = []
        if 'aliexpress_affiliate_product_query_response' in data:
            resp_result = data['aliexpress_affiliate_product_query_response'].get('resp_result', {})
            if 'result' in resp_result and 'products' in resp_result['result']:
                products_data = resp_result['result']['products']
                if isinstance(products_data, dict) and 'product' in products_data:
                    products = products_data['product']
                    if not isinstance(products, list):
                        products = [products]
        
        return {
            'items': products,
            'page': page,
            'pageSize': page_size,
            'total': len(products),
            'hasMore': len(products) >= page_size,
            'method': 'simple_search',
            'source': 'aliexpress'
        }
        
    except Exception as e:
        print(f"AliExpress API Error: {e}")
        return {
            'items': [],
            'page': page,
            'pageSize': page_size,
            'total': 0,
            'hasMore': False,
            'method': 'simple_search',
            'source': 'error'
        }

@router.get("/search")
async def simple_search(
    q: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
    use_api: bool = Query(True, description="Use AliExpress API"),
):
    """
    Simple search endpoint - search products by keyword
    """
    
    # If no query, return empty results
    if not q or not q.strip():
        return {
            "items": [],
            "page": page,
            "pageSize": pageSize,
            "total": 0,
            "hasMore": False,
            "method": "simple_search",
            "source": "no_query"
        }
    
    # Use AliExpress API if use_api is True, otherwise return mock data
    if use_api:
        print(f"Searching AliExpress API for: {q}")
        return await search_aliexpress_products(q, page, pageSize)
    else:
        print(f"Using mock data for: {q}")
        return {
            "items": [
                {
                    "product_id": f"mock_{q}_1",
                    "product_title": f"Mock {q.title()} Product 1",
                    "product_main_image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop&crop=center",
                    "sale_price": 29.99,
                    "sale_price_currency": "USD",
                    "original_price": 49.99,
                    "original_price_currency": "USD",
                    "lastest_volume": 100,
                    "rating_weighted": 4.5,
                    "first_level_category_id": "100001",
                    "promotion_link": f"https://example.com/{q}",
                    "commission_rate": 8.0,
                    "discount": 40,
                    "saved_at": None
                }
            ],
            "page": page,
            "pageSize": pageSize,
            "total": 1,
            "hasMore": False,
            "method": "simple_search",
            "source": "mock_data"
        }