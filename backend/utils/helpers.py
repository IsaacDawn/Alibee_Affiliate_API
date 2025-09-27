# backend/utils/helpers.py
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

def get_daily_seed() -> str:
    """Get daily seed for product rotation"""
    return datetime.now().strftime("%Y%m%d")

def format_price(price: Any, currency: str = "USD") -> str:
    """Format price with currency"""
    try:
        if price is None:
            return "N/A"
        return f"{float(price):.2f} {currency}"
    except (ValueError, TypeError):
        return "N/A"

def format_rating(rating: Any) -> str:
    """Format rating value"""
    try:
        if rating is None:
            return "N/A"
        return f"{float(rating):.1f}"
    except (ValueError, TypeError):
        return "N/A"

def format_volume(volume: Any) -> str:
    """Format volume number"""
    try:
        if volume is None:
            return "0"
        vol = int(volume)
        if vol >= 1000000:
            return f"{vol/1000000:.1f}M"
        elif vol >= 1000:
            return f"{vol/1000:.1f}K"
        else:
            return str(vol)
    except (ValueError, TypeError):
        return "0"

def calculate_discount_percentage(original_price: float, sale_price: float) -> float:
    """Calculate discount percentage"""
    try:
        if not original_price or not sale_price or original_price <= 0:
            return 0
        return round(((original_price - sale_price) / original_price) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

def is_valid_product_id(product_id: str) -> bool:
    """Check if product ID is valid"""
    try:
        return bool(product_id and str(product_id).strip() and len(str(product_id)) > 0)
    except:
        return False

def sanitize_string(text: str) -> str:
    """Sanitize string for database storage"""
    if not text:
        return ""
    return str(text).strip()[:1000]  # Limit to 1000 characters


def get_categories() -> List[Dict[str, str]]:
    """Get predefined categories"""
    return [
        {"id": "100001", "name": "Electronics"},
        {"id": "100002", "name": "Fashion"},
        {"id": "100003", "name": "Home & Garden"},
        {"id": "100004", "name": "Sports & Outdoor"},
        {"id": "100005", "name": "Beauty & Health"},
        {"id": "100006", "name": "Automotive"},
        {"id": "100007", "name": "Toys & Hobbies"},
        {"id": "100008", "name": "Jewelry & Accessories"},
        {"id": "100009", "name": "Shoes & Bags"},
        {"id": "100010", "name": "Computer & Office"},
        {"id": "1421", "name": "Electronics & Gadgets"},
        {"id": "1509", "name": "Women's Fashion"},
        {"id": "1525", "name": "Men's Fashion"},
        {"id": "1526", "name": "Musical Instruments"}
    ]

def validate_pagination_params(page: int, page_size: int, max_page_size: int = 100) -> tuple:
    """Validate and normalize pagination parameters"""
    page = max(1, int(page)) if page else 1
    page_size = max(1, min(int(page_size), max_page_size)) if page_size else 20
    return page, page_size

def create_error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": True,
        "message": message,
        "status_code": status_code,
        "timestamp": get_current_timestamp()
    }

def create_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    response = {
        "success": True,
        "message": message,
        "timestamp": get_current_timestamp()
    }
    if data is not None:
        response["data"] = data
    return response

def merge_product_with_saved_info(product: Dict[str, Any], saved_info: Dict[str, Any]) -> Dict[str, Any]:
    """Merge product data with saved product information"""
    if not saved_info:
        return product
    
    # Add saved_at timestamp
    if saved_info.get('saved_at'):
        product['saved_at'] = saved_info['saved_at'].isoformat() if hasattr(saved_info['saved_at'], 'isoformat') else str(saved_info['saved_at'])
    
    # Add custom title if different from original
    custom_title = saved_info.get('title')
    if custom_title and custom_title != product.get('product_title', ''):
        product['custom_title'] = custom_title
    
    return product

def filter_products_by_video(products: List[Dict[str, Any]], has_video: bool = None) -> List[Dict[str, Any]]:
    """Filter products by video availability"""
    if has_video is None:
        return products
    
    if has_video:
        return [p for p in products if p.get('product_video_url')]
    else:
        return [p for p in products if not p.get('product_video_url')]

def sort_products(products: List[Dict[str, Any]], sort_by: str = "volume_desc") -> List[Dict[str, Any]]:
    """Sort products by various criteria"""
    if not products:
        return products
    
    try:
        if sort_by == "volume_desc":
            return sorted(products, key=lambda x: x.get('lastest_volume', 0), reverse=True)
        elif sort_by == "volume_asc":
            return sorted(products, key=lambda x: x.get('lastest_volume', 0))
        elif sort_by == "price_desc":
            return sorted(products, key=lambda x: x.get('sale_price', 0), reverse=True)
        elif sort_by == "price_asc":
            return sorted(products, key=lambda x: x.get('sale_price', 0))
        elif sort_by == "rating_desc":
            return sorted(products, key=lambda x: x.get('rating_weighted', 0), reverse=True)
        elif sort_by == "rating_asc":
            return sorted(products, key=lambda x: x.get('rating_weighted', 0))
        else:
            return products
    except Exception as e:
        print(f"Error sorting products: {e}")
        return products
