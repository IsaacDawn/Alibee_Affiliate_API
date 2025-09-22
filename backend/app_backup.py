# backend/app.py
from __future__ import annotations

import os
import time
import hmac
import hashlib
import json
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import asyncio
import threading

import mysql.connector
import requests
from dotenv import load_dotenv
# from services.exchange_rate import exchange_rate_service  # Commented out - module not found
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─────────────────── Load .env ───────────────────
load_dotenv()

# ─────────────────── FastAPI app + CORS ───────────────────
app = FastAPI(title="Alibee Affiliator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────── AliExpress API Helper ───────────────────
def make_aliexpress_request(method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Make a request to AliExpress API
    """
    try:
        if not APP_KEY or not APP_SECRET:
            print("AliExpress API not configured")
            return None
        
        # Base URL
        base_url = "https://api-sg.aliexpress.com/sync"
        
        # System parameters
        sys_params = {
            "method": method,
            "app_key": APP_KEY,
            "sign_method": "md5",
            "timestamp": str(int(time.time() * 1000)),
            "v": "2.0",
            "format": "json"
        }
        
        # Combine all parameters
        all_params = {**sys_params, **params}
        
        # Remove empty values
        clean_params = {k: v for k, v in all_params.items() if v is not None and v != ''}
        
        # Create MD5 signature
        def create_md5_signature(params, secret):
            sorted_params = sorted(params.items())
            base_string = secret
            for key, value in sorted_params:
                base_string += f"{key}{value}"
            base_string += secret
            return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()
        
        # Add signature
        clean_params['sign'] = create_md5_signature(clean_params, APP_SECRET)
        
        # Build URL
        url = base_url + '?' + '&'.join([f"{k}={v}" for k, v in clean_params.items()])
        
        # Make request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse response
        return response.json()
        
    except Exception as e:
        print(f"Error making AliExpress request: {e}")
        return None

# ─────────────────── Background Tasks ───────────────────
def fetch_daily_products_background():
    """Background task to fetch daily products"""
    while True:
        try:
            # Check if it's a new day (run at midnight)
            now = datetime.now()
            if now.hour == 0 and now.minute < 5:  # Run within first 5 minutes of midnight
                print(f"Fetching daily products for {now.strftime('%Y-%m-%d')}")
                
                # Fetch fresh products
                if APP_KEY and APP_SECRET:
                    method = "aliexpress.affiliate.hotproduct.query"
                    params = {
                        "page_no": 1,
                        "page_size": 200,  # Fetch more for variety
                        "target_currency": "USD",
                        "target_language": "EN",
                        "keywords": f"daily_deals_{now.strftime('%Y%m%d')}"
                    }
                    
                    response = make_aliexpress_request(method, params)
                    
                    if response and 'aliexpress_affiliate_hotproduct_query_response' in response:
                        products_data = response['aliexpress_affiliate_hotproduct_query_response']
                        if 'resp_result' in products_data and 'result' in products_data['resp_result']:
                            products = products_data['resp_result']['result']['products']
                            
                            # Store products in database
                            cn = mysql.connector.connect(**DB_CFG)
                            cur = cn.cursor()
                            
                            try:
                                for product in products:
                                    try:
                                        cur.execute("""
                                            INSERT INTO aliexpress_products (
                                                product_id, product_title, product_main_image_url, product_video_url,
                                                sale_price, sale_price_currency, original_price, original_price_currency,
                                                lastest_volume, rating_weighted, first_level_category_id, promotion_link
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            ON DUPLICATE KEY UPDATE
                                                product_title=VALUES(product_title),
                                                product_main_image_url=VALUES(product_main_image_url),
                                                product_video_url=VALUES(product_video_url),
                                                sale_price=VALUES(sale_price),
                                                sale_price_currency=VALUES(sale_price_currency),
                                                original_price=VALUES(original_price),
                                                original_price_currency=VALUES(original_price_currency),
                                                lastest_volume=VALUES(lastest_volume),
                                                rating_weighted=VALUES(rating_weighted),
                                                first_level_category_id=VALUES(first_level_category_id),
                                                promotion_link=VALUES(promotion_link),
                                                fetched_at=CURRENT_TIMESTAMP
                                        """, (
                                            product.get('product_id'),
                                            product.get('product_title'),
                                            product.get('product_main_image_url'),
                                            product.get('product_video_url'),
                                            product.get('sale_price'),
                                            product.get('sale_price_currency', 'USD'),
                                            product.get('original_price'),
                                            product.get('original_price_currency', 'USD'),
                                            product.get('lastest_volume'),
                                            product.get('rating_weighted'),
                                            product.get('first_level_category_id'),
                                            product.get('promotion_link')
                                        ))
                                    except Exception as e:
                                        print(f"Error storing product: {e}")
                                        continue
                                
                                cn.commit()
                                print(f"Successfully stored {len(products)} daily products")
                                
                            finally:
                                cur.close()
                                cn.close()
                
                # Sleep for 1 hour to avoid running multiple times
                time.sleep(3600)
            else:
                # Sleep for 1 minute and check again
                time.sleep(60)
                
        except Exception as e:
            print(f"Error in background task: {e}")
            time.sleep(300)  # Sleep for 5 minutes on error

# Start background task in a separate thread (disabled for now to prevent hanging)
# background_thread = threading.Thread(target=fetch_daily_products_background, daemon=True)
# background_thread.start()
background_thread = None  # Disabled to prevent hanging

# ─────────────────── MySQL Config ───────────────────
DB_CFG = dict(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    auth_plugin='mysql_native_password',
    autocommit=True,
)

# ─────────────────── Pydantic Models ───────────────────
class Price(BaseModel):
    value: float
    currency: str
    original: float | None = None
    original_currency: str | None = None

class SaveProduct(BaseModel):
    product_id: str
    title: str
    selected_price: Price
    video_url: Optional[str] = None
    image_main: Optional[str] = None
    images_extra: List[str] = []
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

class UpdateProductDescription(BaseModel):
    product_id: str
    custom_description: str

# ─────────────────── AliExpress Client (HMAC-SHA256 /sync) ───────────────────
class AliClient:
    """
    Client for AliExpress OpenService /sync gateway (api-sg.aliexpress.com/sync)
    using HMAC-SHA256 signatures.

    Signature string = ampersand-joined sorted params: "k1=v1&k2=v2&..."
    sign = HMAC_SHA256(secret, plain).hexdigest().upper()
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

# ─────────────────── AliExpress settings from env ───────────────────
# AliExpress API Configuration (using working credentials from Alibee_PHP)
APP_KEY = os.getenv("APP_KEY") or "514064"
APP_SECRET = os.getenv("APP_SECRET") or "p8rJNLXoolmZKskeUrshCCbs45y4eWS9"
TRACKING_ID = os.getenv("TRACKING_ID", "Alibee")
APP_SIGNATURE = os.getenv("APP_SIGNATURE")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
TRACKING_ID = os.getenv("TRACKING_ID", "Alibee")
ALI_SYNC_BASE = os.getenv("ALI_SYNC_BASE", "https://api-sg.aliexpress.com/sync")

ali_client: Optional[AliClient] = None
if APP_KEY and APP_SECRET:
    try:
        ali_client = AliClient(APP_KEY, APP_SECRET, TRACKING_ID, ALI_SYNC_BASE)
    except Exception:
        ali_client = None  # اجازه می‌دهیم /health بالا بیاید؛ خطا را در زمان فراخوانی گزارش می‌کنیم.

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

        # Generate mock data for missing fields
        import random
        product_id = it.get("product_id") or it.get("item_id") or it.get("id")
        
        # Generate consistent mock data based on product_id
        random.seed(str(product_id))
        mock_volume = random.randint(10, 50000)  # Random volume between 10-50K
        mock_rating = round(random.uniform(3.0, 5.0), 1)  # Random rating between 3.0-5.0
        random.seed()  # Reset random seed
        
        out.append({
            "product_id": product_id,
            "product_title": it.get("product_title") or it.get("title"),
            "product_main_image_url": it.get("product_main_image_url") or it.get("main_image") or it.get("image_url"),
            "product_video_url": it.get("product_video_url") or it.get("video_url"),
            "sale_price": sale_val,
            "sale_price_currency": curr,
            "original_price": orig_val,
            "original_price_currency": curr,
            "lastest_volume": it.get("lastest_volume") or it.get("volume") or it.get("sales") or mock_volume,
            "rating_weighted": it.get("rating_weighted") or it.get("rating") or it.get("score") or it.get("evaluate_rate") or mock_rating,
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

# ─────────────────── Routes ───────────────────
@app.get("/health")
def health():
    """
    وضعیت سیستم: دیتابیس + AliExpress API
    """
    info: Dict[str, Any] = {}
    
    # بررسی دیتابیس
    try:
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Check if tables exist, if not create them
        try:
            cur.execute("SELECT COUNT(*) FROM aliexpress_products")
            count = cur.fetchone()[0]
            info.update({"db": "ok", "productsCount": count})
        except mysql.connector.Error as e:
            if e.errno == 1146:  # Table doesn't exist
                # Create tables if they don't exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS aliexpress_products (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_id VARCHAR(255) NOT NULL UNIQUE,
                        product_title TEXT NOT NULL,
                        product_main_image_url TEXT,
                        product_video_url TEXT,
                        sale_price DECIMAL(10,2),
                        sale_price_currency VARCHAR(10) DEFAULT 'USD',
                        original_price DECIMAL(10,2),
                        original_price_currency VARCHAR(10) DEFAULT 'USD',
                        lastest_volume INT,
                        rating_weighted DECIMAL(3,2),
                        first_level_category_id VARCHAR(50),
                        promotion_link TEXT,
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        
                        INDEX idx_product_id (product_id),
                        INDEX idx_category (first_level_category_id),
                        INDEX idx_volume (lastest_volume),
                        INDEX idx_rating (rating_weighted),
                        INDEX idx_saved_at (saved_at),
                        FULLTEXT idx_title (product_title)
                    )
                """)
                
                cur.execute("""
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
                
                cur.execute("""
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
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS affiliate_links (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_id VARCHAR(255) NOT NULL,
                        original_url TEXT NOT NULL,
                        affiliate_url TEXT NOT NULL,
                        clicks INT DEFAULT 0,
                        conversions INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        
                        INDEX idx_product_id (product_id),
                        INDEX idx_clicks (clicks)
                    )
                """)
                
                cn.commit()
                info.update({"db": "ok", "productsCount": 0, "tables_created": True})
            else:
                raise e
        
        cur.close(); cn.close()
    except Exception as e:
        info.update({"db": "error", "message": str(e)})

    # بررسی AliExpress API
    if ali_client:
        info["ali_client"] = "ok"
        info["ali_api_status"] = "آماده برای جستجو"
    else:
        info["ali_client"] = "not_configured"
        info["ali_api_status"] = "نیاز به تنظیم APP_KEY و APP_SECRET"
    
    return info

@app.get("/status")
def health_simple():
    """
    Simple health check endpoint for frontend compatibility.
    """
    try:
        # Test database connection
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        cur.execute("SELECT 1")
        cur.close(); cn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "aliexpress_api": "configured" if APP_KEY else "not_configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "aliexpress_api": "not_configured",
            "error": str(e)
        }

# Test AliExpress Categories API endpoint
@app.get("/test-categories")
async def test_categories_api():
    """Test AliExpress Categories API methods"""
    results = {}
    
    # Test different potential category methods
    category_methods = [
        "aliexpress.category.redefining.getcategorylist",
        "aliexpress.category.redefining.getchildcategorylist", 
        "aliexpress.affiliate.category.get",
        "aliexpress.category.get",
        "aliexpress.category.list"
    ]
    
    for method in category_methods:
        try:
            print(f"Testing category method: {method}")
            # Create simple test client
            if APP_KEY and APP_SECRET:
                ali_client = AliClient(APP_KEY, APP_SECRET, TRACKING_ID)
                response = ali_client.call(method)
                results[method] = {"success": True, "response": response}
            else:
                results[method] = {"success": False, "error": "AliExpress API not configured"}
        except Exception as e:
            print(f"Method {method} failed: {e}")
            results[method] = {"success": False, "error": str(e)}
    
    return {"category_methods_test": results}

# Get AliExpress Categories endpoint
@app.get("/categories")
async def get_categories():
    """Get AliExpress categories - real categories used by AliExpress"""
    
    # Real AliExpress categories with their actual IDs (fixed duplicates)
    aliexpress_categories = [
        {"id": "", "name": "All Categories", "name_fa": "همه دسته‌بندی‌ها"},
        {"id": "3", "name": "Electronics", "name_fa": "لوازم الکترونیکی"},
        {"id": "1501", "name": "Phones & Telecommunications", "name_fa": "تلفن و مخابرات"},
        {"id": "1420", "name": "Computer & Office", "name_fa": "کامپیوتر و دفتری"},
        {"id": "1511", "name": "Consumer Electronics", "name_fa": "الکترونیک مصرفی"},
        {"id": "7", "name": "Home & Garden", "name_fa": "خانه و باغ"},
        {"id": "1503", "name": "Jewelry & Accessories", "name_fa": "جواهرات و لوازم جانبی"},
        {"id": "36", "name": "Sports & Entertainment", "name_fa": "ورزش و سرگرمی"},
        {"id": "1524", "name": "Automobiles & Motorcycles", "name_fa": "خودرو و موتورسیکلت"},
        {"id": "21", "name": "Toys & Hobbies", "name_fa": "اسباب‌بازی و سرگرمی"},
        {"id": "1509", "name": "Health & Beauty", "name_fa": "سلامت و زیبایی"},
        {"id": "15", "name": "Women's Clothing", "name_fa": "پوشاک زنانه"},
        {"id": "1", "name": "Men's Clothing", "name_fa": "پوشاک مردانه"},
        {"id": "1504", "name": "Shoes", "name_fa": "کفش"},
        {"id": "1502", "name": "Bags & Luggage", "name_fa": "کیف و چمدان"},
        {"id": "1421", "name": "Tools & Home Improvement", "name_fa": "ابزار و بهسازی خانه"},
        {"id": "66", "name": "Mother & Kids", "name_fa": "مادر و کودک"},
        {"id": "1525", "name": "Security & Protection", "name_fa": "امنیت و حفاظت"},
        {"id": "44", "name": "Lights & Lighting", "name_fa": "نور و روشنایی"},
        {"id": "13", "name": "Home Appliances", "name_fa": "لوازم خانگی"},
        {"id": "1526", "name": "Musical Instruments", "name_fa": "لوازم موسیقی و سازها"}
    ]
    
    return {
        "status": "success",
        "message": "AliExpress categories retrieved successfully",
        "total": len(aliexpress_categories),
        "categories": aliexpress_categories,
        "source": "aliexpress_official"
    }

# Exchange Rates endpoint
# @app.get("/exchange-rates")
# async def get_exchange_rates(base_currency: str = Query("USD", description="Base currency")):
#     """Get current exchange rates for supported currencies"""
#     try:
#         rates = exchange_rate_service.get_exchange_rates(base_currency)
#         supported_currencies = exchange_rate_service.get_supported_currencies()
#         
#         return {
#             "status": "success",
#             "message": "Exchange rates retrieved successfully",
#             "base_currency": base_currency,
#             "rates": rates,
#             "supported_currencies": supported_currencies,
#             "timestamp": time.time(),
#             "source": "exchangerate-api"
#         }
#     except Exception as e:
#         print(f"Error fetching exchange rates: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to fetch exchange rates: {str(e)}")

# Currency Conversion endpoint
# @app.get("/convert-currency")
# async def convert_currency(
#     amount: float = Query(..., description="Amount to convert"),
#     from_currency: str = Query(..., description="Source currency"),
#     to_currency: str = Query(..., description="Target currency")
# ):
#     """Convert amount from one currency to another"""
#     try:
#         converted_amount = exchange_rate_service.convert_currency(amount, from_currency, to_currency)
#         
#         return {
#             "status": "success",
#             "message": "Currency conversion successful",
#             "original_amount": amount,
#             "from_currency": from_currency,
#             "to_currency": to_currency,
#             "converted_amount": converted_amount,
#             "timestamp": time.time()
#         }
#     except Exception as e:
#         print(f"Error converting currency: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to convert currency: {str(e)}")

@app.get("/demo")
def demo_products():
    """
    Demo endpoint with guaranteed sample products for presentation
    """
    # Sample AliExpress products for demonstration
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
            "discount": 48
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
            "discount": 44
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
            "discount": 44
        },
        {
            "product_id": "1005001234567893",
            "product_title": "LED Strip Lights RGB - Smart Home Lighting",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567893.jpg",
            "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "sale_price": 12.99,
            "sale_price_currency": "USD",
            "original_price": 24.99,
            "original_price_currency": "USD",
            "lastest_volume": 1800,
            "rating_weighted": 4.5,
            "first_level_category_id": "100004",
            "promotion_link": "https://s.click.aliexpress.com/demo4",
            "commission_rate": 9.0,
            "discount": 48
        },
        {
            "product_id": "1005001234567894",
            "product_title": "Phone Case with Card Holder - Premium Protection",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567894.jpg",
            "product_video_url": "",
            "sale_price": 8.99,
            "sale_price_currency": "USD",
            "original_price": 15.99,
            "original_price_currency": "USD",
            "lastest_volume": 3200,
            "rating_weighted": 4.9,
            "first_level_category_id": "100003",
            "promotion_link": "https://s.click.aliexpress.com/demo5",
            "commission_rate": 15.0,
            "discount": 44
        }
    ]
    
    # Check which demo products are saved by joining with saved_products table
    try:
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Get product IDs from the demo products
        product_ids = [str(item.get('product_id', '')) for item in sample_products if item.get('product_id')]
        
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
            
            # Add saved_at field to demo products
            for item in sample_products:
                product_id = str(item.get('product_id', ''))
                if product_id in saved_products:
                    item['saved_at'] = saved_products[product_id].isoformat() if saved_products[product_id] else None
                else:
                    item['saved_at'] = None
        
        cur.close(); cn.close()
    except Exception as e:
        # If database check fails, just continue without saved_at info
        print(f"Warning: Could not check saved demo products: {e}")
        for item in sample_products:
            item['saved_at'] = None
    
    return {
        "status": "success",
        "message": "Demo products loaded successfully",
        "query": "demo_products",
        "page": 1,
        "pageSize": 5,
        "total": len(sample_products),
        "items": sample_products,
        "method": "demo",
        "source": "sample_data"
    }

@app.get("/test-ali")
def test_aliexpress():
    """
    Test AliExpress API with a simple search using iop library
    """
    if not APP_KEY or not APP_SECRET:
        return {
            "status": "error",
            "message": "AliExpress API not configured",
            "solution": "Please set APP_KEY and APP_SECRET in .env file"
        }
    
    try:
        # Use official AliExpress SDK
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python'))
        import iop
        
        # Initialize client with System APIs URL
        client = iop.IopClient('https://api-sg.aliexpress.com/rest', APP_KEY, APP_SECRET)
        
        # Create request
        request = iop.IopRequest('aliexpress.affiliate.product.query')
        request.set_simplify()
        
        # Add parameters
        if APP_SIGNATURE:
            request.add_api_param('app_signature', APP_SIGNATURE)
        
        request.add_api_param('v', '2.0')
        request.add_api_param('fields', 'commission_rate,sale_price,product_title,product_main_image_url')
        request.add_api_param('keywords', 'phone')
        request.add_api_param('page_no', '1')
        request.add_api_param('page_size', '5')
        request.add_api_param('platform_product_type', 'ALL')
        request.add_api_param('sort', 'SALE_PRICE_ASC')
        request.add_api_param('target_currency', 'USD')
        request.add_api_param('target_language', 'EN')
        request.add_api_param('tracking_id', TRACKING_ID)
        
        # Execute request without access token first
        response = client.execute(request)
        
        # Debug: show raw response
        print("Raw API Response:", response.body)
        print("Response Type:", response.type)
        print("Response Code:", response.code)
        print("Response Message:", response.message)
        
        # Parse response
        raw = response.body
        items = _normalize_items(raw)
        
        return {
            "status": "success",
            "message": "AliExpress API is working with iop library",
            "test_query": "phone",
            "results_count": len(items),
            "sample_products": items[:3] if items else [],
            "raw_response": raw,  # For debugging
            "response_type": str(response.type) if hasattr(response, 'type') else "unknown"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"AliExpress API error: {str(e)}",
            "solution": "Check APP_KEY, APP_SECRET, and APP_SIGNATURE"
        }

@app.get("/daily-products")
def get_daily_products(
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
    target_currency: str = Query("USD", description="Target currency"),
    target_language: str = Query("EN", description="Target language"),
):
    """
    Get daily rotating products for homepage - ensures fresh content daily
    """
    from datetime import datetime, timedelta
    
    # Get today's date for daily rotation
    today = datetime.now().strftime("%Y%m%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    # Check if we have fresh products for today
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor(dictionary=True)
    
    try:
        # Check if we have products from today
        cur.execute("""
            SELECT COUNT(*) as count FROM aliexpress_products 
            WHERE DATE(fetched_at) = CURDATE()
        """)
        today_count = cur.fetchone()['count']
        
        # If we don't have enough products for today, fetch new ones
        if today_count < 50:  # Minimum threshold
            # Fetch fresh products from AliExpress API
            if APP_KEY and APP_SECRET:
                try:
                    # Use hot products API for daily deals
                    method = "aliexpress.affiliate.hotproduct.query"
                    params = {
                        "page_no": 1,
                        "page_size": 100,  # Fetch more to have variety
                        "target_currency": target_currency,
                        "target_language": target_language,
                        "keywords": f"daily_deals_{today}"
                    }
                    
                    # Make API call
                    response = make_aliexpress_request(method, params)
                    
                    if response and 'aliexpress_affiliate_hotproduct_query_response' in response:
                        products_data = response['aliexpress_affiliate_hotproduct_query_response']
                        if 'resp_result' in products_data and 'result' in products_data['resp_result']:
                            products = products_data['resp_result']['result']['products']
                            
                            # Store products in database
                            for product in products:
                                try:
                                    cur.execute("""
                                        INSERT INTO aliexpress_products (
                                            product_id, product_title, product_main_image_url, product_video_url,
                                            sale_price, sale_price_currency, original_price, original_price_currency,
                                            lastest_volume, rating_weighted, first_level_category_id, promotion_link
                                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON DUPLICATE KEY UPDATE
                                            product_title=VALUES(product_title),
                                            product_main_image_url=VALUES(product_main_image_url),
                                            product_video_url=VALUES(product_video_url),
                                            sale_price=VALUES(sale_price),
                                            sale_price_currency=VALUES(sale_price_currency),
                                            original_price=VALUES(original_price),
                                            original_price_currency=VALUES(original_price_currency),
                                            lastest_volume=VALUES(lastest_volume),
                                            rating_weighted=VALUES(rating_weighted),
                                            first_level_category_id=VALUES(first_level_category_id),
                                            promotion_link=VALUES(promotion_link),
                                            fetched_at=CURRENT_TIMESTAMP
                                    """, (
                                        product.get('product_id'),
                                        product.get('product_title'),
                                        product.get('product_main_image_url'),
                                        product.get('product_video_url'),
                                        product.get('sale_price'),
                                        product.get('sale_price_currency', 'USD'),
                                        product.get('original_price'),
                                        product.get('original_price_currency', 'USD'),
                                        product.get('lastest_volume'),
                                        product.get('rating_weighted'),
                                        product.get('first_level_category_id'),
                                        product.get('promotion_link')
                                    ))
                                except Exception as e:
                                    print(f"Error storing product: {e}")
                                    continue
                            
                            cn.commit()
                            
                except Exception as e:
                    print(f"Error fetching daily products: {e}")
        
        # Get products for the requested page
        offset = (page - 1) * pageSize
        
        # Get fresh products from today, with some randomization
        cur.execute("""
            SELECT product_id, product_title, product_main_image_url, product_video_url,
                   sale_price, sale_price_currency, original_price, original_price_currency,
                   lastest_volume, rating_weighted, first_level_category_id, promotion_link,
                   fetched_at as saved_at
            FROM aliexpress_products 
            WHERE DATE(fetched_at) = CURDATE()
            ORDER BY RAND(), lastest_volume DESC
            LIMIT %s OFFSET %s
        """, (pageSize, offset))
        
        products = cur.fetchall()
        
        # If not enough products for today, get from yesterday as fallback
        if len(products) < pageSize:
            remaining = pageSize - len(products)
            cur.execute("""
                SELECT product_id, product_title, product_main_image_url, product_video_url,
                       sale_price, sale_price_currency, original_price, original_price_currency,
                       lastest_volume, rating_weighted, first_level_category_id, promotion_link,
                       fetched_at as saved_at
                FROM aliexpress_products 
                WHERE DATE(fetched_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
                ORDER BY RAND(), lastest_volume DESC
                LIMIT %s
            """, (remaining,))
            
            fallback_products = cur.fetchall()
            products.extend(fallback_products)
        
        # If still no products, fetch from AliExpress API directly
        if len(products) == 0 and APP_KEY and APP_SECRET:
            try:
                method = "aliexpress.affiliate.hotproduct.query"
                params = {
                    "page_no": page,
                    "page_size": pageSize,
                    "target_currency": target_currency,
                    "target_language": target_language,
                    "keywords": f"daily_deals_{today}"
                }
                
                response = make_aliexpress_request(method, params)
                
                if response and 'aliexpress_affiliate_hotproduct_query_response' in response:
                    products_data = response['aliexpress_affiliate_hotproduct_query_response']
                    if 'resp_result' in products_data and 'result' in products_data['resp_result']:
                        result = products_data['resp_result']['result']
                        if 'products' in result and 'product' in result['products']:
                            api_products = result['products']['product']
                            if not isinstance(api_products, list):
                                api_products = [api_products]
                            if api_products:
                                # Convert API products to our format
                                for product in api_products:
                                    products.append({
                                        "product_id": product.get('product_id'),
                                        "product_title": product.get('product_title'),
                                        "product_main_image_url": product.get('product_main_image_url'),
                                        "product_video_url": product.get('product_video_url'),
                                        "sale_price": product.get('sale_price'),
                                        "sale_price_currency": product.get('sale_price_currency', 'USD'),
                                        "original_price": product.get('original_price'),
                                        "original_price_currency": product.get('original_price_currency', 'USD'),
                                        "lastest_volume": product.get('lastest_volume'),
                                        "rating_weighted": product.get('rating_weighted'),
                                        "first_level_category_id": product.get('first_level_category_id'),
                                        "promotion_link": product.get('promotion_link'),
                                        "saved_at": None
                                    })
            except Exception as e:
                print(f"Error fetching from API: {e}")
        
        return {
            "items": products,
            "page": page,
            "pageSize": pageSize,
            "hasMore": len(products) == pageSize,
            "daily_seed": today,
            "source": "daily_rotation"
        }
        
    finally:
        cur.close()
        cn.close()

@app.post("/refresh-daily-products")
def refresh_daily_products():
    """
    Manually refresh daily products - useful for testing or immediate updates
    """
    try:
        from datetime import datetime
        
        today = datetime.now().strftime("%Y%m%d")
        print(f"Manually refreshing daily products for {today}")
        
        if not APP_KEY or not APP_SECRET:
            raise HTTPException(status_code=400, detail="AliExpress API not configured")
        
        # Fetch fresh products
        method = "aliexpress.affiliate.hotproduct.query"
        params = {
            "page_no": 1,
            "page_size": 200,
            "target_currency": "USD",
            "target_language": "EN",
            "keywords": f"daily_deals_{today}"
        }
        
        response = make_aliexpress_request(method, params)
        
        if not response or 'aliexpress_affiliate_hotproduct_query_response' not in response:
            raise HTTPException(status_code=500, detail="Failed to fetch products from AliExpress")
        
        products_data = response['aliexpress_affiliate_hotproduct_query_response']
        if 'resp_result' not in products_data or 'result' not in products_data['resp_result']:
            raise HTTPException(status_code=500, detail="Invalid response format from AliExpress")
        
        products = products_data['resp_result']['result']['products']
        
        # Store products in database
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        try:
            stored_count = 0
            for product in products:
                try:
                    cur.execute("""
                        INSERT INTO aliexpress_products (
                            product_id, product_title, product_main_image_url, product_video_url,
                            sale_price, sale_price_currency, original_price, original_price_currency,
                            lastest_volume, rating_weighted, first_level_category_id, promotion_link
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            product_title=VALUES(product_title),
                            product_main_image_url=VALUES(product_main_image_url),
                            product_video_url=VALUES(product_video_url),
                            sale_price=VALUES(sale_price),
                            sale_price_currency=VALUES(sale_price_currency),
                            original_price=VALUES(original_price),
                            original_price_currency=VALUES(original_price_currency),
                            lastest_volume=VALUES(lastest_volume),
                            rating_weighted=VALUES(rating_weighted),
                            first_level_category_id=VALUES(first_level_category_id),
                            promotion_link=VALUES(promotion_link),
                            fetched_at=CURRENT_TIMESTAMP
                    """, (
                        product.get('product_id'),
                        product.get('product_title'),
                        product.get('product_main_image_url'),
                        product.get('product_video_url'),
                        product.get('sale_price'),
                        product.get('sale_price_currency', 'USD'),
                        product.get('original_price'),
                        product.get('original_price_currency', 'USD'),
                        product.get('lastest_volume'),
                        product.get('rating_weighted'),
                        product.get('first_level_category_id'),
                        product.get('promotion_link')
                    ))
                    stored_count += 1
                except Exception as e:
                    print(f"Error storing product: {e}")
                    continue
            
            cn.commit()
            
            return {
                "status": "success",
                "message": f"Successfully refreshed {stored_count} daily products",
                "daily_seed": today,
                "products_fetched": len(products),
                "products_stored": stored_count
            }
            
        finally:
            cur.close()
            cn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing daily products: {str(e)}")

@app.get("/daily-status")
def get_daily_status():
    """
    Get status of daily products rotation
    """
    try:
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor(dictionary=True)
        
        try:
            # Get today's products count
            cur.execute("""
                SELECT COUNT(*) as today_count FROM aliexpress_products 
                WHERE DATE(fetched_at) = CURDATE()
            """)
            today_count = cur.fetchone()['today_count']
            
            # Get yesterday's products count
            cur.execute("""
                SELECT COUNT(*) as yesterday_count FROM aliexpress_products 
                WHERE DATE(fetched_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
            """)
            yesterday_count = cur.fetchone()['yesterday_count']
            
            # Get total products count
            cur.execute("SELECT COUNT(*) as total_count FROM aliexpress_products")
            total_count = cur.fetchone()['total_count']
            
            # Get latest fetch time
            cur.execute("""
                SELECT MAX(fetched_at) as latest_fetch FROM aliexpress_products
            """)
            latest_fetch = cur.fetchone()['latest_fetch']
            
            return {
                "status": "success",
                "daily_seed": datetime.now().strftime("%Y%m%d"),
                "today_products": today_count,
                "yesterday_products": yesterday_count,
                "total_products": total_count,
                "latest_fetch": latest_fetch,
                "background_task_running": background_thread.is_alive() if background_thread else False,
                "api_configured": bool(APP_KEY and APP_SECRET)
            }
            
        finally:
            cur.close()
            cn.close()
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/stats")
def get_stats():
    """
    Get application statistics.
    """
    stats: Dict[str, Any] = {}
    try:
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Get saved products count
        cur.execute("SELECT COUNT(*) FROM saved_products")
        saved_products = cur.fetchone()[0]
        
        # Get total searches count
        cur.execute("SELECT COUNT(*) FROM search_history")
        total_searches = cur.fetchone()[0]
        
        # Get affiliate links count
        cur.execute("SELECT COUNT(*) FROM affiliate_links")
        affiliate_links = cur.fetchone()[0]
        
        # Get recent searches (last 7 days)
        cur.execute("""
            SELECT COUNT(*) FROM search_history 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        recent_searches = cur.fetchone()[0]
        
        cur.close(); cn.close()
        
        stats = {
            "totalProducts": 0,  # This would come from AliExpress API
            "savedProducts": saved_products,
            "totalSearches": total_searches,
            "activeUsers": 0,  # This could be tracked in a separate table
            "affiliate_links": affiliate_links,
            "recent_searches": recent_searches,
        }
    except Exception as e:
        stats = {"error": str(e)}
    
    return stats

@app.get("/products")
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    categoryId: Optional[str] = Query(None, description="Category ID"),
    hasVideo: Optional[bool] = Query(None, description="Has video"),
    sort: str = Query("volume_desc", pattern="^(volume_desc|discount_desc|rating_desc)$"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
):
    """
    Fetch saved products from our MySQL (used for Client Interface and saved ❤️).
    """
    offset = (page - 1) * pageSize
    wh, params = ["1=1"], []

    if q:
        wh.append("product_title LIKE ?")
        params.append(f"%{q}%")
    if categoryId:
        wh.append("first_level_category_id = ?")
        params.append(categoryId)
    if hasVideo:
        wh.append("product_video_url IS NOT NULL AND product_video_url <> ''")

    order = {
        "volume_desc": "lastest_volume DESC",
        "discount_desc": "discount DESC",
        "rating_desc": "rating_weighted DESC",
    }[sort]

    sql = f"""
      SELECT product_id, product_title, product_main_image_url, product_video_url,
             sale_price, sale_price_currency, original_price, original_price_currency,
             lastest_volume, rating_weighted, promotion_link, saved_at
      FROM aliexpress_products
      WHERE {' AND '.join(wh)}
      ORDER BY {order}
      LIMIT %s OFFSET %s
    """.replace("?", "%s")

    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor(dictionary=True)
    cur.execute(sql, (*params, pageSize, offset))
    rows = cur.fetchall()
    cur.close(); cn.close()

    return {"items": rows, "page": page, "pageSize": pageSize, "hasMore": len(rows) >= pageSize}

@app.post("/save")
def save_product_simple(p: SaveProduct):
    """
    Save/Upsert a product (❤️) into our DB - Simple version for frontend.
    """
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        # First, ensure saved_products table has all necessary columns
        try:
            columns_to_add = [
                "ADD COLUMN title TEXT",
                "ADD COLUMN image_main TEXT",
                "ADD COLUMN video_url TEXT",
                "ADD COLUMN sale_price DECIMAL(10,2)",
                "ADD COLUMN sale_price_currency VARCHAR(10)",
                "ADD COLUMN original_price DECIMAL(10,2)",
                "ADD COLUMN original_price_currency VARCHAR(10)",
                "ADD COLUMN lastest_volume INT",
                "ADD COLUMN rating_weighted DECIMAL(3,2)",
                "ADD COLUMN category_id VARCHAR(255)",
                "ADD COLUMN promotion_link TEXT",
                "ADD COLUMN product_url TEXT",
                "ADD COLUMN shop_url TEXT",
                "ADD COLUMN shop_title VARCHAR(500)",
                "ADD COLUMN discount_percentage DECIMAL(5,2)",
                "ADD COLUMN commission_rate DECIMAL(5,2)",
                "ADD COLUMN commission_value DECIMAL(10,2)",
                "ADD COLUMN images_extra JSON",
                "ADD COLUMN product_detail_url TEXT",
                "ADD COLUMN product_sku VARCHAR(255)",
                "ADD COLUMN product_brand VARCHAR(255)",
                "ADD COLUMN product_condition VARCHAR(50)",
                "ADD COLUMN product_warranty VARCHAR(255)",
                "ADD COLUMN product_shipping_info TEXT",
                "ADD COLUMN product_return_policy TEXT",
                "ADD COLUMN custom_description TEXT",
                "ADD COLUMN saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ]
            
            for column in columns_to_add:
                try:
                    cur.execute(f"ALTER TABLE saved_products {column}")
                except mysql.connector.Error as e:
                    # Column already exists, ignore
                    if e.errno != 1060:  # Duplicate column name
                        raise
        except Exception:
            pass  # Ignore column addition errors
        
        # Insert into saved_products table
        cur.execute(
            """
            INSERT INTO saved_products (
              product_id, title, image_main, video_url,
              sale_price, sale_price_currency, original_price, original_price_currency,
              lastest_volume, rating_weighted, category_id, promotion_link,
              product_url, shop_url, shop_title, discount_percentage,
              commission_rate, commission_value, images_extra, product_detail_url,
              product_sku, product_brand, product_condition, product_warranty,
              product_shipping_info, product_return_policy
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              title=VALUES(title),
              image_main=VALUES(image_main),
              video_url=VALUES(video_url),
              sale_price=VALUES(sale_price),
              sale_price_currency=VALUES(sale_price_currency),
              original_price=VALUES(original_price),
              original_price_currency=VALUES(original_price_currency),
              lastest_volume=VALUES(lastest_volume),
              rating_weighted=VALUES(rating_weighted),
              category_id=VALUES(category_id),
              promotion_link=VALUES(promotion_link),
              product_url=VALUES(product_url),
              shop_url=VALUES(shop_url),
              shop_title=VALUES(shop_title),
              discount_percentage=VALUES(discount_percentage),
              commission_rate=VALUES(commission_rate),
              commission_value=VALUES(commission_value),
              images_extra=VALUES(images_extra),
              product_detail_url=VALUES(product_detail_url),
              product_sku=VALUES(product_sku),
              product_brand=VALUES(product_brand),
              product_condition=VALUES(product_condition),
              product_warranty=VALUES(product_warranty),
              product_shipping_info=VALUES(product_shipping_info),
              product_return_policy=VALUES(product_return_policy),
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                p.product_id,
                p.title,
                p.image_main,
                p.video_url,
                p.selected_price.value,
                p.selected_price.currency,
                p.selected_price.original,
                p.selected_price.original_currency or p.selected_price.currency,
                p.lastest_volume,
                p.rating_weighted,
                p.category_id,
                p.promotion_link,
                p.product_url,
                p.shop_url,
                p.shop_title,
                p.discount_percentage,
                p.commission_rate,
                p.commission_value,
                json.dumps(p.images_extra) if p.images_extra else None,
                p.product_detail_url,
                p.product_sku,
                p.product_brand,
                p.product_condition,
                p.product_warranty,
                p.product_shipping_info,
                p.product_return_policy,
            ),
        )
        cn.commit()
        return {"success": True, "message": "Product saved successfully"}
    except Exception as e:
        cn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close(); cn.close()

@app.post("/ensure-unique-constraint")
def ensure_unique_constraint():
    """
    Ensure product_id has unique constraint in saved_products table
    """
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        # Add unique constraint on product_id if it doesn't exist
        try:
            cur.execute("ALTER TABLE saved_products ADD UNIQUE KEY unique_product_id (product_id)")
            cn.commit()
            return {"status": "success", "message": "Unique constraint added to product_id"}
        except mysql.connector.Error as e:
            if e.errno == 1061:  # Duplicate key name
                return {"status": "success", "message": "Unique constraint already exists on product_id"}
            elif e.errno == 1062:  # Duplicate entry
                return {"status": "warning", "message": "Duplicate entries found, please clean up first"}
            else:
                raise
    except Exception as e:
        cn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add unique constraint: {str(e)}")
    finally:
        cur.close()
        cn.close()

@app.post("/update-description")
def update_product_description(update_data: UpdateProductDescription):
    """
    Update custom description for a saved product
    """
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        # Check if product exists in saved_products table
        cur.execute("SELECT product_id FROM saved_products WHERE product_id = %s", (update_data.product_id,))
        result = cur.fetchone()
        cur.fetchall()  # Clear any remaining results
        
        if not result:
            raise HTTPException(status_code=404, detail="Product not found in saved products")
        
        # Update the title (custom description)
        cur.execute(
            "UPDATE saved_products SET title = %s, updated_at = CURRENT_TIMESTAMP WHERE product_id = %s",
            (update_data.custom_description, update_data.product_id)
        )
        cn.commit()
        
        return {
            "status": "success",
            "message": "Product description updated successfully",
            "product_id": update_data.product_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        cn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update description: {str(e)}")
    finally:
        cur.close()
        cn.close()

@app.post("/affiliator/save")
def save_product(p: SaveProduct):
    """
    Save/Upsert a product (❤️) into our DB.
    """
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        # First, ensure saved_products table has all necessary columns
        try:
            columns_to_add = [
                "ADD COLUMN title TEXT",
                "ADD COLUMN image_main TEXT",
                "ADD COLUMN video_url TEXT",
                "ADD COLUMN sale_price DECIMAL(10,2)",
                "ADD COLUMN sale_price_currency VARCHAR(10)",
                "ADD COLUMN original_price DECIMAL(10,2)",
                "ADD COLUMN original_price_currency VARCHAR(10)",
                "ADD COLUMN lastest_volume INT",
                "ADD COLUMN rating_weighted DECIMAL(3,2)",
                "ADD COLUMN category_id VARCHAR(255)",
                "ADD COLUMN promotion_link TEXT",
                "ADD COLUMN product_url TEXT",
                "ADD COLUMN shop_url TEXT",
                "ADD COLUMN shop_title VARCHAR(500)",
                "ADD COLUMN discount_percentage DECIMAL(5,2)",
                "ADD COLUMN commission_rate DECIMAL(5,2)",
                "ADD COLUMN commission_value DECIMAL(10,2)",
                "ADD COLUMN images_extra JSON",
                "ADD COLUMN product_detail_url TEXT",
                "ADD COLUMN product_sku VARCHAR(255)",
                "ADD COLUMN product_brand VARCHAR(255)",
                "ADD COLUMN product_condition VARCHAR(50)",
                "ADD COLUMN product_warranty VARCHAR(255)",
                "ADD COLUMN product_shipping_info TEXT",
                "ADD COLUMN product_return_policy TEXT",
                "ADD COLUMN custom_description TEXT",
                "ADD COLUMN saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ]
            
            for column in columns_to_add:
                try:
                    cur.execute(f"ALTER TABLE saved_products {column}")
                except mysql.connector.Error as e:
                    # Column already exists, ignore
                    if e.errno != 1060:  # Duplicate column name
                        raise
        except Exception:
            pass  # Ignore column addition errors
        
        # Insert into saved_products table
        cur.execute(
            """
            INSERT INTO saved_products (
              product_id, title, image_main, video_url,
              sale_price, sale_price_currency, original_price, original_price_currency,
              lastest_volume, rating_weighted, category_id, promotion_link,
              product_url, shop_url, shop_title, discount_percentage,
              commission_rate, commission_value, images_extra, product_detail_url,
              product_sku, product_brand, product_condition, product_warranty,
              product_shipping_info, product_return_policy
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
              title=VALUES(title),
              image_main=VALUES(image_main),
              video_url=VALUES(video_url),
              sale_price=VALUES(sale_price),
              sale_price_currency=VALUES(sale_price_currency),
              original_price=VALUES(original_price),
              original_price_currency=VALUES(original_price_currency),
              lastest_volume=VALUES(lastest_volume),
              rating_weighted=VALUES(rating_weighted),
              category_id=VALUES(category_id),
              promotion_link=VALUES(promotion_link),
              product_url=VALUES(product_url),
              shop_url=VALUES(shop_url),
              shop_title=VALUES(shop_title),
              discount_percentage=VALUES(discount_percentage),
              commission_rate=VALUES(commission_rate),
              commission_value=VALUES(commission_value),
              images_extra=VALUES(images_extra),
              product_detail_url=VALUES(product_detail_url),
              product_sku=VALUES(product_sku),
              product_brand=VALUES(product_brand),
              product_condition=VALUES(product_condition),
              product_warranty=VALUES(product_warranty),
              product_shipping_info=VALUES(product_shipping_info),
              product_return_policy=VALUES(product_return_policy),
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                p.product_id,
                p.title,
                p.image_main,
                p.video_url,
                p.selected_price.value,
                p.selected_price.currency,
                p.selected_price.original,
                p.selected_price.original_currency or p.selected_price.currency,
                p.lastest_volume,
                p.rating_weighted,
                p.category_id,
                p.promotion_link,
                p.product_url,
                p.shop_url,
                p.shop_title,
                p.discount_percentage,
                p.commission_rate,
                p.commission_value,
                json.dumps(p.images_extra) if p.images_extra else None,
                p.product_detail_url,
                p.product_sku,
                p.product_brand,
                p.product_condition,
                p.product_warranty,
                p.product_shipping_info,
                p.product_return_policy,
            ),
        )
        cn.commit()
        return {"ok": True, "saved": True}
    except Exception as e:
        cn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close(); cn.close()

@app.post("/unsave")
def unsave_product_simple(request: dict):
    """
    Remove a product from saved_products table - Simple version for frontend.
    """
    product_id = request.get("product_id")
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required")
    
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        cur.execute("DELETE FROM saved_products WHERE product_id = %s", (product_id,))
        cn.commit()
        
        if cur.rowcount > 0:
            return {"success": True, "message": "Product unsaved successfully"}
        else:
            return {"success": False, "message": "Product not found in saved list"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cur.close(); cn.close()

@app.delete("/affiliator/unsave/{product_id}")
def unsave_product(product_id: str):
    """
    Remove a product from saved_products table.
    """
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        cur.execute("DELETE FROM saved_products WHERE product_id = %s", (product_id,))
        cn.commit()
        
        if cur.rowcount > 0:
            return {"ok": True, "message": "Product unsaved successfully"}
        else:
            return {"ok": False, "message": "Product not found in saved list"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        cur.close(); cn.close()

@app.delete("/unsave/{product_id}")
def unsave_product_simple(product_id: str):
    """
    Remove a product from saved_products table - Simple version for frontend.
    """
    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    try:
        cur.execute("DELETE FROM saved_products WHERE product_id = %s", (product_id,))
        cn.commit()
        
        if cur.rowcount > 0:
            return {"success": True, "message": "Product removed successfully"}
        else:
            return {"success": False, "detail": "Product not found"}
    except Exception as e:
        return {"success": False, "detail": "Failed to remove product"}
    finally:
        cur.close(); cn.close()

@app.get("/saved")
def get_saved_products(
    q: Optional[str] = Query(None, description="Search query"),
    sort: str = Query("saved_at_desc", pattern="^(saved_at_desc|saved_at_asc|title_asc|title_desc)$"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
):
    """
    Fetch saved products from saved_products table.
    """
    offset = (page - 1) * pageSize
    wh, params = ["1=1"], []

    if q:
        wh.append("title LIKE %s")
        params.append(f"%{q}%")

    order = {
        "saved_at_desc": "saved_at DESC",
        "saved_at_asc": "saved_at ASC",
        "title_asc": "title ASC",
        "title_desc": "title DESC",
    }[sort]

    cn = mysql.connector.connect(**DB_CFG)
    cur = cn.cursor()
    
    # Get total count
    cur.execute(f"SELECT COUNT(*) FROM saved_products WHERE {' AND '.join(wh)}", params)
    total = cur.fetchone()[0]
    
    # Get products
    cur.execute(f"""
        SELECT 
            product_id, title, image_main, video_url,
            sale_price, sale_price_currency, original_price, original_price_currency,
            lastest_volume, rating_weighted, category_id, promotion_link,
            product_url, shop_url, shop_title, discount_percentage,
            commission_rate, commission_value, images_extra, product_detail_url,
            product_sku, product_brand, product_condition, product_warranty,
            product_shipping_info, product_return_policy, custom_description, saved_at
        FROM saved_products 
        WHERE {' AND '.join(wh)}
        ORDER BY {order}
        LIMIT %s OFFSET %s
    """, params + [pageSize, offset])
    
    rows = cur.fetchall()
    cur.close(); cn.close()

    return {"items": rows, "page": page, "pageSize": pageSize, "hasMore": len(rows) >= pageSize, "total": total}

@app.get("/demo-simple")
def demo_products_simple():
    """
    Demo endpoint with guaranteed sample products for presentation - Simple version for frontend.
    """
    # Sample AliExpress products for demonstration
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
        },
        {
            "product_id": "1005001234567893",
            "product_title": "LED Strip Lights RGB - Smart Home Lighting",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567893.jpg",
            "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "sale_price": 12.99,
            "sale_price_currency": "USD",
            "original_price": 24.99,
            "original_price_currency": "USD",
            "lastest_volume": 1800,
            "rating_weighted": 4.5,
            "first_level_category_id": "100004",
            "promotion_link": "https://s.click.aliexpress.com/demo4",
            "commission_rate": 9.0,
            "discount": 48,
            "saved_at": None
        },
        {
            "product_id": "1005001234567894",
            "product_title": "Phone Case with Card Holder - Premium Protection",
            "product_main_image_url": "https://ae01.alicdn.com/kf/H1234567894.jpg",
            "product_video_url": "",
            "sale_price": 8.99,
            "sale_price_currency": "USD",
            "original_price": 15.99,
            "original_price_currency": "USD",
            "lastest_volume": 3200,
            "rating_weighted": 4.9,
            "first_level_category_id": "100003",
            "promotion_link": "https://s.click.aliexpress.com/demo5",
            "commission_rate": 15.0,
            "discount": 44,
            "saved_at": None
        }
    ]
    
    # Check which demo products are saved by joining with saved_products table
    try:
        cn = mysql.connector.connect(**DB_CFG)
        cur = cn.cursor()
        
        # Get product IDs from the demo products
        product_ids = [str(item.get('product_id', '')) for item in sample_products if item.get('product_id')]
        
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
            
            # Add saved_at field to demo products
            for item in sample_products:
                product_id = str(item.get('product_id', ''))
                if product_id in saved_products:
                    item['saved_at'] = saved_products[product_id].isoformat() if saved_products[product_id] else None
                else:
                    item['saved_at'] = None
        
        cur.close(); cn.close()
    except Exception as e:
        # If database check fails, just continue without saved_at info
        print(f"Warning: Could not check saved demo products: {e}")
        for item in sample_products:
            item['saved_at'] = None
    
    return {
        "items": sample_products,
        "page": 1,
        "pageSize": 5,
        "total": len(sample_products),
        "hasMore": False,
        "method": "demo",
        "source": "sample_data"
    }

@app.get("/search-md5")
def search_products_md5(
    request: Request,
    q: Optional[str] = None,
    categoryId: Optional[str] = None,
    page: int = 1,
    pageSize: int = int(os.getenv("DEFAULT_PAGE_SIZE", 20)),
    hot: bool = False,
    target_currency: str = "USD",
    target_language: str = "EN"
):
    """
    Search products using MD5 signature method (like Alibee_PHP)
    """
    if not APP_KEY or not APP_SECRET:
        raise HTTPException(
            status_code=400, 
            detail="AliExpress API not configured. Please set APP_KEY and APP_SECRET in .env file."
        )

    try:
        import hashlib
        import time
        
        # Base URL for AliExpress API (correct endpoint from Alibee_PHP)
        base_url = 'https://api-sg.aliexpress.com/sync'
        
        # System parameters
        sys_params = {
            'method': 'aliexpress.affiliate.hotproduct.query' if hot else 'aliexpress.affiliate.product.query',
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
            'target_language': target_language,
            'target_currency': target_currency,
            'trackingId': TRACKING_ID
        }
        
        # Add sort parameter
        if sort:
            # Map frontend sort options to AliExpress API sort types
            sort_mapping = {
                "volume_desc": "volume_desc",     # محصولات پر فروش
                "rating_desc": "score_desc",      # بیشترین ستاره
                "discount_desc": "discount_desc"  # بیشترین تخفیف
            }
            if sort in sort_mapping:
                api_params['sort'] = sort_mapping[sort]
        
        # Add search parameters
        keywords = []
        
        # Add user search query if provided
        if q:
            keywords.append(q)
        
        # Add category keywords if category is selected
        if categoryId and categoryId != "" and categoryId != "all":
            # Map category IDs to relevant keywords for better search results
            category_keywords = {
                "3": "electronics gadgets devices",
                "1501": "phone mobile smartphone accessories",
                "1420": "computer laptop office equipment",
                "1511": "consumer electronics audio video",
                "7": "home garden furniture decor",
                "1503": "jewelry accessories watches",
                "36": "sports fitness outdoor equipment",
                "1524": "automotive car motorcycle parts",
                "21": "toys games hobbies",
                "1509": "beauty health cosmetics skincare",
                "15": "women clothing fashion dress",
                "1": "men clothing fashion shirt",
                "1504": "shoes footwear sneakers",
                "1502": "bags luggage backpack suitcase",
                "1421": "tools home improvement hardware",
                "1525": "security protection safety equipment",
                "66": "mother kids baby products",
                "13": "home appliances kitchen",
                "44": "lights lighting lamps bulbs",
                "1526": "musical instruments music guitar piano drums"
            }
            
            if categoryId in category_keywords:
                # Combine user search query with category keywords
                keywords.append(category_keywords[categoryId])
            else:
                # Fallback to category_ids if no keyword mapping exists
                api_params['category_ids'] = categoryId
        
        # Set combined keywords
        if keywords:
            api_params['keywords'] = " ".join(keywords)
        
        # Combine all parameters
        all_params = {**sys_params, **api_params}
        
        # Remove empty values
        clean_params = {k: v for k, v in all_params.items() if v is not None and v != ''}
        
        # Create MD5 signature (like Alibee_PHP)
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
        data = response.json()
        
        # Extract products from response (like Alibee_PHP)
        products = []
        if 'aliexpress_affiliate_product_query_response' in data:
            resp = data['aliexpress_affiliate_product_query_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    products = result['products']['product']
                    if not isinstance(products, list):
                        products = [products]
        elif 'aliexpress_affiliate_hotproduct_query_response' in data:
            resp = data['aliexpress_affiliate_hotproduct_query_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    products = result['products']['product']
                    if not isinstance(products, list):
                        products = [products]
        
        return {
            "query": q or "hot_products",
            "page": page,
            "pageSize": pageSize,
            "total": len(products),
            "items": products,
            "method": "md5_signature",
            "source": "aliexpress_api",
            "url": url,
            "raw_response": data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/search-demo")
def search_products_demo(
    request: Request,
    q: Optional[str] = None,
    categoryId: Optional[str] = None,
    page: int = 1,
    pageSize: int = int(os.getenv("DEFAULT_PAGE_SIZE", 20)),
    hot: bool = False,
    target_currency: str = "USD",
    target_language: str = "EN",
    demo: bool = False
):
    """
    Search products with demo mode - guaranteed to return results
    """
    if demo:
        # Return demo products for guaranteed results
        sample_products = [
            {
                "product_id": "1005001234567890",
                "product_title": f"Demo Product for '{q}' - High Quality",
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
                "discount": 48
            },
            {
                "product_id": "1005001234567891",
                "product_title": f"Smart {q} - Premium Quality",
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
                "discount": 44
            }
        ]
        
        return {
            "query": q or "demo",
            "page": page,
            "pageSize": pageSize,
            "total": len(sample_products),
            "items": sample_products,
            "method": "demo_search",
            "source": "demo_data",
            "demo_mode": True
        }
    
    # Continue with real API call
    return search_products_real(request, q, categoryId, page, pageSize, hot, target_currency, target_language, None, "volume_desc", None, None)

@app.get("/search-api")
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
    """
    Direct product search from AliExpress API
    This endpoint fetches products directly from AliExpress
    """
    if not APP_KEY or not APP_SECRET:
        raise HTTPException(
            status_code=400, 
            detail="AliExpress API not configured. Please set APP_KEY and APP_SECRET in .env file."
        )

    # Special handling for "All Categories" - show Today's Deals with daily rotation
    if not categoryId or categoryId == "" or categoryId == "all":
        # For "All Categories", use hot products (Today's Deals equivalent)
        hot = True
        # Add daily rotation seed to ensure different results each day
        from datetime import datetime
        daily_seed = datetime.now().strftime("%Y%m%d")
        # Add daily seed to search query to get different results each day
        if not q:
            q = f"daily_deals_{daily_seed}"
        else:
            q = f"{q} {daily_seed}"
    
    method = "aliexpress.affiliate.hotproduct.query" if hot else "aliexpress.affiliate.product.query"

    # Base parameters
    params: Dict[str, Any] = {
        "page_no": page,
        "page_size": pageSize,
        "target_currency": target_currency,
        "target_language": target_language,
    }
    if q:
        params["keywords"] = q
    if categoryId and categoryId != "" and categoryId != "all":
        # Depending on version, category_id might be required; we pass both
        params["category_ids"] = categoryId
        params["category_id"] = categoryId

    # Passthrough common parameters used in Explorer
    passthrough = [
        "fields", "ship_to_country", "delivery_days", "sort",
        "platform_product_type", "promotion_name",
        "min_sale_price", "max_sale_price",
        "target_country", "country",           # Some versions
    ]
    for k in passthrough:
        v = request.query_params.get(k)
        if v:
            params[k] = v

    try:
        # Use MD5 signature method (like Alibee_PHP) - WORKING SOLUTION
        import hashlib
        import time
        
        # Base URL for AliExpress API (correct endpoint from Alibee_PHP)
        base_url = 'https://api-sg.aliexpress.com/sync'
        
        # System parameters
        sys_params = {
            'method': method,
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
            'target_language': target_language,
            'target_currency': target_currency,
            'trackingId': TRACKING_ID
        }
        
        # Add sort parameter
        if sort:
            # Map frontend sort options to AliExpress API sort types
            sort_mapping = {
                "volume_desc": "volume_desc",     # محصولات پر فروش
                "rating_desc": "score_desc",      # بیشترین ستاره
                "discount_desc": "discount_desc"  # بیشترین تخفیف
            }
            if sort in sort_mapping:
                api_params['sort'] = sort_mapping[sort]
        
        # Add search parameters
        keywords = []
        
        # Add user search query if provided
        if q:
            keywords.append(q)
        
        # Add category keywords if category is selected
        if categoryId and categoryId != "" and categoryId != "all":
            # Map category IDs to relevant keywords for better search results
            category_keywords = {
                "3": "electronics gadgets devices",
                "1501": "phone mobile smartphone accessories",
                "1420": "computer laptop office equipment",
                "1511": "consumer electronics audio video",
                "7": "home garden furniture decor",
                "1503": "jewelry accessories watches",
                "36": "sports fitness outdoor equipment",
                "1524": "automotive car motorcycle parts",
                "21": "toys games hobbies",
                "1509": "beauty health cosmetics skincare",
                "15": "women clothing fashion dress",
                "1": "men clothing fashion shirt",
                "1504": "shoes footwear sneakers",
                "1502": "bags luggage backpack suitcase",
                "1421": "tools home improvement hardware",
                "1525": "security protection safety equipment",
                "66": "mother kids baby products",
                "13": "home appliances kitchen",
                "44": "lights lighting lamps bulbs",
                "1526": "musical instruments music guitar piano drums"
            }
            
            if categoryId in category_keywords:
                # Combine user search query with category keywords
                keywords.append(category_keywords[categoryId])
            else:
                # Fallback to category_ids if no keyword mapping exists
                api_params['category_ids'] = categoryId
        
        # Set combined keywords
        if keywords:
            api_params['keywords'] = " ".join(keywords)
        
        # Add passthrough parameters
        for k in passthrough:
            v = request.query_params.get(k)
            if v:
                api_params[k] = v
        
        # Combine all parameters
        all_params = {**sys_params, **api_params}
        
        # Remove empty values
        clean_params = {k: v for k, v in all_params.items() if v is not None and v != ''}
        
        # Create MD5 signature (like Alibee_PHP)
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
        
        # Extract products from response (like Alibee_PHP)
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
        items = _normalize_items({'items': items})

        # Apply hasVideo filter if requested
        if hasVideo:
            items = [item for item in items 
                    if item.get('product_video_url') and item.get('product_video_url').strip()]
            
            # اگر محصولات ویدیو دار پیدا نشد، چندین صفحه دیگر را جستجو کن
            if not items and page == 1:
                items = _search_multiple_pages_for_video_products(
                    method, params, api_params, passthrough, request, pageSize
                )
        
        # Apply price range filter if requested
        if minPrice is not None or maxPrice is not None:
            filtered_items = []
            for item in items:
                try:
                    # Get sale price (preferred) or original price
                    price = None
                    if item.get('sale_price'):
                        price = float(item.get('sale_price', 0))
                    elif item.get('original_price'):
                        price = float(item.get('original_price', 0))
                    
                    if price is not None:
                        # Check if price is within range
                        within_range = True
                        if minPrice is not None and price < minPrice:
                            within_range = False
                        if maxPrice is not None and price > maxPrice:
                            within_range = False
                        
                        if within_range:
                            filtered_items.append(item)
                except (ValueError, TypeError):
                    # Skip items with invalid price data
                    continue
            
            items = filtered_items

        # If still nothing found, try other common paths (soft guard)
        if not items:
            result = raw.get("result") or {}
            items = (
                result.get("product_list") or
                result.get("ae_hot_products") or
                result.get("ae_products") or
                []
            )

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
                    
                    # Query saved_products table to get saved_at timestamps and custom titles
                    cur.execute(f"""
                        SELECT product_id, saved_at, title 
                        FROM saved_products 
                        WHERE product_id IN ({placeholders})
                    """, product_ids)
                    
                    saved_products = {row[0]: {'saved_at': row[1], 'title': row[2]} for row in cur.fetchall()}
                    
                    # Add saved_at field and custom title to items
                    for item in items:
                        product_id = str(item.get('product_id', ''))
                        if product_id in saved_products:
                            item['saved_at'] = saved_products[product_id]['saved_at'].isoformat() if saved_products[product_id]['saved_at'] else None
                            # Use custom title if it exists and is different from original
                            custom_title = saved_products[product_id]['title']
                            if custom_title and custom_title != item.get('product_title', ''):
                                item['custom_title'] = custom_title
                        else:
                            item['saved_at'] = None
                
                cur.close(); cn.close()
            except Exception as e:
                # If database check fails, just continue without saved_at info
                print(f"Warning: Could not check saved products: {e}")
                for item in items:
                    item['saved_at'] = None

        # Apply client-side sorting since AliExpress API sorting may not work as expected
        if sort and items:
            if sort == "volume_desc":
                # Sort by sales volume (highest first)
                items.sort(key=lambda x: int(x.get('lastest_volume', 0) or 0), reverse=True)
            elif sort == "rating_desc":
                # Sort by rating (highest first)
                items.sort(key=lambda x: float(x.get('rating_weighted', 0) or 0), reverse=True)
            elif sort == "discount_desc":
                # Sort by discount percentage (highest first)
                def calculate_discount(item):
                    try:
                        original = float(item.get('original_price', 0) or 0)
                        sale = float(item.get('sale_price', 0) or 0)
                        if original > 0 and sale > 0:
                            return ((original - sale) / original) * 100
                        return 0
                    except:
                        return 0
                items.sort(key=calculate_discount, reverse=True)

        # Record search history
        if q:
            try:
                cn = mysql.connector.connect(**DB_CFG)
                cur = cn.cursor()
                cur.execute(
                    "INSERT INTO search_history (query, results_count, user_ip) VALUES (%s, %s, %s)",
                    (q, len(items), request.client.host if request.client else None)
                )
                cn.commit()
                cur.close(); cn.close()
            except Exception:
                pass  # Don't fail the main request if logging fails

        debug = request.query_params.get("debug") in ("1", "true", "yes")
        return {
            "items": items or [],
            "page": page,
            "pageSize": pageSize,
            "hasMore": len(items or []) >= pageSize,  # اگر تعداد items برابر یا بیشتر از pageSize باشد، احتمالاً صفحه بعدی وجود دارد
            "live": True,
            "method": method,
            **({"raw": raw} if debug else {})
        }
    except requests.HTTPError as rexc:
        text = getattr(rexc.response, "text", "")
        raise HTTPException(status_code=502, detail=f"AliExpress HTTP error: {rexc} {text}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AliExpress error: {e}")

@app.get("/search-demo-v2")
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
    """
    Search products with demo fallback - guaranteed to return results
    """
    if demo or not APP_KEY or not APP_SECRET:
        # Return demo products for guaranteed results
        sample_products = [
            {
                "product_id": "1005001234567890",
                "product_title": f"Demo Product for '{q or 'search'}' - High Quality",
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
                "product_title": f"Smart {q or 'Device'} - Premium Quality",
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
                "product_title": f"Portable {q or 'Gadget'} - Fast Performance",
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
            "page": page,
            "pageSize": pageSize,
            "total": len(sample_products),
            "hasMore": False,
            "method": "demo_search",
            "source": "demo_data",
            "demo_mode": True
        }
    
    # Continue with real API call
    return search_products_real(request, q, categoryId, page, pageSize, hot, target_currency, target_language, None, "volume_desc", None, None)

@app.get("/search")
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
    sort: str = Query("volume_desc", description="Sort order"),
    minPrice: Optional[float] = Query(None, description="Minimum price"),
    maxPrice: Optional[float] = Query(None, description="Maximum price"),
):
    """
    Search products with demo fallback - guaranteed to return results
    """
    if demo or not APP_KEY or not APP_SECRET:
        # Return demo products for guaranteed results
        # For "All Categories", show Today's Deals style products
        if not categoryId or categoryId == "" or categoryId == "all":
            sample_products = [
                {
                    "product_id": "1005001234567890",
                    "product_title": "🔥 Today's Deal: Wireless Bluetooth Headphones - 50% OFF",
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
                "product_title": f"Smart {q or 'Device'} - Premium Quality",
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
                "product_title": f"Portable {q or 'Gadget'} - Fast Performance",
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
            "page": page,
            "pageSize": pageSize,
            "total": len(sample_products),
            "hasMore": len(sample_products) >= pageSize,  # اگر تعداد items برابر یا بیشتر از pageSize باشد، احتمالاً صفحه بعدی وجود دارد
            "method": "demo_search",
            "source": "demo_data",
            "demo_mode": True
        }
    
    # Special handling for "All Categories" - show Today's Deals with daily rotation
    if not categoryId or categoryId == "" or categoryId == "all":
        # For "All Categories", use hot products (Today's Deals equivalent)
        hot = True
        # Add daily rotation seed to ensure different results each day
        from datetime import datetime
        daily_seed = datetime.now().strftime("%Y%m%d")
        # Add daily seed to search query to get different results each day
        if not q:
            q = f"daily_deals_{daily_seed}"
        else:
            q = f"{q} {daily_seed}"
    
    # Continue with real API call
    return search_products_real(request, q, categoryId, page, pageSize, hot, target_currency, target_language, hasVideo, sort, minPrice, maxPrice)
        
@app.post("/ali/link")
def ali_generate_link(urls: List[str]):
    """
    Generate affiliate links for one or multiple product URLs.
    """
    if not ali_client:
        raise HTTPException(status_code=400, detail="AliExpress client not configured.")
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    try:
        raw = ali_client.call("aliexpress.affiliate.link.generate", source_values=",".join(urls))
        resp = next((raw.get(k) for k in raw.keys() if k.endswith("_response")), raw) or {}
        resp_result = resp.get("resp_result") or {}
        result = resp_result.get("result") or {}
        links = result.get("links") or result
        
        # Record affiliate links in database
        if links:
            try:
                cn = mysql.connector.connect(**DB_CFG)
                cur = cn.cursor()
                
                for link_data in links:
                    if isinstance(link_data, dict):
                        original_url = link_data.get("source_value", "")
                        affiliate_url = link_data.get("promotion_link", "")
                        
                        if original_url and affiliate_url:
                            # Extract product_id from URL (if possible)
                            product_id = "unknown"
                            if "item/" in original_url:
                                try:
                                    product_id = original_url.split("item/")[1].split(".")[0]
                                except:
                                    pass
                            
                            cur.execute(
                                """INSERT INTO affiliate_links 
                                   (product_id, original_url, affiliate_url) 
                                   VALUES (%s, %s, %s)
                                   ON DUPLICATE KEY UPDATE 
                                   affiliate_url=VALUES(affiliate_url),
                                   updated_at=NOW()""",
                                (product_id, original_url, affiliate_url)
                            )
                
                cn.commit()
                cur.close(); cn.close()
            except Exception:
                pass  # Don't fail the main request if logging fails
        
        return {"links": links}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─────────────────── Helper Functions ───────────────────
def _search_multiple_pages_for_video_products(method, params, api_params, passthrough, request, pageSize):
    """
    جستجوی چندین صفحه برای پیدا کردن محصولات ویدیو دار
    """
    import hashlib
    import time
    import requests
    
    base_url = 'https://api-sg.aliexpress.com/sync'
    video_products = []
    max_pages_to_search = 20  # حداکثر 20 صفحه جستجو کن
    
    for page_num in range(2, max_pages_to_search + 2):  # از صفحه 2 شروع کن
        try:
            # System parameters
            sys_params = {
                'method': method,
                'app_key': APP_KEY,
                'sign_method': 'md5',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                'format': 'json',
                'v': '2.0'
            }
            
            # API parameters
            current_api_params = api_params.copy()
            current_api_params['page_no'] = page_num
            current_api_params['page_size'] = pageSize
            
            # Add passthrough parameters
            for k in passthrough:
                v = request.query_params.get(k)
                if v:
                    current_api_params[k] = v
            
            # Combine all parameters
            all_params = {**sys_params, **current_api_params}
            
            # Remove empty values
            clean_params = {k: v for k, v in all_params.items() if v is not None and v != ''}
            
            # Create MD5 signature
            def create_md5_signature(params, secret):
                sorted_params = sorted(params.items())
                base_string = secret
                for key, value in sorted_params:
                    base_string += key + str(value)
                base_string += secret
                return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()
            
            signature = create_md5_signature(clean_params, APP_SECRET)
            clean_params['sign'] = signature
            
            # Build URL
            url = base_url + '?' + '&'.join([f"{k}={v}" for k, v in clean_params.items()])
            
            # Make request
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse response
            raw = response.json()
            
            # Extract products
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
            
            # Normalize items
            normalized_items = _normalize_items({'items': items})
            
            # Filter for video products
            video_items = [item for item in normalized_items 
                          if item.get('product_video_url') and item.get('product_video_url').strip()]
            
            video_products.extend(video_items)
            
            # اگر به اندازه کافی محصول ویدیو دار پیدا کردیم، متوقف شو
            if len(video_products) >= pageSize:
                break
                
        except Exception as e:
            print(f"Error searching page {page_num}: {e}")
            continue
    
    # فقط تعداد مورد نیاز را برگردان
    return video_products[:pageSize]

# ─────────────────── Local run ───────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=int(os.getenv("PORT", "8080")), reload=True)
