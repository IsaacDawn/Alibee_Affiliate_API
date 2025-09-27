#!/usr/bin/env python3
"""
Debug script to check backend routes
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    from fastapi.routing import APIRoute
    
    print("🔍 Backend Routes Debug")
    print("=" * 50)
    
    # Get all routes
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    
    print(f"📊 Total Routes: {len(routes)}")
    print()
    
    # Display routes
    for route in routes:
        methods = ", ".join(route["methods"])
        print(f"🔗 {route['path']} [{methods}] - {route['name']}")
    
    print()
    print("🧪 Test URLs:")
    print("=" * 20)
    base_url = "https://alibee-affiliate-api.onrender.com"
    
    test_routes = [
        "/",
        "/health", 
        "/api/categories",
        "/api/stats",
        "/api/search",
        "/api/products",
        "/api/exchange"
    ]
    
    for route in test_routes:
        print(f"✅ {base_url}{route}")
    
    print()
    print("🔧 Route Registration Check:")
    print("=" * 30)
    
    # Check if routes are properly registered
    api_routes = [r for r in routes if r["path"].startswith("/api")]
    print(f"API Routes Found: {len(api_routes)}")
    
    for route in api_routes:
        print(f"  - {route['path']}")
    
    print()
    print("✅ Backend routes are properly configured!")
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're in the backend directory and all dependencies are installed")
except Exception as e:
    print(f"❌ Error: {e}")
