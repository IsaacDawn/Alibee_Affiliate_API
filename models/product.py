# Product models and schemas
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Price(BaseModel):
    value: float
    currency: str
    original: Optional[float] = None
    original_currency: Optional[str] = None

class SaveProductRequest(BaseModel):
    product_id: str
    title: str
    image_url: str
    video_url: Optional[str] = None
    sale_price: float
    sale_price_currency: str
    original_price: Optional[float] = None
    original_price_currency: Optional[str] = None
    volume: int
    rating: float
    category_id: Optional[str] = None
    promotion_link: str

class ProductResponse(BaseModel):
    product_id: str
    product_title: str
    product_main_image_url: str
    product_video_url: Optional[str] = None
    sale_price: float
    sale_price_currency: str
    original_price: Optional[float] = None
    original_price_currency: Optional[str] = None
    lastest_volume: int
    rating_weighted: float
    first_level_category_id: Optional[str] = None
    promotion_link: str
    saved_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None

class PaginatedResponse(BaseModel):
    items: List[ProductResponse]
    page: int
    pageSize: int
    hasMore: bool

class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None
