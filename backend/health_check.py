#!/usr/bin/env python3
"""
Health check script to verify API endpoints are working
"""

import requests
import sys
import os

def health_check():
    """Check if the API is healthy"""
    base_url = os.getenv('API_BASE_URL', 'https://alibee-affiliate-api.onrender.com')
    
    print(f"🏥 Health checking API at: {base_url}")
    
    # Test critical endpoints
    endpoints = [
        "/health",
        "/categories", 
        "/check/1005009233542451"
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            return False
    
    print("🎉 All health checks passed!")
    return True

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
