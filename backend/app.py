# backend/app_new.py
"""
Alibee Affiliator API - Modular Version
This is the new modular version of the application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from routes import api_router

# Create FastAPI application
app = FastAPI(
    title="Alibee Affiliator API",
    description="Modular AliExpress Affiliate API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    **settings.get_cors_config()
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Alibee Affiliator API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "API is running",
        "version": "2.0.0"
    }

# Additional endpoints that might be needed
@app.get("/demo")
def demo_products():
    """Demo products endpoint for backward compatibility"""
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

@app.get("/products")
def list_products():
    """List products endpoint for backward compatibility"""
    # This would need to be implemented based on your specific requirements
    return {
        "items": [],
        "page": 1,
        "pageSize": 20,
        "hasMore": False,
        "total": 0,
        "message": "This endpoint needs to be implemented based on your requirements"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
