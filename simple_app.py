from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import mysql.connector
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AliExpress API Configuration
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

# Database Configuration
DB_CFG = dict(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "alibee_affiliate"),
    auth_plugin='mysql_native_password',
    autocommit=True,
)

app = FastAPI(title="Alibee Affiliate API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Product(BaseModel):
    product_id: str
    title: str
    price: str
    image_url: str
    product_url: str
    saved_at: str = None

class Stats(BaseModel):
    total_products: int = 0
    saved_products: int = 0
    total_searches: int = 0
    affiliate_links: int = 0

class SystemStatus(BaseModel):
    db: str = "ok"
    ali_client: str = "ok"
    message: str = None

class SaveProductRequest(BaseModel):
    product_id: str
    title: str
    selected_price: Dict[str, Any]
    video_url: Optional[str] = None
    image_main: Optional[str] = None
    images_extra: Optional[List[str]] = []
    lastest_volume: Optional[int] = None
    rating_weighted: Optional[float] = None
    category_id: Optional[str] = None
    promotion_link: Optional[str] = None
    product_url: Optional[str] = None
    shop_url: Optional[str] = None
    shop_title: Optional[str] = None
    discount_percentage: Optional[float] = None
    commission_rate: Optional[float] = None
    commission_value: Optional[float] = None
    product_detail_url: Optional[str] = None
    product_sku: Optional[str] = None
    product_brand: Optional[str] = None
    product_condition: Optional[str] = None
    product_warranty: Optional[str] = None
    product_shipping_info: Optional[str] = None
    product_return_policy: Optional[str] = None

class UnsaveRequest(BaseModel):
    product_id: str

@app.get("/")
async def root():
    return {"message": "Alibee Affiliate API is running!"}

@app.get("/health")
async def health():
    return SystemStatus()

@app.get("/stats")
async def stats():
    try:
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Get saved products count
        cur.execute("SELECT COUNT(*) FROM saved_products")
        saved_products = cur.fetchone()[0]
        
        # Get total searches (you might have a searches table)
        # For now, we'll use a default value
        total_searches = 0
        
        # Get affiliate links count (you might have an affiliate_links table)
        # For now, we'll use saved_products as a proxy
        affiliate_links = saved_products
        
        cur.close()
        cn.close()
        
        return {
            "total_products": 0,  # Keep for compatibility
            "saved_products": saved_products,
            "total_searches": total_searches,
            "affiliate_links": affiliate_links
        }
        
    except mysql.connector.Error as e:
        print(f"Database error in stats: {e}")
        # Fallback to default values
        return {
            "total_products": 0,
            "saved_products": 0,
            "total_searches": 0,
            "affiliate_links": 0
        }
    except Exception as e:
        print(f"Unexpected error in stats: {e}")
        return {
            "total_products": 0,
            "saved_products": 0,
            "total_searches": 0,
            "affiliate_links": 0
        }

@app.get("/ali/products")
async def search_products(
    q: str = None,
    page: int = 1,
    pageSize: int = 20,
    target_currency: str = "USD"
):
    """
    Search products from AliExpress API (alias for /search)
    """
    # Redirect to the main search endpoint
    return await search_products_endpoint(q, page, pageSize, target_currency, "volume_desc")

@app.get("/search")
async def search_products_endpoint(
    q: str = None,
    page: int = 1,
    pageSize: int = 20,
    target_currency: str = "USD",
    sort: str = "volume_desc"
):
    """
    Search products from AliExpress API
    """
    if not APP_KEY or not APP_SECRET:
        # Return mock data when AliExpress API is not configured
        print("⚠️  AliExpress API not configured. Using mock data.")
        return {
            "items": [
                {
                    "product_id": f"mock_{page}_{i}",
                    "product_title": f"Mock Product {i} - {q or 'Product'} - High Quality",
                    "product_description": f"This is a mock product {i} for testing. Real AliExpress API not configured.",
                    "sale_price": 15 + i * 3,
                    "sale_price_currency": target_currency,
                    "original_price": 30 + i * 6,
                    "original_price_currency": target_currency,
                    "product_main_image_url": f"https://picsum.photos/300/300?random={i + 100}",
                    "images_extra": [
                        f"https://picsum.photos/300/300?random={i+150}",
                        f"https://picsum.photos/300/300?random={i+250}",
                        f"https://picsum.photos/300/300?random={i+350}"
                    ],
                    "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" if i % 3 == 0 else "",
                    "promotion_link": f"https://example.com/search/{i}",
                    "lastest_volume": 200 + i * 30,
                    "rating_weighted": 4.2 + (i % 4) * 0.15,
                    "saved_at": None
                }
                for i in range(1, pageSize + 1)
            ],
            "page": page,
            "pageSize": pageSize,
            "hasMore": page < 3,
            "total": pageSize * 3,
            "warning": "Using mock data - AliExpress API not configured"
        }

    try:
        import hashlib
        import time
        import requests
        
        # Base URL for AliExpress API
        base_url = 'https://api-sg.aliexpress.com/sync'
        
        # System parameters
        sys_params = {
            'method': 'aliexpress.affiliate.product.query',
            'app_key': APP_KEY,
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'format': 'json',
            'v': '2.0'
        }
        
        # API parameters
        api_params = {
            'page_no': page,
            'page_size': pageSize,
            'target_language': 'EN',
            'target_currency': target_currency,
            'trackingId': TRACKING_ID
        }
        
        # Add search parameters
        if q:
            api_params['keywords'] = q
        
        # Combine all parameters
        all_params = {**sys_params, **api_params}
        
        # Remove empty values
        clean_params = {k: v for k, v in all_params.items() if v is not None and v != ''}
        
        # Create MD5 signature
        def create_md5_signature(params, secret):
            # Sort parameters
            sorted_params = sorted(params.items())
            
            # Create base string: secret + key1value1key2value2... + secret
            base_string = secret
            for key, value in sorted_params:
                base_string += key + str(value)
            base_string += secret
            
            # Create MD5 hash and convert to uppercase
            return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()
        
        # Generate signature
        signature = create_md5_signature(clean_params, APP_SECRET)
        clean_params['sign'] = signature
        
        # Build URL
        url = base_url + '?' + '&'.join([f"{k}={v}" for k, v in clean_params.items()])
        
        # Make request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse response
        raw = response.json()
        
        # Extract products from response
        items = []
        if 'aliexpress_affiliate_product_query_response' in raw:
            resp = raw['aliexpress_affiliate_product_query_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    items = result['products']['product']
                    if not isinstance(items, list):
                        items = [items]
        
        # Check which products are saved by joining with saved_products table
        if items:
            try:
                cn = mysql.connector.connect(**DB_CFG)
                cur = cn.cursor()
                
                # Get product IDs from the items
                product_ids = [str(item.get('product_id', '')) for item in items if item.get('product_id')]
                
                if product_ids:
                    # Create placeholders for the IN clause
                    placeholders = ','.join(['%s'] * len(product_ids))
                    
                    # Query saved_products table to get saved_at timestamps
                    cur.execute(f"""
                        SELECT product_id, saved_at 
                        FROM saved_products 
                        WHERE product_id IN ({placeholders})
                    """, product_ids)
                    
                    saved_products = {row[0]: row[1] for row in cur.fetchall()}
                    
                    # Add saved_at field and process images for items
                    for item in items:
                        product_id = str(item.get('product_id', ''))
                        if product_id in saved_products:
                            item['saved_at'] = saved_products[product_id].isoformat() if saved_products[product_id] else None
                        else:
                            item['saved_at'] = None
                        
                        # Process extra images from AliExpress API
                        if 'product_small_image_urls' in item and 'string' in item['product_small_image_urls']:
                            extra_images = item['product_small_image_urls']['string']
                            # Remove main image from extra images to avoid duplicates
                            main_image = item.get('product_main_image_url', '')
                            item['images_extra'] = [img for img in extra_images if img != main_image]
                        else:
                            item['images_extra'] = []
                
                cur.close(); cn.close()
            except Exception as e:
                # If database check fails, just continue without saved_at info
                print(f"Warning: Could not check saved products: {e}")
                for item in items:
                    item['saved_at'] = None

        return {
            "items": items,
            "page": page,
            "pageSize": pageSize,
            "hasMore": len(items) == pageSize,
            "total": len(items)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"AliExpress API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"AliExpress API request failed: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in search: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/saved")
async def get_saved_products(
    sort: str = Query("saved_at_desc", pattern="^(saved_at_desc|saved_at_asc|title_asc|title_desc|volume_desc|rating_desc)$"),
    page: int = 1,
    pageSize: int = 20
):
    """
    Fetch saved products from saved_products table in database.
    Note: This endpoint ignores search queries - it only returns saved products.
    """
    try:
        offset = (page - 1) * pageSize
        wh, params = ["1=1"], []

        # Ignore search queries - only return saved products
        # No search filtering for saved products

        order = {
            "saved_at_desc": "saved_at DESC",
            "saved_at_asc": "saved_at ASC",
            "title_asc": "title ASC",
            "title_desc": "title DESC",
            "volume_desc": "lastest_volume DESC",
            "rating_desc": "rating_weighted DESC",
        }[sort]

        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Get total count
        cur.execute(f"SELECT COUNT(*) FROM saved_products WHERE {' AND '.join(wh)}", params)
        total = cur.fetchone()[0]
        
        # Get products with all fields
        cur.execute(f"""
            SELECT 
                product_id, title, image_main, video_url,
                sale_price, sale_price_currency, original_price, original_price_currency,
                lastest_volume, rating_weighted, category_id, promotion_link,
                product_url, shop_url, shop_title, discount_percentage,
                commission_rate, commission_value, images_extra, product_detail_url,
                product_sku, product_brand, product_condition, product_warranty,
                product_shipping_info, product_return_policy, saved_at
            FROM saved_products 
            WHERE {' AND '.join(wh)}
            ORDER BY {order}
            LIMIT %s OFFSET %s
        """, params + [pageSize, offset])
        
        rows = cur.fetchall()
        cur.close()
        cn.close()

        # Convert database rows to frontend format
        items = []
        for row in rows:
            item = {
                "product_id": row[0],
                "product_title": row[1],
                "product_main_image_url": row[2],
                "product_video_url": row[3] if row[3] else "",
                "sale_price": float(row[4]) if row[4] else 0,
                "sale_price_currency": row[5] if row[5] else "USD",
                "original_price": float(row[6]) if row[6] else 0,
                "original_price_currency": row[7] if row[7] else "USD",
                "lastest_volume": row[8] if row[8] else 0,
                "rating_weighted": float(row[9]) if row[9] else 0,
                "category_id": row[10] if row[10] else "",
                "promotion_link": row[11] if row[11] else "",
                "product_url": row[12] if row[12] else "",
                "shop_url": row[13] if row[13] else "",
                "shop_title": row[14] if row[14] else "",
                "discount_percentage": float(row[15]) if row[15] else 0,
                "commission_rate": float(row[16]) if row[16] else 0,
                "commission_value": float(row[17]) if row[17] else 0,
                "images_extra": json.loads(row[18]) if row[18] else [],
                "product_detail_url": row[19] if row[19] else "",
                "product_sku": row[20] if row[20] else "",
                "product_brand": row[21] if row[21] else "",
                "product_condition": row[22] if row[22] else "",
                "product_warranty": row[23] if row[23] else "",
                "product_shipping_info": row[24] if row[24] else "",
                "product_return_policy": row[25] if row[25] else "",
                "saved_at": row[26].isoformat() if row[26] else None
            }
            items.append(item)

        return {
            "items": items,
            "page": page,
            "pageSize": pageSize,
            "hasMore": len(items) == pageSize,
            "total": total
        }
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        # Fallback to mock data if database connection fails
        return {
            "items": [],
            "page": page,
            "pageSize": pageSize,
            "hasMore": False,
            "total": 0,
            "error": f"Database connection failed: {str(e)}"
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            "items": [],
            "page": page,
            "pageSize": pageSize,
            "hasMore": False,
            "total": 0,
            "error": f"Unexpected error: {str(e)}"
        }

@app.post("/save")
async def save_product(request: SaveProductRequest):
    """
    Save a product to saved_products table.
    """
    try:
        # Extract fields from request body
        product_id = request.product_id
        title = request.title
        image_main = request.image_main
        
        # Extract price information from selected_price
        selected_price = request.selected_price
        sale_price = selected_price.get("value", 0)
        sale_price_currency = selected_price.get("currency", "USD")
        original_price = selected_price.get("original")
        original_price_currency = selected_price.get("original_currency", "USD")
        
        promotion_link = request.promotion_link
        lastest_volume = request.lastest_volume or 0
        rating_weighted = request.rating_weighted or 0.0
        category_id = request.category_id
        video_url = request.video_url
        images_extra = json.dumps(request.images_extra or [])
        product_detail_url = request.product_detail_url or ""
        product_sku = request.product_sku or ""
        product_brand = request.product_brand or ""
        product_condition = request.product_condition or ""
        product_warranty = request.product_warranty or ""
        product_shipping_info = request.product_shipping_info or ""
        product_return_policy = request.product_return_policy or ""
        discount_percentage = request.discount_percentage or 0.0
        commission_rate = request.commission_rate or 0.0
        commission_value = request.commission_value or 0.0
        
        if not product_id or not title or not image_main:
            return {
                "success": False,
                "message": "product_id, title, and image_main are required",
                "saved": False
            }
        
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Check if product already exists
        cur.execute("SELECT COUNT(*) FROM saved_products WHERE product_id = %s", (product_id,))
        exists = cur.fetchone()[0] > 0
        
        if exists:
            return {
                "success": False,
                "message": f"Product {product_id} already exists in saved list",
                "saved": False
            }
        
        # Insert the product into saved_products table
        cur.execute("""
            INSERT INTO saved_products (
                product_id, title, image_main, sale_price, sale_price_currency,
                original_price, original_price_currency, promotion_link, lastest_volume,
                rating_weighted, category_id, video_url, images_extra, product_detail_url,
                product_sku, product_brand, product_condition, product_warranty,
                product_shipping_info, product_return_policy, discount_percentage,
                commission_rate, commission_value, saved_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """, (
            product_id, title, image_main, sale_price, sale_price_currency,
            original_price, original_price_currency, promotion_link, lastest_volume,
            rating_weighted, category_id, video_url, images_extra, product_detail_url,
            product_sku, product_brand, product_condition, product_warranty,
            product_shipping_info, product_return_policy, discount_percentage,
            commission_rate, commission_value
        ))
        
        cur.close()
        cn.close()
        
        return {
            "success": True,
            "message": f"Product {product_id} saved successfully",
            "saved": True
        }
        
    except mysql.connector.Error as e:
        print(f"Database error in save: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "saved": False
        }
    except Exception as e:
        print(f"Unexpected error in save: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "saved": False
        }

@app.post("/unsave")
async def unsave_product(request: dict):
    """
    Remove a product from saved_products table.
    """
    try:
        # Extract product_id from request body
        product_id = request.get("product_id")
        if not product_id:
            return {
                "success": False,
                "message": "product_id is required",
                "deleted_count": 0
            }
        
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Delete the product from saved_products table
        cur.execute("DELETE FROM saved_products WHERE product_id = %s", (product_id,))
        deleted_count = cur.rowcount
        
        cur.close()
        cn.close()
        
        if deleted_count > 0:
            return {
                "success": True,
                "message": f"Product {product_id} removed from saved list",
                "deleted_count": deleted_count
            }
        else:
            return {
                "success": False,
                "message": f"Product {product_id} not found in saved list",
                "deleted_count": 0
            }
        
    except mysql.connector.Error as e:
        print(f"Database error in unsave: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "deleted_count": 0
        }
    except Exception as e:
        print(f"Unexpected error in unsave: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "deleted_count": 0
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
