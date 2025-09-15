from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import mysql.connector
import os
import json
import logging
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# AliExpress API Configuration
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

# ─────────────────── AliExpress Client (HMAC-SHA256 /sync) ───────────────────
class AliClient:
    """
    Client for AliExpress OpenService /sync gateway (api-sg.aliexpress.com/sync)
    using HMAC-SHA256 signatures.
    """

    def __init__(self, app_key: str, app_secret: str, tracking_id: str,
                 base: str = "https://api-sg.aliexpress.com/sync") -> None:
        if not app_key or not app_secret:
            raise RuntimeError("APP_KEY/APP_SECRET are required.")
        self.app_key = app_key
        self.app_secret = app_secret.encode("utf-8")
        self.tracking_id = tracking_id
        self.base = base

    @staticmethod
    def _ts_ms() -> str:
        return str(int(time.time() * 1000))

    @staticmethod
    def _sorted_plain(params: Dict[str, Any]) -> bytes:
        items = sorted((k, v) for k, v in params.items() if v is not None)
        plain = "&".join(f"{k}={v}" for k, v in items)
        return plain.encode("utf-8")

    def _sign_sha256(self, params: Dict[str, Any]) -> str:
        # Remove sign parameter if it exists
        params_copy = {k: v for k, v in params.items() if k != "sign"}
        plain = self._sorted_plain(params_copy)
        return hmac.new(self.app_secret, plain, hashlib.sha256).hexdigest().upper()

    def call(self, method: str, **service_params) -> Dict[str, Any]:
        base_params = {
            "method": method,
            "app_key": self.app_key,
            "sign_method": "sha256",
            "timestamp": self._ts_ms(),
            "tracking_id": self.tracking_id,
        }
        params = {**base_params, **{k: v for k, v in service_params.items() if v is not None}}
        params["sign"] = self._sign_sha256(params)

        r = requests.get(self.base, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

# Initialize AliExpress client
ali_client: Optional[AliClient] = None
if APP_KEY and APP_SECRET:
    try:
        ali_client = AliClient(APP_KEY, APP_SECRET, TRACKING_ID)
    except Exception as e:
        logger.error(f"Failed to initialize AliExpress client: {e}")
        ali_client = None

# ─────────────────── Helpers ───────────────────
def _normalize_items(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize various AliExpress response shapes into a flat list of product dicts.
    """
    # response may be wrapped like "..._response" -> resp_result -> result -> products/list/items
    resp = next((raw.get(k) for k in raw.keys() if k.endswith("_response")), raw) or {}
    resp_result = resp.get("resp_result") or resp.get("result") or {}
    result = resp_result.get("result") or {}
    items = (
        result.get("products")
        or result.get("items")
        or result.get("list")
        or result.get("result")
        or raw.get("items")
        or []
    )
    if isinstance(items, dict):
        # sometimes nested like {"items":[...]} again
        for key in ("items", "list", "products", "data"):
            if isinstance(items.get(key), list):
                items = items[key]
                break

    out: List[Dict[str, Any]] = []
    for it in items or []:
        sale = it.get("sale_price")
        orig = it.get("original_price")
        curr = it.get("currency") or (sale.get("currency") if isinstance(sale, dict) else None) or "USD"
        sale_val = sale.get("value") if isinstance(sale, dict) else sale
        orig_val = orig.get("value") if isinstance(orig, dict) else orig

        out.append({
            "product_id": it.get("product_id") or it.get("item_id") or it.get("id"),
            "product_title": it.get("product_title") or it.get("title"),
            "product_main_image_url": it.get("product_main_image_url") or it.get("main_image") or it.get("image_url"),
            "product_video_url": it.get("product_video_url") or it.get("video_url"),
            "sale_price": sale_val,
            "sale_price_currency": curr,
            "original_price": orig_val,
            "original_price_currency": curr,
            "lastest_volume": it.get("lastest_volume") or it.get("volume") or it.get("sales"),
            "rating_weighted": it.get("rating_weighted") or it.get("rating") or it.get("score"),
            "first_level_category_id": it.get("first_level_category_id") or it.get("category_id"),
            "promotion_link": it.get("promotion_link") or it.get("target_url"),
            # New fields from AliExpress API
            "product_url": it.get("product_detail_url"),
            "shop_url": it.get("shop_url"),
            "shop_title": it.get("shop_name"),
            "discount_percentage": it.get("discount"),
            "commission_rate": it.get("hot_product_commission_rate") or it.get("commission_rate"),
            "commission_value": it.get("commission_value"),
            "product_detail_url": it.get("product_detail_url"),
            "product_sku": it.get("sku_id"),
            "product_brand": it.get("brand"),
            "product_condition": it.get("condition"),
            "product_warranty": it.get("warranty"),
            "product_shipping_info": it.get("shipping_info"),
            "product_return_policy": it.get("return_policy"),
            "images_extra": it.get("product_small_image_urls", {}).get("string", []) if it.get("product_small_image_urls") else [],
        })
    return out

# Database Configuration
DB_CFG = dict(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "alibee_affiliate"),
    port=int(os.getenv("DB_PORT", "3306")),
    autocommit=True,
    charset='utf8mb4',
    use_unicode=True
)

# Create FastAPI app
app = FastAPI(
    title="Alibee Affiliate API",
    description="Production API for Alibee Affiliate System",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG", "False").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("DEBUG", "False").lower() == "true" else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class Price(BaseModel):
    value: float
    currency: str

class SaveProductRequest(BaseModel):
    product_id: str
    product_title: str
    product_main_image_url: str
    product_video_url: Optional[str] = None
    product_description: Optional[str] = None
    images_extra: Optional[List[str]] = []
    sale_price: float
    sale_price_currency: str
    original_price: Optional[float] = None
    original_price_currency: Optional[str] = None
    promotion_link: str
    rating_weighted: Optional[float] = None
    lastest_volume: Optional[int] = None

class UnsaveRequest(BaseModel):
    product_id: str

# Database connection helper
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CFG)
        return connection
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tables exist, if not create them
        try:
            cursor.execute("SELECT COUNT(*) FROM saved_products")
            count = cursor.fetchone()[0]
        except mysql.connector.Error as e:
            if e.errno == 1146:  # Table doesn't exist
                # Create tables if they don't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS saved_products (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_id VARCHAR(255) NOT NULL,
                        title TEXT,
                        image_main TEXT,
                        video_url TEXT,
                        sale_price DECIMAL(10,2),
                        sale_price_currency VARCHAR(10),
                        original_price DECIMAL(10,2),
                        original_price_currency VARCHAR(10),
                        lastest_volume INT,
                        rating_weighted DECIMAL(3,2),
                        category_id VARCHAR(255),
                        promotion_link TEXT,
                        product_url TEXT,
                        shop_url TEXT,
                        shop_title VARCHAR(500),
                        discount_percentage DECIMAL(5,2),
                        commission_rate DECIMAL(5,2),
                        commission_value DECIMAL(10,2),
                        images_extra JSON,
                        product_detail_url TEXT,
                        product_sku VARCHAR(255),
                        product_brand VARCHAR(255),
                        product_condition VARCHAR(50),
                        product_warranty VARCHAR(255),
                        product_shipping_info TEXT,
                        product_return_policy TEXT,
                        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        
                        INDEX idx_product_id (product_id),
                        INDEX idx_saved_at (saved_at)
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        query VARCHAR(255) NOT NULL,
                        results_count INT DEFAULT 0,
                        user_ip VARCHAR(45),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        INDEX idx_query (query),
                        INDEX idx_created_at (created_at)
                    )
                """)
                
                conn.commit()
                count = 0
            else:
                raise e
        
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "aliexpress_api": "configured" if ali_client else "not_configured",
            "saved_products_count": count,
            "app_key": "set" if APP_KEY else "not_set",
            "app_secret": "set" if APP_SECRET else "not_set",
            "tracking_id": "set" if TRACKING_ID else "not_set"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "aliexpress_api": "not_configured",
            "error": str(e)
        }

