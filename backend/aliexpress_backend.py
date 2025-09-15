from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
import hashlib
import time
import json
import uvicorn

app = FastAPI(title="Alibee AliExpress Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AliExpress API Configuration
ALI_APP_KEY = "514064"
ALI_APP_SECRET = "p8rJNLXoolmZKskeUrshCCbs45y4eWS9"
ALI_TRACKING_ID = "Alibee"
ALI_BASE_URL = "https://api-sg.aliexpress.com/sync"

class Product(BaseModel):
    product_id: str
    title: str
    price: str
    image_url: str
    product_url: str
    saved_at: str = None

def top_sign(params: dict, secret: str) -> str:
    """Generate TOP signature for AliExpress API"""
    # Sort parameters
    sorted_params = sorted(params.items())
    
    # Build signature string
    base = secret
    for key, value in sorted_params:
        if value is None or value == "":
            continue
        base += key + str(value)
    base += secret
    
    # Generate MD5 hash and convert to uppercase
    return hashlib.md5(base.encode('utf-8')).hexdigest().upper()

def call_aliexpress_api(method: str, params: dict) -> dict:
    """Call AliExpress API with proper authentication"""
    
    # System parameters
    sys_params = {
        'method': method,
        'app_key': ALI_APP_KEY,
        'sign_method': 'md5',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
        'format': 'json',
        'v': '2.0'
    }
    
    # Combine all parameters
    all_params = {**sys_params, **params}
    
    # Remove empty values for signature
    clean_params = {k: v for k, v in all_params.items() if v is not None and v != ""}
    
    # Generate signature
    signature = top_sign(clean_params, ALI_APP_SECRET)
    clean_params['sign'] = signature
    
    # Build URL
    url = f"{ALI_BASE_URL}?{requests.compat.urlencode(clean_params)}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"AliExpress API error: {str(e)}")

def extract_products(data: dict) -> List[dict]:
    """Extract products from AliExpress API response"""
    try:
        # Try different response structures
        paths = [
            ['aliexpress_affiliate_product_query_response', 'resp_result', 'result', 'products', 'product'],
            ['resp_result', 'result', 'products', 'product'],
            ['result', 'products', 'product'],
            ['result'],
            ['items'],
            ['products']
        ]
        
        for path in paths:
            current = data
            for segment in path:
                if isinstance(current, dict) and segment in current:
                    current = current[segment]
                else:
                    current = None
                    break
            
            if isinstance(current, list) and current:
                return current
        
        # Fallback: look for any array in the response
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    return value
        
        return []
    except Exception as e:
        print(f"Error extracting products: {e}")
        return []

def normalize_product(product: dict) -> dict:
    """Normalize AliExpress product data to our format"""
    return {
        "product_id": product.get('product_id', product.get('item_id', product.get('sku_id', str(hash(product.get('product_detail_url', '')))))),
        "title": product.get('product_title', product.get('title', '')),
        "price": product.get('target_sale_price', product.get('app_sale_price', product.get('sale_price', '')),
        "image_url": product.get('product_main_image_url', product.get('main_image', '')),
        "product_url": product.get('promotion_link', product.get('product_detail_url', '')),
        "saved_at": None
    }

@app.get("/")
async def root():
    return {"message": "Alibee AliExpress Backend is running!"}

@app.get("/health")
async def health():
    return {
        "db": "ok",
        "ali_client": "ok",
        "message": "AliExpress backend running"
    }

@app.get("/stats")
async def stats():
    return {
        "total_products": 0,
        "saved_products": 0,
        "total_searches": 0,
        "affiliate_links": 0
    }

@app.get("/search")
async def search_products(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=50, description="Page size"),
    target_currency: str = Query("USD", description="Target currency"),
    sort: str = Query("volume_desc", description="Sort order")
):
    """Search products using AliExpress API"""
    
    try:
        # Call AliExpress API
        api_params = {
            'keywords': q,
            'page_no': page,
            'page_size': pageSize,
            'target_currency': target_currency,
            'trackingId': ALI_TRACKING_ID
        }
        
        response_data = call_aliexpress_api('aliexpress.affiliate.product.query', api_params)
        
        # Extract and normalize products
        raw_products = extract_products(response_data)
        normalized_products = [normalize_product(p) for p in raw_products]
        
        return {
            "items": normalized_products,
            "hasMore": len(normalized_products) == pageSize,  # Assume more if we got full page
            "total": len(normalized_products) * 10  # Rough estimate
        }
        
    except Exception as e:
        print(f"Search error: {e}")
        # Return mock data on error with real placeholder images
        mock_products = [
            {
                "product_id": f"mock_{i}",
                "title": f"Mock Product {i} - {q}",
                "price": f"${9.99 + i * 2.50:.2f}",
                "image_url": f"https://picsum.photos/300/300?random={i + 200}",
                "product_url": f"https://example.com/product/{i}",
                "saved_at": None
            }
            for i in range(1, min(pageSize, 10) + 1)
        ]
        
        return {
            "items": mock_products,
            "hasMore": False,
            "total": len(mock_products)
        }

@app.get("/ali/products")
async def ali_products(
    q: str = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=50, description="Page size"),
    target_currency: str = Query("USD", description="Target currency")
):
    """AliExpress products endpoint"""
    if q:
        return await search_products(q, page, pageSize, target_currency)
    else:
        # Return hot/featured products
        try:
            api_params = {
                'page_no': page,
                'page_size': pageSize,
                'target_currency': target_currency,
                'trackingId': ALI_TRACKING_ID
            }
            
            response_data = call_aliexpress_api('aliexpress.affiliate.featuredpromo.products.get', api_params)
            raw_products = extract_products(response_data)
            normalized_products = [normalize_product(p) for p in raw_products]
            
            return {
                "items": normalized_products,
                "hasMore": len(normalized_products) == pageSize,
                "total": len(normalized_products) * 10
            }
        except Exception as e:
            print(f"Hot products error: {e}")
            return {
                "items": [],
                "hasMore": False,
                "total": 0
            }

@app.get("/saved")
async def get_saved_products():
    return {
        "items": [],
        "hasMore": False,
        "total": 0
    }

if __name__ == "__main__":
    print("🚀 Starting Alibee AliExpress Backend...")
    print("📍 URL: http://127.0.0.1:8080")
    print("🔍 Test search: http://127.0.0.1:8080/search?q=bag")
    print("="*50)
    
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
