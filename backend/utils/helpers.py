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

def get_demo_products(search_query: str = None) -> List[Dict[str, Any]]:
    """Get demo products for testing with search-relevant filtering"""
    
    # Create search-relevant demo products based on common search terms
    demo_products_by_category = {
        "watch": [
            {
                "product_id": "1005001234567890",
                "product_title": "⌚ Smart Watch - Fitness Tracker with Heart Rate Monitor",
                "product_main_image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "sale_price": 45.99,
                "sale_price_currency": "USD",
                "original_price": 89.99,
                "original_price_currency": "USD",
                "lastest_volume": 1250,
                "rating_weighted": 4.8,
                "first_level_category_id": "100001",
                "promotion_link": "https://s.click.aliexpress.com/demo1",
                "commission_rate": 8.5,
                "discount": 49,
                "saved_at": None
            },
            {
                "product_id": "1005001234567891",
                "product_title": "🕐 Digital Watch - Waterproof Sports Watch",
                "product_main_image_url": "https://images.unsplash.com/photo-1523170335258-f5c6a6f1e6b1?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 29.99,
                "sale_price_currency": "USD",
                "original_price": 59.99,
                "original_price_currency": "USD",
                "lastest_volume": 890,
                "rating_weighted": 4.6,
                "first_level_category_id": "100001",
                "promotion_link": "https://s.click.aliexpress.com/demo2",
                "commission_rate": 12.0,
                "discount": 50,
                "saved_at": None
            }
        ],
        "phone": [
            {
                "product_id": "1005001234567892",
                "product_title": "📱 Smartphone - 128GB Storage with Dual Camera",
                "product_main_image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                "sale_price": 199.99,
                "sale_price_currency": "USD",
                "original_price": 299.99,
                "original_price_currency": "USD",
                "lastest_volume": 2100,
                "rating_weighted": 4.7,
                "first_level_category_id": "100002",
                "promotion_link": "https://s.click.aliexpress.com/demo3",
                "commission_rate": 6.5,
                "discount": 33,
                "saved_at": None
            }
        ],
        "laptop": [
            {
                "product_id": "1005001234567893",
                "product_title": "💻 Gaming Laptop - 16GB RAM, 512GB SSD",
                "product_main_image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 799.99,
                "sale_price_currency": "USD",
                "original_price": 1199.99,
                "original_price_currency": "USD",
                "lastest_volume": 450,
                "rating_weighted": 4.9,
                "first_level_category_id": "100003",
                "promotion_link": "https://s.click.aliexpress.com/demo4",
                "commission_rate": 10.0,
                "discount": 33,
                "saved_at": None
            }
        ],
        "headphones": [
            {
                "product_id": "1005001234567894",
                "product_title": "🎧 Wireless Bluetooth Headphones - Noise Cancelling",
                "product_main_image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 39.99,
                "sale_price_currency": "USD",
                "original_price": 79.99,
                "original_price_currency": "USD",
                "lastest_volume": 780,
                "rating_weighted": 4.5,
                "first_level_category_id": "100004",
                "promotion_link": "https://s.click.aliexpress.com/demo5",
                "commission_rate": 15.0,
                "discount": 50,
                "saved_at": None
            }
        ],
        "shoes": [
            {
                "product_id": "1005001234567895",
                "product_title": "👟 Running Shoes - Comfortable Athletic Sneakers",
                "product_main_image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 49.99,
                "sale_price_currency": "USD",
                "original_price": 99.99,
                "original_price_currency": "USD",
                "lastest_volume": 1200,
                "rating_weighted": 4.6,
                "first_level_category_id": "100005",
                "promotion_link": "https://s.click.aliexpress.com/demo6",
                "commission_rate": 12.0,
                "discount": 50,
                "saved_at": None
            }
        ],
        "bag": [
            {
                "product_id": "1005001234567896",
                "product_title": "👜 Leather Handbag - Fashionable Shoulder Bag",
                "product_main_image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 35.99,
                "sale_price_currency": "USD",
                "original_price": 69.99,
                "original_price_currency": "USD",
                "lastest_volume": 650,
                "rating_weighted": 4.4,
                "first_level_category_id": "100006",
                "promotion_link": "https://s.click.aliexpress.com/demo7",
                "commission_rate": 18.0,
                "discount": 49,
                "saved_at": None
            }
        ],
        # Add more categories for better keyword matching
        "hat": [
            {
                "product_id": "1005001234567897",
                "product_title": "🧢 Baseball Cap - Adjustable Sports Hat",
                "product_main_image_url": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 12.99,
                "sale_price_currency": "USD",
                "original_price": 24.99,
                "original_price_currency": "USD",
                "lastest_volume": 1800,
                "rating_weighted": 4.3,
                "first_level_category_id": "100007",
                "promotion_link": "https://s.click.aliexpress.com/demo8",
                "commission_rate": 20.0,
                "discount": 48,
                "saved_at": None
            }
        ],
        "camera": [
            {
                "product_id": "1005001234567898",
                "product_title": "📷 Digital Camera - 4K Video Recording",
                "product_main_image_url": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 299.99,
                "sale_price_currency": "USD",
                "original_price": 499.99,
                "original_price_currency": "USD",
                "lastest_volume": 320,
                "rating_weighted": 4.7,
                "first_level_category_id": "100008",
                "promotion_link": "https://s.click.aliexpress.com/demo9",
                "commission_rate": 8.0,
                "discount": 40,
                "saved_at": None
            }
        ],
        "book": [
            {
                "product_id": "1005001234567899",
                "product_title": "📚 Educational Book - Learning Guide",
                "product_main_image_url": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 19.99,
                "sale_price_currency": "USD",
                "original_price": 39.99,
                "original_price_currency": "USD",
                "lastest_volume": 450,
                "rating_weighted": 4.6,
                "first_level_category_id": "100009",
                "promotion_link": "https://s.click.aliexpress.com/demo10",
                "commission_rate": 25.0,
                "discount": 50,
                "saved_at": None
            }
        ]
    }
    
    # If no search query, return a mix of products
    if not search_query:
        all_products = []
        for category_products in demo_products_by_category.values():
            all_products.extend(category_products)
        return all_products[:5]  # Return first 5 products
    
    # Search for relevant products based on query
    search_lower = search_query.lower().strip()
    relevant_products = []
    
    # Check if the search query is a product ID
    # Product IDs are typically long numeric strings (e.g., "1005001234567890")
    is_product_id_search = False
    if search_lower and search_lower.isdigit() and len(search_lower) >= 10:
        is_product_id_search = True
        print(f"🔍 Product ID search detected: '{search_query}'")
        
        # Search for the specific product ID in all demo products
        for category, products in demo_products_by_category.items():
            for product in products:
                if product.get('product_id') == search_query:
                    print(f"✅ Found product by ID: {product.get('product_title')}")
                    relevant_products.append(product)
                    break
            if relevant_products:
                break
        
        if not relevant_products:
            print(f"❌ Product ID '{search_query}' not found in demo products")
            # Return a message product indicating the ID was not found
            relevant_products = [{
                "product_id": search_query,
                "product_title": f"🔍 Product ID '{search_query}' not found",
                "product_main_image_url": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=400&fit=crop&crop=center",
                "product_video_url": "",
                "sale_price": 0.00,
                "sale_price_currency": "USD",
                "original_price": 0.00,
                "original_price_currency": "USD",
                "lastest_volume": 0,
                "rating_weighted": 0.0,
                "first_level_category_id": "000000",
                "promotion_link": "",
                "commission_rate": 0.0,
                "discount": 0,
                "saved_at": None
            }]
    
    # If not a product ID search, proceed with normal keyword search
    if not is_product_id_search:
        # Extract the original keyword from enhanced queries
        # Enhanced queries look like: "hat cap baseball cap beanie winter hat summer hat"
        # We want to extract the main keyword: "hat"
        original_keyword = None
        if search_lower:
            # Split by spaces and find the first word that matches a category
            words = search_lower.split()
            for word in words:
                if word in demo_products_by_category:
                    original_keyword = word
                    break
            
            # If no exact category match, use the first word as the main keyword
            if not original_keyword and words:
                original_keyword = words[0]
        
        print(f"🔍 Demo search for: '{search_query}' -> '{search_lower}' -> original: '{original_keyword}'")
        
        # First, try exact category matches with original keyword
        if original_keyword and original_keyword in demo_products_by_category:
            print(f"✅ Original keyword exact match: {original_keyword}")
            relevant_products.extend(demo_products_by_category[original_keyword])
        
        # If no match with original keyword, try exact category matches with full query
        if not relevant_products:
            for category, products in demo_products_by_category.items():
                if category == search_lower:
                    print(f"✅ Full query exact match: {category}")
                    relevant_products.extend(products)
                    break
        
        # If no exact match, try partial category matches
        if not relevant_products:
            for category, products in demo_products_by_category.items():
                if category in search_lower or any(keyword in search_lower for keyword in category.split()):
                    print(f"✅ Partial category match: {category}")
                    relevant_products.extend(products)
                    break
        
        # If no category match, try to find products with matching keywords in titles
        if not relevant_products:
            for category, products in demo_products_by_category.items():
                for product in products:
                    title = product.get('product_title', '').lower()
                    if any(keyword in title for keyword in search_lower.split()):
                        print(f"✅ Title keyword match: {keyword} in {title}")
                        relevant_products.append(product)
        
        # If still no matches, try broader keyword matching
        if not relevant_products:
            # Create a mapping of common keywords to categories
            keyword_mapping = {
                'smart': 'phone',
                'mobile': 'phone', 
                'android': 'phone',
                'iphone': 'phone',
                'computer': 'laptop',
                'notebook': 'laptop',
                'gaming': 'laptop',
                'earphone': 'headphones',
                'earbud': 'headphones',
                'bluetooth': 'headphones',
                'sneaker': 'shoes',
                'athletic': 'shoes',
                'running': 'shoes',
                'handbag': 'bag',
                'purse': 'bag',
                'backpack': 'bag',
                'cap': 'hat',
                'baseball': 'hat',
                'digital': 'camera',
                'photo': 'camera',
                'recording': 'camera',
                'learning': 'book',
                'education': 'book',
                'guide': 'book'
            }
            
            # Try keyword mapping with original keyword first
            if original_keyword and original_keyword in keyword_mapping:
                category = keyword_mapping[original_keyword]
                if category in demo_products_by_category:
                    print(f"✅ Original keyword mapping match: {original_keyword} -> {category}")
                    relevant_products.extend(demo_products_by_category[category])
            
            # If no match with original keyword, try with full query
            if not relevant_products:
                for keyword, category in keyword_mapping.items():
                    if keyword in search_lower and category in demo_products_by_category:
                        print(f"✅ Full query keyword mapping match: {keyword} -> {category}")
                        relevant_products.extend(demo_products_by_category[category])
                        break
        
        # If still no matches, return a diverse mix instead of just the first category
        if not relevant_products:
            print(f"❌ No matches found for '{search_query}', returning diverse mix")
            # Return a mix of different categories instead of just the first one
            all_products = []
            for category_products in demo_products_by_category.values():
                all_products.extend(category_products)
            # Return first 3 products from different categories
            relevant_products = all_products[:3]
    
    print(f"📦 Returning {len(relevant_products)} products for search: '{search_query}'")
    return relevant_products

