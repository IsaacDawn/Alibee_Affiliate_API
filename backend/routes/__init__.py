# backend/routes/__init__.py
from fastapi import APIRouter
from .health import router as health_router
from .products import router as products_router
from .simple_search import router as simple_search_router
from .categories import router as categories_router
from .stats import router as stats_router
from .exchange import router as exchange_router

# Create main router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, tags=["health"])
api_router.include_router(products_router, tags=["products"])
api_router.include_router(simple_search_router, tags=["search"])
api_router.include_router(categories_router, tags=["categories"])
api_router.include_router(stats_router, tags=["stats"])
api_router.include_router(exchange_router, tags=["exchange"])

__all__ = ["api_router"]