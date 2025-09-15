#!/usr/bin/env python3
"""
Production startup script for Alibee Affiliate API
"""
import os
import sys
import uvicorn

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Get port from environment (Render provides PORT environment variable)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Start the application
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        workers=1,  # Single worker for Render free tier
        access_log=True,
        reload=False  # No reload in production
    )
