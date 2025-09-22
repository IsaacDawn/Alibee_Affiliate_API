# backend/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class Price(BaseModel):
    """Price model for products"""
    value: float = Field(..., description="Price value")
    currency: str = Field(..., description="Currency code")

class SaveProduct(BaseModel):
    """Model for saving a product - Optimized version with only essential fields"""
    product_id: str = Field(..., description="Product ID")
    product_title: str = Field(..., description="Product title")
    promotion_link: str = Field(..., description="Affiliate promotion link")
    product_category: Optional[str] = Field(None, description="Product category")
    custom_title: Optional[str] = Field(None, description="Custom title for the product")
    has_video: Optional[bool] = Field(False, description="Whether the product has a video")

class UpdateProductDescription(BaseModel):
    """Model for updating product description"""
    product_id: str = Field(..., description="Product ID")
    custom_description: str = Field(..., description="Custom description")

class ProductResponse(BaseModel):
    """Model for product response"""
    product_id: str
    product_title: str
    product_main_image_url: Optional[str] = None
    product_video_url: Optional[str] = None
    sale_price: Optional[float] = None
    sale_price_currency: Optional[str] = None
    original_price: Optional[float] = None
    original_price_currency: Optional[str] = None
    lastest_volume: Optional[int] = None
    rating_weighted: Optional[float] = None
    first_level_category_id: Optional[str] = None
    promotion_link: Optional[str] = None
    saved_at: Optional[str] = None
    custom_title: Optional[str] = None
    # Additional fields from demo pattern
    product_description: Optional[str] = None
    discount: Optional[float] = None
    commission_rate: Optional[float] = None
    shop_title: Optional[str] = None
    shop_url: Optional[str] = None
    product_detail_url: Optional[str] = None
    product_small_image_urls: Optional[List[str]] = None
    first_level_category_name: Optional[str] = None
    second_level_category_name: Optional[str] = None
    evaluate_rate: Optional[str] = None
    rating_percent: Optional[str] = None
    positive_feedback_rate: Optional[str] = None
    avg_evaluation_rate: Optional[str] = None
    avg_rating_percent: Optional[str] = None
    product_score: Optional[str] = None
    product_score_stars: Optional[float] = None
    product_category: Optional[str] = None
    images_link: Optional[List[str]] = None
    video_link: Optional[str] = None

class SearchResponse(BaseModel):
    """Model for search response"""
    items: List[ProductResponse]
    page: int
    pageSize: int
    hasMore: bool
    total: Optional[int] = None
    method: Optional[str] = None
    source: Optional[str] = None
    demo_mode: Optional[bool] = None

class StatsResponse(BaseModel):
    """Model for stats response"""
    totalProducts: int
    savedProducts: int
    totalSearches: int
    activeUsers: int
    affiliate_links: int
    recent_searches: int

class CategoryResponse(BaseModel):
    """Model for category response"""
    id: str
    name: str
    name_fa: str

class HealthResponse(BaseModel):
    """Model for health check response"""
    status: str
    timestamp: str
    version: str
    database: str
    aliexpress_api: str
