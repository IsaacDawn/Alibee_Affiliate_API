#!/usr/bin/env python
"""
Test Real Rating Service
"""

import asyncio
from services.real_rating_service import real_rating_service

async def test_real_rating():
    """تست سرویس دریافت ریت واقعی"""
    
    print("🧪 Testing Real Rating Service...")
    
    # تست با یک product_id واقعی
    test_product_id = "1005009897762509"  # از تست قبلی
    
    print(f"\n📦 Testing product ID: {test_product_id}")
    
    try:
        rating = real_rating_service.get_rating_from_product_id(test_product_id)
        
        if rating:
            print(f"✅ Real rating found:")
            print(f"   - Rating: {rating.get('rating', 'N/A')}")
            print(f"   - Review Count: {rating.get('review_count', 'N/A')}")
        else:
            print("❌ No rating found")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # تست با URL مستقیم
    print(f"\n🌐 Testing with direct URL...")
    test_url = f"https://www.aliexpress.com/item/{test_product_id}.html"
    
    try:
        rating = real_rating_service.get_product_rating_from_url(test_url)
        
        if rating:
            print(f"✅ Real rating from URL found:")
            print(f"   - Rating: {rating.get('rating', 'N/A')}")
            print(f"   - Review Count: {rating.get('review_count', 'N/A')}")
        else:
            print("❌ No rating found from URL")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_real_rating())

