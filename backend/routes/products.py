# backend/routes/products.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from models.schemas import SaveProduct, UpdateProductDescription
from database.connection import db_ops
from utils.helpers import validate_pagination_params, create_success_response, create_error_response

router = APIRouter()

@router.post("/save-product")
def save_product_simple(p: SaveProduct):
    """Save a product to the database"""
    try:
        # Convert Pydantic model to dict
        product_data = p.dict()
        
        # Save to database
        success = db_ops.save_product(product_data)
        
        if success:
            return create_success_response(message="Product saved successfully")
        else:
            raise HTTPException(status_code=500, detail="Failed to save product")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save product: {str(e)}")

@router.post("/affiliator/save")
def save_product(p: SaveProduct):
    """Save a product to the database (affiliator endpoint)"""
    try:
        # Convert Pydantic model to dict
        product_data = p.dict()
        
        # Save to database
        success = db_ops.save_product(product_data)
        
        if success:
            return create_success_response(message="Product saved successfully")
        else:
            raise HTTPException(status_code=500, detail="Failed to save product")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save product: {str(e)}")

@router.post("/unsave")
def unsave_product_simple(request: dict):
    """Remove a product from saved products"""
    product_id = request.get("product_id")
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required")
    
    success = db_ops.unsave_product(product_id)
    
    if success:
        return create_success_response(message="Product unsaved successfully")
    else:
        return create_error_response("Product not found in saved list")

@router.delete("/affiliator/unsave/{product_id}")
def unsave_product(product_id: str):
    """Remove a product from saved products (affiliator endpoint)"""
    success = db_ops.unsave_product(product_id)
    
    if success:
        return create_success_response(message="Product unsaved successfully")
    else:
        return create_error_response("Product not found in saved list")

@router.delete("/unsave/{product_id}")
def unsave_product_simple_by_id(product_id: str):
    """Remove a product from saved products by ID"""
    success = db_ops.unsave_product(product_id)
    
    if success:
        return create_success_response(message="Product removed successfully")
    else:
        return create_error_response("Product not found")

@router.get("/saved")
def get_saved_products(
    q: Optional[str] = Query(None, description="Search query"),
    sort: str = Query("saved_at_desc", pattern="^(saved_at_desc|saved_at_asc|title_asc|title_desc)$"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
):
    """Get saved products with pagination and search"""
    try:
        page, page_size = validate_pagination_params(page, pageSize)
        
        rows, total = db_ops.get_saved_products(
            page=page,
            page_size=page_size,
            search_query=q,
            sort=sort
        )
        
        return {
            "items": rows,
            "page": page,
            "pageSize": page_size,
            "hasMore": len(rows) >= page_size,
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get saved products: {str(e)}")

@router.post("/update-description")
def update_product_description(update_data: UpdateProductDescription):
    """Update product description/title"""
    try:
        success = db_ops.update_product_title(
            update_data.product_id,
            update_data.custom_description
        )
        
        if success:
            return create_success_response(
                data={"product_id": update_data.product_id},
                message="Product description updated successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Product not found in saved products")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update description: {str(e)}")

@router.post("/ensure-unique-constraint")
def ensure_unique_constraint():
    """Ensure unique constraint on product_id in saved_products table"""
    result = db_ops.ensure_unique_constraint()
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

@router.get("/check/{product_id}")
def check_product_exists(product_id: str):
    """Check if a product exists in saved products"""
    try:
        with db_ops.db.get_cursor() as (cursor, connection):
            cursor.execute("SELECT product_id FROM saved_products WHERE product_id = %s", (product_id,))
            exists = cursor.fetchone() is not None
            
            return {
                "exists": exists,
                "product_id": product_id,
                "message": "Product exists" if exists else "Product not found"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check product: {str(e)}")

@router.get("/info/{product_id}")
def get_product_info(product_id: str):
    """Get detailed information about a saved product"""
    try:
        with db_ops.db.get_cursor() as (cursor, connection):
            cursor.execute("""
                SELECT product_id, product_title, custom_title, saved_at, has_video 
                FROM saved_products 
                WHERE product_id = %s
            """, (product_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "product_id": result[0],
                    "product_title": result[1],
                    "custom_title": result[2],
                    "saved_at": result[3].isoformat() if result[3] else None,
                    "has_video": bool(result[4]),
                    "exists": True
                }
            else:
                return {
                    "exists": False,
                    "product_id": product_id,
                    "message": "Product not found"
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product info: {str(e)}")

@router.put("/save")
def update_product(p: SaveProduct):
    """Update an existing product in the database"""
    try:
        # Convert Pydantic model to dict
        product_data = p.dict()
        
        # Update in database
        success = db_ops.save_product(product_data)
        
        if success:
            return create_success_response(message="Product updated successfully")
        else:
            raise HTTPException(status_code=500, detail="Failed to update product")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")

@router.get("/products")
def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Page size"),
):
    """Get products for homepage (no search query)"""
    # Return sample products for homepage
    sample_products = [
        {
            "product_id": "1005001234567890",
            "product_title": "📱 Smartphone - 128GB Storage",
            "product_main_image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop&crop=center",
            "sale_price": 199.99,
            "sale_price_currency": "USD",
            "original_price": 299.99,
            "original_price_currency": "USD",
            "lastest_volume": 1200,
            "rating_weighted": 4.5,
            "first_level_category_id": "100001",
            "promotion_link": "https://example.com/phone",
            "commission_rate": 8.0,
            "discount": 33,
            "saved_at": None
        },
        {
            "product_id": "1005001234567891",
            "product_title": "💻 Laptop - 16GB RAM, 512GB SSD",
            "product_main_image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&h=400&fit=crop&crop=center",
            "sale_price": 799.99,
            "sale_price_currency": "USD",
            "original_price": 1199.99,
            "original_price_currency": "USD",
            "lastest_volume": 450,
            "rating_weighted": 4.8,
            "first_level_category_id": "100002",
            "promotion_link": "https://example.com/laptop",
            "commission_rate": 10.0,
            "discount": 33,
            "saved_at": None
        },
        {
            "product_id": "1005001234567892",
            "product_title": "⌚ Smart Watch - Fitness Tracker",
            "product_main_image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop&crop=center",
            "sale_price": 149.99,
            "sale_price_currency": "USD",
            "original_price": 249.99,
            "original_price_currency": "USD",
            "lastest_volume": 890,
            "rating_weighted": 4.6,
            "first_level_category_id": "100003",
            "promotion_link": "https://example.com/watch",
            "commission_rate": 12.0,
            "discount": 40,
            "saved_at": None
        }
    ]
    
    # Apply pagination
    start_index = (page - 1) * pageSize
    end_index = start_index + pageSize
    paginated_products = sample_products[start_index:end_index]
    
    return {
        "items": paginated_products,
        "page": page,
        "pageSize": pageSize,
        "total": len(sample_products),
        "hasMore": end_index < len(sample_products),
        "method": "products_homepage",
        "source": "sample_data"
    }

@router.get("/demo-simple")
def demo_products_simple():
    """Get demo products for testing"""
    # Return empty demo products for now
    return {
        "items": [],
        "page": 1,
        "pageSize": 0,
        "hasMore": False,
        "total": 0,
        "method": "demo_products",
        "source": "demo_data",
        "demo_mode": True
    }

