# backend/routes/products.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from models.schemas import SaveProduct, UpdateProductDescription
from database.connection import db_ops
from utils.helpers import get_demo_products, validate_pagination_params, create_success_response, create_error_response

router = APIRouter()

@router.post("/save")
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

@router.get("/demo-simple")
def demo_products_simple():
    """Get demo products for testing"""
    demo_products = get_demo_products()
    
    return {
        "items": demo_products,
        "page": 1,
        "pageSize": len(demo_products),
        "hasMore": False,
        "total": len(demo_products),
        "method": "demo_products",
        "source": "demo_data",
        "demo_mode": True
    }