def get_categories() -> List[Dict[str, str]]:
    """Get predefined categories"""
    return [
        {"id": "100001", "name": "Electronics", "name_fa": "الکترونیک"},
        {"id": "100002", "name": "Fashion", "name_fa": "مد و پوشاک"},
        {"id": "100003", "name": "Home & Garden", "name_fa": "خانه و باغ"},
        {"id": "100004", "name": "Sports & Outdoor", "name_fa": "ورزش و طبیعت"},
        {"id": "100005", "name": "Beauty & Health", "name_fa": "زیبایی و سلامت"},
        {"id": "100006", "name": "Automotive", "name_fa": "خودرو"},
        {"id": "100007", "name": "Toys & Hobbies", "name_fa": "اسباب بازی و سرگرمی"},
        {"id": "100008", "name": "Jewelry & Accessories", "name_fa": "جواهرات و اکسسوری"},
        {"id": "100009", "name": "Shoes & Bags", "name_fa": "کفش و کیف"},
        {"id": "100010", "name": "Computer & Office", "name_fa": "کامپیوتر و اداری"},
        {"id": "1421", "name": "Electronics & Gadgets", "name_fa": "الکترونیک و گجت"},
        {"id": "1509", "name": "Women's Fashion", "name_fa": "مد زنانه"},
        {"id": "1525", "name": "Men's Fashion", "name_fa": "مد مردانه"},
        {"id": "1526", "name": "Musical Instruments", "name_fa": "لوازم موسیقی و سازها"}
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