# Stats endpoint
@app.get("/stats")
async def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get saved products count
        cursor.execute("SELECT COUNT(*) FROM saved_products")
        saved_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "totalProducts": 0,  # This would come from AliExpress API
            "savedProducts": saved_count,
            "totalSearches": 0,  # This could be tracked in a separate table
            "activeUsers": 0     # This could be tracked in a separate table
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")

# Search endpoint with AliExpress API
@app.get("/search")
async def search_products(
    q: Optional[str] = Query(None, description="Search query"),
    sort: str = Query("volume_desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size")
):
    try:
        if not ali_client:
            logger.warning("AliExpress API not configured, returning mock data")
            return generate_mock_data(page, pageSize)
        
        # Use AliExpress API with MD5 signature method (working solution)
        import hashlib
        import time
        
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
            'target_currency': 'USD',
            'trackingId': TRACKING_ID
        }
        
        # Add search parameters
        if q:
            api_params['keywords'] = q
        else:
            # If no search query, get hot products
            sys_params['method'] = 'aliexpress.affiliate.hotproduct.query'
        
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
        elif 'aliexpress_affiliate_hotproduct_query_response' in raw:
            resp = raw['aliexpress_affiliate_hotproduct_query_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    items = result['products']['product']
                    if not isinstance(items, list):
                        items = [items]
        
        # Normalize items for consistent format
        normalized_items = _normalize_items({'items': items})
        
        # If no real products found, fallback to mock data
        if not normalized_items:
            logger.warning("No products found from AliExpress API, returning mock data")
            return generate_mock_data(page, pageSize)
        
        # Check which products are saved
        if normalized_items:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Get product IDs from the items
                product_ids = [str(item.get('product_id', '')) for item in normalized_items if item.get('product_id')]
                
                if product_ids:
                    # Create placeholders for the IN clause
                    placeholders = ','.join(['%s'] * len(product_ids))
                    
                    # Query saved_products table to get saved_at timestamps
                    cursor.execute(f"""
                        SELECT product_id, saved_at 
                        FROM saved_products 
                        WHERE product_id IN ({placeholders})
                    """, product_ids)
                    
                    saved_products = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # Add saved_at field to items
                    for item in normalized_items:
                        product_id = str(item.get('product_id', ''))
                        if product_id in saved_products:
                            item['saved_at'] = saved_products[product_id].isoformat() if saved_products[product_id] else None
                        else:
                            item['saved_at'] = None
                
                cursor.close()
                conn.close()
            except Exception as e:
                # If database check fails, just continue without saved_at info
                logger.warning(f"Could not check saved products: {e}")
                for item in normalized_items:
                    item['saved_at'] = None
        
        return {
            "items": normalized_items,
            "page": page,
            "pageSize": pageSize,
            "total": len(normalized_items),
            "hasMore": len(normalized_items) == pageSize,
            "method": "aliexpress_api",
            "source": "aliexpress"
        }
        
    except requests.HTTPError as rexc:
        text = getattr(rexc.response, "text", "")
        logger.error(f"AliExpress HTTP error: {rexc} {text}")
        # Fallback to mock data on API error
        return generate_mock_data(page, pageSize)
    except Exception as e:
        logger.error(f"Search error: {e}")
        # Fallback to mock data on any error
        return generate_mock_data(page, pageSize)

# Saved products endpoint
@app.get("/saved")
async def get_saved_products(
    sort: str = Query("saved_at_desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size")
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build sort clause
        sort_mapping = {
            "saved_at_desc": "saved_at DESC",
            "saved_at_asc": "saved_at ASC",
            "price_desc": "sale_price DESC",
            "price_asc": "sale_price ASC",
            "rating_desc": "rating_weighted DESC",
            "volume_desc": "lastest_volume DESC"
        }
        sort_clause = sort_mapping.get(sort, "saved_at DESC")
        
        # Calculate offset
        offset = (page - 1) * pageSize
        
        # Query saved products
        query = f"""
        SELECT id, product_id, product_title, product_main_image_url, product_video_url,
               product_description, images_extra, sale_price, sale_price_currency,
               original_price, original_price_currency, promotion_link,
               rating_weighted, lastest_volume, saved_at, fetched_at
        FROM saved_products
        ORDER BY {sort_clause}
        LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, (pageSize, offset))
        rows = cursor.fetchall()
        
        # Convert to response format
        items = []
        for row in rows:
            item = {
                "product_id": row[1],
                "product_title": row[2],
                "product_main_image_url": row[3],
                "product_video_url": row[4],
                "product_description": row[5],
                "images_extra": json.loads(row[6]) if row[6] else [],
                "sale_price": float(row[7]) if row[7] else 0,
                "sale_price_currency": row[8],
                "original_price": float(row[9]) if row[9] else None,
                "original_price_currency": row[10],
                "promotion_link": row[11],
                "rating_weighted": float(row[12]) if row[12] else None,
                "lastest_volume": row[13],
                "saved_at": row[14].isoformat() if row[14] else None,
                "fetched_at": row[15].isoformat() if row[15] else None
            }
            items.append(item)
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM saved_products")
        total_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "items": items,
            "total": total_count,
            "page": page,
            "pageSize": pageSize,
            "hasMore": (page * pageSize) < total_count
        }
        
    except Exception as e:
        logger.error(f"Saved products error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch saved products")

# Save product endpoint
@app.post("/save")
async def save_product(request: SaveProductRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert or update product
        query = """
        INSERT INTO saved_products (
            product_id, product_title, product_main_image_url, product_video_url,
            product_description, images_extra, sale_price, sale_price_currency,
            original_price, original_price_currency, promotion_link,
            rating_weighted, lastest_volume, saved_at, fetched_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) ON DUPLICATE KEY UPDATE
            product_title = VALUES(product_title),
            product_main_image_url = VALUES(product_main_image_url),
            product_video_url = VALUES(product_video_url),
            product_description = VALUES(product_description),
            images_extra = VALUES(images_extra),
            sale_price = VALUES(sale_price),
            sale_price_currency = VALUES(sale_price_currency),
            original_price = VALUES(original_price),
            original_price_currency = VALUES(original_price_currency),
            promotion_link = VALUES(promotion_link),
            rating_weighted = VALUES(rating_weighted),
            lastest_volume = VALUES(lastest_volume),
            saved_at = NOW()
        """
        
        cursor.execute(query, (
            request.product_id,
            request.product_title,
            request.product_main_image_url,
            request.product_video_url,
            request.product_description,
            json.dumps(request.images_extra) if request.images_extra else None,
            request.sale_price,
            request.sale_price_currency,
            request.original_price,
            request.original_price_currency,
            request.promotion_link,
            request.rating_weighted,
            request.lastest_volume
        ))
        
        cursor.close()
        conn.close()
        
        return {"success": True, "message": "Product saved successfully"}
        
    except Exception as e:
        logger.error(f"Save product error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save product")

# Unsave product endpoint
@app.post("/unsave")
async def unsave_product(request: UnsaveRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM saved_products WHERE product_id = %s", (request.product_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        cursor.close()
        conn.close()
        
        return {"success": True, "message": "Product removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unsave product error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove product")

# Test AliExpress API endpoint
@app.get("/test-ali")
async def test_aliexpress():
    """Test AliExpress API with a simple search"""
    if not ali_client:
        return {
            "status": "error",
            "message": "AliExpress API not configured",
            "solution": "Please set APP_KEY and APP_SECRET in environment variables"
        }
    
    try:
        # Test with a simple search
        import hashlib
        import time
        
        base_url = 'https://api-sg.aliexpress.com/sync'
        
        sys_params = {
            'method': 'aliexpress.affiliate.product.query',
            'app_key': APP_KEY,
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'format': 'json',
            'v': '2.0'
        }
        
        api_params = {
            'page_no': 1,
            'page_size': 5,
            'target_language': 'EN',
            'target_currency': 'USD',
            'trackingId': TRACKING_ID,
            'keywords': 'phone'
        }
        
        all_params = {**sys_params, **api_params}
        clean_params = {k: v for k, v in all_params.items() if v is not None and v != ''}
        
        def create_md5_signature(params, secret):
            sorted_params = sorted(params.items())
            base_string = secret
            for key, value in sorted_params:
                base_string += key + str(value)
            base_string += secret
            return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()
        
        signature = create_md5_signature(clean_params, APP_SECRET)
        clean_params['sign'] = signature
        
        url = base_url + '?' + '&'.join([f"{k}={v}" for k, v in clean_params.items()])
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        raw = response.json()
        items = _normalize_items(raw)
        
        return {
            "status": "success",
            "message": "AliExpress API is working",
            "test_query": "phone",
            "results_count": len(items),
            "sample_products": items[:3] if items else [],
            "api_url": url,
            "response_keys": list(raw.keys()) if raw else []
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"AliExpress API error: {str(e)}",
            "solution": "Check APP_KEY, APP_SECRET, and network connection"
        }

# Demo endpoint
@app.get("/demo")
async def get_demo_products():
    """Get demo products for presentation"""
    sample_products = [
        {
            "product_id": "1005001234567890",
            "product_title": "Wireless Bluetooth Headphones - High Quality Sound",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567890.jpg",
            "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "sale_price": 25.99,
            "sale_price_currency": "USD",
            "original_price": 49.99,
            "original_price_currency": "USD",
            "lastest_volume": 1250,
            "rating_weighted": 4.8,
            "first_level_category_id": "100001",
            "promotion_link": "https://s.click.aliexpress.com/demo1",
            "commission_rate": 8.5,
            "discount": 48,
            "saved_at": None
        },
        {
            "product_id": "1005001234567891",
            "product_title": "Smart Watch with Heart Rate Monitor - Fitness Tracker",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567891.jpg",
            "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
            "sale_price": 89.99,
            "sale_price_currency": "USD",
            "original_price": 159.99,
            "original_price_currency": "USD",
            "lastest_volume": 890,
            "rating_weighted": 4.6,
            "first_level_category_id": "100002",
            "promotion_link": "https://s.click.aliexpress.com/demo2",
            "commission_rate": 12.0,
            "discount": 44,
            "saved_at": None
        },
        {
            "product_id": "1005001234567892",
            "product_title": "Portable Power Bank 20000mAh - Fast Charging",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567892.jpg",
            "product_video_url": "",
            "sale_price": 19.99,
            "sale_price_currency": "USD",
            "original_price": 35.99,
            "original_price_currency": "USD",
            "lastest_volume": 2100,
            "rating_weighted": 4.7,
            "first_level_category_id": "100003",
            "promotion_link": "https://s.click.aliexpress.com/demo3",
            "commission_rate": 6.5,
            "discount": 44,
            "saved_at": None
        }
    ]
    
    return {
        "items": sample_products,
        "page": 1,
        "pageSize": 3,
        "total": len(sample_products),
        "hasMore": False,
        "method": "demo",
        "source": "sample_data"
    }

# Mock data generator for development
def generate_mock_data(page: int, pageSize: int):
    items = []
    for i in range(pageSize):
        item = {
            "product_id": f"mock_{page}_{i}",
            "product_title": f"Mock Product {page}_{i}",
            "product_main_image_url": f"https://picsum.photos/400/400?random={page}_{i}",
            "product_video_url": f"https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "product_description": f"This is a mock product description for item {page}_{i}",
            "images_extra": [
                f"https://picsum.photos/400/400?random={page}_{i}_1",
                f"https://picsum.photos/400/400?random={page}_{i}_2"
            ],
            "sale_price": 29.99 + (i * 5),
            "sale_price_currency": "USD",
            "original_price": 39.99 + (i * 5),
            "original_price_currency": "USD",
            "promotion_link": f"https://example.com/product/{page}_{i}",
            "rating_weighted": 4.5 + (i * 0.1),
            "lastest_volume": 100 + (i * 50),
            "saved_at": None,
            "fetched_at": None
        }
        items.append(item)
    
    return {
        "items": items,
        "total": 1000,  # Mock total
        "page": page,
        "pageSize": pageSize,
        "hasMore": page < 50  # Mock hasMore
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

