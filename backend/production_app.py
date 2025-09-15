from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import mysql.connector
import os
import json
import logging
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
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "aliexpress_api": "configured" if APP_KEY else "not_configured"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

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
    q: str = Query(..., description="Search query"),
    sort: str = Query("volume_desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size")
):
    try:
        if not APP_KEY or not APP_SECRET or not TRACKING_ID:
            logger.warning("AliExpress API credentials not configured, returning mock data")
            return generate_mock_data(page, pageSize)
        
        # AliExpress API call would go here
        # For now, return mock data
        return generate_mock_data(page, pageSize)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

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
