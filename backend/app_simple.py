"""
Simple Alibee Affiliator API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import hashlib
import time
import json
import asyncio
from services.currency_service import currency_service

# AliExpress API Configuration
ALI_APP_KEY = "514064"
ALI_APP_SECRET = "p8rJNLXoolmZKskeUrshCCbs45y4eWS9"
ALI_BASE_URL = "https://api-sg.aliexpress.com/sync"

def _get_product_rating(item):
    """Get product rating from evaluate_rate field or return null"""
    product_id = item.get('product_id', '')
    product_title = item.get('product_title', '')
    
    # Debug: Log evaluate_rate from AliExpress API
    print(f"🔍 Rating Debug for Product {product_id}:")
    print(f"   - evaluate_rate: {item.get('evaluate_rate', 'NOT_FOUND')} (type: {type(item.get('evaluate_rate'))})")
    
    # Handle evaluate_rate (percentage) - convert to 5-star rating
    evaluate_rate = item.get('evaluate_rate')
    if evaluate_rate and str(evaluate_rate).strip() != '' and str(evaluate_rate) != '0.0%':
        try:
            # Remove % and convert to float
            rate_str = str(evaluate_rate).replace('%', '').strip()
            rate_float = float(rate_str)
            
            # Skip if rate is 0
            if rate_float == 0:
                print(f"   ⚠️ evaluate_rate is 0%, returning null")
                return None
            
            # Convert percentage to 5-star rating (94% = 4.7 stars)
            converted_rating = round((rate_float / 100) * 5, 1)
            print(f"   ✅ Converted evaluate_rate {evaluate_rate} to rating: {converted_rating}")
            return converted_rating
        except (ValueError, TypeError):
            print(f"   ❌ Failed to convert evaluate_rate: {evaluate_rate}")
            pass
    
    # If no valid evaluate_rate found, return null to show "No rate"
    print(f"   ⚠️ No valid evaluate_rate found for product: {product_title[:50]}... - returning null")
    return None

def generate_signature(params):
    """Generate TOP MD5 signature for API request"""
    clean_params = {}
    for k, v in params.items():
        if v is not None and v != '':
            clean_params[k] = v
    
    sorted_params = sorted(clean_params.items())
    
    base = ALI_APP_SECRET
    for k, v in sorted_params:
        base += k + str(v)
    base += ALI_APP_SECRET
    
    signature = hashlib.md5(base.encode('utf-8')).hexdigest().upper()
    return signature

def get_super_deals(page=1, page_size=20):
    """Get Super Deals from AliExpress API"""
    try:
        # System parameters for Super Deals
        sys_params = {
            'app_key': ALI_APP_KEY,
            'method': 'aliexpress.affiliate.featuredpromo.products.get',
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'partner_id': 'apidoc'
        }
        
        # Business parameters for Super Deals
        biz_params = {
            'page_no': page,
            'page_size': page_size,
            'target_currency': 'USD',
            'target_language': 'EN',
            'trackingId': 'Alibee',
            'promotion_type': 'SUPER_DEALS',  # Specify Super Deals
            'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating'
        }
        
        # Combine all parameters
        all_params = {**sys_params, **biz_params}
        
        # Generate signature
        signature = generate_signature(all_params)
        all_params['sign'] = signature
        
        # Make request
        response = requests.get(ALI_BASE_URL, params=all_params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"💎 Super Deals API Response: {json.dumps(data, indent=2)[:500]}...")
        print(f"💎 Super Deals Promotion Type: {biz_params['promotion_type']}")
        
        # Parse response
        products = []
        if 'aliexpress_affiliate_featuredpromo_products_get_response' in data:
            resp = data['aliexpress_affiliate_featuredpromo_products_get_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    product_data = result['products']['product']
                    
                    # Handle both single product and array
                    if isinstance(product_data, list):
                        products = product_data
                    elif isinstance(product_data, dict):
                        products = [product_data]
        
        # Normalize products
        normalized_products = []
        for item in products:
            # Log rating from AliExpress API
            print(f"🔍 AliExpress API Rating for {item.get('product_id', 'unknown')}:")
            print(f"   - rating_weighted: {item.get('rating_weighted', 'NOT_FOUND')} (type: {type(item.get('rating_weighted'))})")
            print(f"   - rating: {item.get('rating', 'NOT_FOUND')} (type: {type(item.get('rating'))})")
            print(f"   - score: {item.get('score', 'NOT_FOUND')} (type: {type(item.get('score'))})")
            print(f"   - average_rating: {item.get('average_rating', 'NOT_FOUND')} (type: {type(item.get('average_rating'))})")
            print(f"   - evaluate_rate: {item.get('evaluate_rate', 'NOT_FOUND')} (type: {type(item.get('evaluate_rate'))})")
            try:
                normalized_item = {
                    'product_id': item.get('product_id', ''),
                    'product_title': item.get('product_title', ''),
                    'product_main_image_url': item.get('product_main_image_url', ''),
                    'product_video_url': item.get('product_video_url', ''),
                    'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                    'sale_price_currency': item.get('sale_price_currency', 'USD'),
                    'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                    'original_price_currency': item.get('original_price_currency', 'USD'),
                    'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                    'rating_weighted': _get_product_rating(item),
                    'rating': float(item.get('rating', 0)) if item.get('rating') and str(item.get('rating')).strip() != '' else None,
                    'score': float(item.get('score', 0)) if item.get('score') and str(item.get('score')).strip() != '' else None,
                    'average_rating': float(item.get('average_rating', 0)) if item.get('average_rating') and str(item.get('average_rating')).strip() != '' else None,
                    'evaluate_rate': item.get('evaluate_rate', ''),
                    'first_level_category_id': item.get('first_level_category_id', ''),
                    'promotion_link': item.get('promotion_link', ''),
                    'commission_rate': float(str(item.get('commission_rate', 0)).replace('%', '')) if item.get('commission_rate') else 0,
                    'discount': int(str(item.get('discount', 0)).replace('%', '')) if item.get('discount') else 0,
                    'saved_at': None
                }
                normalized_products.append(normalized_item)
            except Exception as e:
                print(f"Error normalizing super deal product: {e}")
                continue
        
        return normalized_products
        
    except Exception as e:
        print(f"Error calling Super Deals API: {e}")
        return []

def get_hot_products(page=1, page_size=20):
    """Get Hot Products from AliExpress API"""
    try:
        # System parameters for hot products
        sys_params = {
            'app_key': ALI_APP_KEY,
            'method': 'aliexpress.affiliate.hotproduct.query',
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'partner_id': 'apidoc'
        }
        
        # Business parameters for hot products
        biz_params = {
            'page_no': page,
            'page_size': page_size,
            'target_currency': 'USD',
            'target_language': 'EN',
            'trackingId': 'Alibee',
            'keywords': 'electronics phone laptop fashion clothing shoes home beauty sports toys automotive jewelry watch camera tablet',
            'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating'
        }
        
        # Combine all parameters
        all_params = {**sys_params, **biz_params}
        
        # Generate signature
        signature = generate_signature(all_params)
        all_params['sign'] = signature
        
        # Make request
        response = requests.get(ALI_BASE_URL, params=all_params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"🔥 Hot Products API Response: {json.dumps(data, indent=2)[:500]}...")
        print(f"🔥 Hot Products Keywords: {biz_params['keywords']}")
        
        # Parse response
        products = []
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            resp = data['aliexpress_affiliate_hotproduct_query_response']
            if 'result' in resp and 'products' in resp['result']:
                products = resp['result']['products']
            elif 'result' in resp and 'product' in resp['result']:
                # Handle single product response
                product_data = resp['result']['product']
                if isinstance(product_data, dict):
                    products = [product_data]
        
        # Normalize products
        normalized_products = []
        for item in products:
            # Log rating from AliExpress API
            print(f"🔍 AliExpress API Rating for {item.get('product_id', 'unknown')}:")
            print(f"   - rating_weighted: {item.get('rating_weighted', 'NOT_FOUND')} (type: {type(item.get('rating_weighted'))})")
            print(f"   - rating: {item.get('rating', 'NOT_FOUND')} (type: {type(item.get('rating'))})")
            print(f"   - score: {item.get('score', 'NOT_FOUND')} (type: {type(item.get('score'))})")
            print(f"   - average_rating: {item.get('average_rating', 'NOT_FOUND')} (type: {type(item.get('average_rating'))})")
            print(f"   - evaluate_rate: {item.get('evaluate_rate', 'NOT_FOUND')} (type: {type(item.get('evaluate_rate'))})")
            try:
                normalized_item = {
                    'product_id': item.get('product_id', ''),
                    'product_title': item.get('product_title', ''),
                    'product_main_image_url': item.get('product_main_image_url', ''),
                    'product_video_url': item.get('product_video_url', ''),
                    'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                    'sale_price_currency': item.get('sale_price_currency', 'USD'),
                    'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                    'original_price_currency': item.get('original_price_currency', 'USD'),
                    'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                    'rating_weighted': _get_product_rating(item),
                    'rating': float(item.get('rating', 0)) if item.get('rating') and str(item.get('rating')).strip() != '' else None,
                    'score': float(item.get('score', 0)) if item.get('score') and str(item.get('score')).strip() != '' else None,
                    'average_rating': float(item.get('average_rating', 0)) if item.get('average_rating') and str(item.get('average_rating')).strip() != '' else None,
                    'evaluate_rate': item.get('evaluate_rate', ''),
                    'first_level_category_id': item.get('first_level_category_id', ''),
                    'promotion_link': item.get('promotion_link', ''),
                    'commission_rate': float(str(item.get('commission_rate', 0)).replace('%', '')) if item.get('commission_rate') else 0,
                    'discount': int(str(item.get('discount', 0)).replace('%', '')) if item.get('discount') else 0,
                    'saved_at': None
                }
                normalized_products.append(normalized_item)
            except Exception as e:
                print(f"Error normalizing hot product: {e}")
                continue
        
        print(f"✅ Found {len(normalized_products)} Hot Products from AliExpress API")
        return normalized_products
        
    except Exception as e:
        print(f"Error calling Hot Products API: {e}")
        return []

def get_todays_deals(page=1, page_size=20):
    """Get Today's Deals from AliExpress API"""
    try:
        # System parameters for hot products (Today's Deals)
        sys_params = {
            'app_key': ALI_APP_KEY,
            'method': 'aliexpress.affiliate.product.query',
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'partner_id': 'apidoc'
        }
        
        # Random keywords for diverse products
        import random
        keyword_sets = [
            'phone smartphone mobile',
            'laptop computer notebook',
            'fashion clothing dress',
            'shoes sneakers boots',
            'home garden furniture',
            'beauty cosmetics skincare',
            'sports fitness gym',
            'toys games children',
            'jewelry watch accessories',
            'camera photography',
            'tablet ipad android',
            'kitchen cooking utensils',
            'electronics gadgets tech',
            'health wellness supplements',
            'books stationery office'
        ]
        
        # Select random keywords for variety
        selected_keywords = random.choice(keyword_sets)
        
        # Business parameters for hot products
        biz_params = {
            'page_no': page,
            'page_size': page_size,
            'target_currency': 'USD',  # Force USD to get AliExpress rates
            'target_language': 'EN',
            'trackingId': 'Alibee',
            'keywords': selected_keywords
        }
        
        # Combine all parameters
        all_params = {**sys_params, **biz_params}
        
        # Generate signature
        signature = generate_signature(all_params)
        all_params['sign'] = signature
        
        # Make request
        response = requests.get(ALI_BASE_URL, params=all_params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"🔥 Today's Deals API Response: {json.dumps(data, indent=2)[:500]}...")
        print(f"🔥 Today's Deals Selected Keywords: {selected_keywords}")
        print(f"🔥 Today's Deals All Keywords: {biz_params['keywords']}")
        
        # Parse response
        products = []
        if 'aliexpress_affiliate_product_query_response' in data:
            resp = data['aliexpress_affiliate_product_query_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    product_data = result['products']['product']
                    
                    # Handle both single product and array
                    if isinstance(product_data, list):
                        products = product_data
                    elif isinstance(product_data, dict):
                        products = [product_data]
        
        # Normalize products
        normalized_products = []
        for item in products:
            # Log rating from AliExpress API
            print(f"🔍 AliExpress API Rating for {item.get('product_id', 'unknown')}:")
            print(f"   - rating_weighted: {item.get('rating_weighted', 'NOT_FOUND')} (type: {type(item.get('rating_weighted'))})")
            print(f"   - rating: {item.get('rating', 'NOT_FOUND')} (type: {type(item.get('rating'))})")
            print(f"   - score: {item.get('score', 'NOT_FOUND')} (type: {type(item.get('score'))})")
            print(f"   - average_rating: {item.get('average_rating', 'NOT_FOUND')} (type: {type(item.get('average_rating'))})")
            print(f"   - evaluate_rate: {item.get('evaluate_rate', 'NOT_FOUND')} (type: {type(item.get('evaluate_rate'))})")
            try:
                normalized_item = {
                    'product_id': item.get('product_id', ''),
                    'product_title': item.get('product_title', ''),
                    'product_main_image_url': item.get('product_main_image_url', ''),
                    'product_video_url': item.get('product_video_url', ''),
                    'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                    'sale_price_currency': item.get('sale_price_currency', 'USD'),
                    'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                    'original_price_currency': item.get('original_price_currency', 'USD'),
                    'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                    'rating_weighted': _get_product_rating(item),
                    'rating': float(item.get('rating', 0)) if item.get('rating') and str(item.get('rating')).strip() != '' else None,
                    'score': float(item.get('score', 0)) if item.get('score') and str(item.get('score')).strip() != '' else None,
                    'average_rating': float(item.get('average_rating', 0)) if item.get('average_rating') and str(item.get('average_rating')).strip() != '' else None,
                    'evaluate_rate': item.get('evaluate_rate', ''),
                    'first_level_category_id': item.get('first_level_category_id', ''),
                    'promotion_link': item.get('promotion_link', ''),
                    'commission_rate': float(str(item.get('commission_rate', 0)).replace('%', '')) if item.get('commission_rate') else 0,
                    'discount': int(str(item.get('discount', 0)).replace('%', '')) if item.get('discount') else 0,
                    'saved_at': None
                }
                normalized_products.append(normalized_item)
            except Exception as e:
                print(f"Error normalizing hot product: {e}")
                continue
        
        return normalized_products
        
    except Exception as e:
        print(f"Error calling Today's Deals API: {e}")
        return []

def get_product_details(product_ids):
    """Get detailed product information using productdetail.get API"""
    try:
        # System parameters
        sys_params = {
            'app_key': ALI_APP_KEY,
            'method': 'aliexpress.affiliate.productdetail.get',
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'partner_id': 'apidoc'
        }
        
        # Business parameters
        biz_params = {
            'product_ids': product_ids,
            'target_currency': 'USD',
            'target_language': 'EN',
            'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating'
        }
        
        # Combine all parameters
        all_params = {**sys_params, **biz_params}
        
        # Generate signature
        signature = generate_signature(all_params)
        all_params['sign'] = signature
        
        # Make request
        response = requests.get(ALI_BASE_URL, params=all_params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"🔍 Product Detail API Response: {json.dumps(data, indent=2)[:1000]}...")
        
        # Parse response
        products = []
        if 'aliexpress_affiliate_productdetail_get_response' in data:
            resp = data['aliexpress_affiliate_productdetail_get_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    product_data = result['products']['product']
                    
                    # Handle both single product and array
                    if isinstance(product_data, list):
                        products = product_data
                    elif isinstance(product_data, dict):
                        products = [product_data]
        
        # Log detailed rating information
        for item in products:
            print(f"\n🌟 DETAILED RATING INFO for Product {item.get('product_id', 'unknown')}:")
            print(f"   Raw API Response Keys: {list(item.keys())}")
            
            # Check all possible rating fields
            rating_fields = ['rating_weighted', 'rating', 'score', 'average_rating', 'evaluate_rate']
            for field in rating_fields:
                value = item.get(field)
                print(f"   - {field}: {value} (type: {type(value)})")
            
            # Check for any field containing 'rating' or 'score'
            for key, value in item.items():
                if 'rating' in key.lower() or 'score' in key.lower() or 'evaluate' in key.lower():
                    print(f"   - {key}: {value} (type: {type(value)})")
        
        return products
        
    except Exception as e:
        print(f"Error calling Product Detail API: {e}")
        return []

def search_aliexpress_products(query=None, page=1, page_size=20):
    """Search products from AliExpress API"""
    try:
        # System parameters
        sys_params = {
            'app_key': ALI_APP_KEY,
            'method': 'aliexpress.affiliate.product.query',
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            'partner_id': 'apidoc'
        }
        
        # Business parameters
        biz_params = {
            'page_no': page,
            'page_size': page_size,
            'target_currency': 'USD',
            'target_language': 'EN',
            'trackingId': 'Alibee',
            'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating'
        }
        
        if query:
            biz_params['keywords'] = query
        
        # Combine all parameters
        all_params = {**sys_params, **biz_params}
        
        # Generate signature
        signature = generate_signature(all_params)
        all_params['sign'] = signature
        
        # Make request
        response = requests.get(ALI_BASE_URL, params=all_params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"🌟 AliExpress API Response: {json.dumps(data, indent=2)[:500]}...")
        
        # Parse response
        products = []
        if 'aliexpress_affiliate_product_query_response' in data:
            resp = data['aliexpress_affiliate_product_query_response']
            if 'resp_result' in resp and 'result' in resp['resp_result']:
                result = resp['resp_result']['result']
                if 'products' in result and 'product' in result['products']:
                    product_data = result['products']['product']
                    
                    # Handle both single product and array
                    if isinstance(product_data, list):
                        products = product_data
                    elif isinstance(product_data, dict):
                        products = [product_data]
        
        # Normalize products
        normalized_products = []
        for item in products:
            # Log rating from AliExpress API
            print(f"🔍 AliExpress API Rating for {item.get('product_id', 'unknown')}:")
            print(f"   - rating_weighted: {item.get('rating_weighted', 'NOT_FOUND')} (type: {type(item.get('rating_weighted'))})")
            print(f"   - rating: {item.get('rating', 'NOT_FOUND')} (type: {type(item.get('rating'))})")
            print(f"   - score: {item.get('score', 'NOT_FOUND')} (type: {type(item.get('score'))})")
            print(f"   - average_rating: {item.get('average_rating', 'NOT_FOUND')} (type: {type(item.get('average_rating'))})")
            print(f"   - evaluate_rate: {item.get('evaluate_rate', 'NOT_FOUND')} (type: {type(item.get('evaluate_rate'))})")
            try:
                normalized_item = {
                    'product_id': item.get('product_id', ''),
                    'product_title': item.get('product_title', ''),
                    'product_main_image_url': item.get('product_main_image_url', ''),
                    'product_video_url': item.get('product_video_url', ''),
                    'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                    'sale_price_currency': item.get('sale_price_currency', 'USD'),
                    'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                    'original_price_currency': item.get('original_price_currency', 'USD'),
                    'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                    'rating_weighted': _get_product_rating(item),
                    'rating': float(item.get('rating', 0)) if item.get('rating') and str(item.get('rating')).strip() != '' else None,
                    'score': float(item.get('score', 0)) if item.get('score') and str(item.get('score')).strip() != '' else None,
                    'average_rating': float(item.get('average_rating', 0)) if item.get('average_rating') and str(item.get('average_rating')).strip() != '' else None,
                    'evaluate_rate': item.get('evaluate_rate', ''),
                    'first_level_category_id': item.get('first_level_category_id', ''),
                    'promotion_link': item.get('promotion_link', ''),
                    'commission_rate': float(str(item.get('commission_rate', 0)).replace('%', '')) if item.get('commission_rate') else 0,
                    'discount': int(str(item.get('discount', 0)).replace('%', '')) if item.get('discount') else 0,
                    'saved_at': None
                }
                normalized_products.append(normalized_item)
            except Exception as e:
                print(f"Error normalizing product: {e}")
                continue
        
        return normalized_products
        
    except Exception as e:
        print(f"Error calling AliExpress API: {e}")
        return []

# Create FastAPI application
app = FastAPI(
    title="Alibee Affiliator API",
    description="AliExpress Affiliate API with CurrencyFreaks integration",
    version="1.0.0"
)

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include real ratings routes
from routes.real_ratings import router as real_ratings_router
app.include_router(real_ratings_router, prefix="/api", tags=["Real Ratings"])

# Background task for currency updates
async def currency_update_task():
    """Background task to update currency rates every hour"""
    while True:
        try:
            await asyncio.sleep(3600)  # Wait 1 hour
            print("🔄 Background: Updating currency rates...")
            await currency_service._update_rates_from_api()
            print("✅ Background: Currency rates updated successfully")
        except Exception as e:
            print(f"❌ Background: Error updating currency rates: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize currency service on startup"""
    print("🚀 Starting Alibee Affiliator API with CurrencyFreaks...")
    
    # Initialize currency service
    await currency_service._update_rates_from_api()
    print("✅ Currency service initialized")
    
    # Start background task
    asyncio.create_task(currency_update_task())
    print("✅ Background currency update task started")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Alibee Affiliator API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is working"}

# Simple endpoints for testing
@app.get("/stats")
async def get_stats():
    return {
        "total_products": 0,
        "total_categories": 0,
        "api_status": "working"
    }

@app.get("/categories")
async def get_categories():
    return {
        "categories": [
            {"id": "100001", "name": "Electronics", "keywords": "electronics gadgets"},
            {"id": "100002", "name": "Fashion", "keywords": "fashion clothing"},
            {"id": "100003", "name": "Home & Garden", "keywords": "home garden"},
            {"id": "100004", "name": "Sports & Outdoor", "keywords": "sports outdoor"},
            {"id": "100005", "name": "Beauty & Health", "keywords": "beauty health"},
            {"id": "100006", "name": "Automotive", "keywords": "automotive"},
            {"id": "100007", "name": "Toys & Hobbies", "keywords": "toys hobbies"},
            {"id": "100008", "name": "Jewelry & Accessories", "keywords": "jewelry accessories"},
            {"id": "100009", "name": "Shoes & Bags", "keywords": "shoes bags"},
            {"id": "100010", "name": "Computer & Office", "keywords": "computer office"},
            {"id": "100011", "name": "Musical Instruments", "keywords": "musical instruments"}
        ],
        "message": "Categories retrieved successfully"
    }

@app.get("/debug-categories")
async def debug_categories():
    """Debug endpoint to see actual category IDs from AliExpress API"""
    try:
        # Get some products to see their category IDs
        products = get_todays_deals(1, 5)
        
        category_ids = {}
        for product in products:
            cat_id = product.get('first_level_category_id')
            cat_name = product.get('first_level_category_name', 'Unknown')
            product_title = product.get('product_title', 'Unknown')[:50]
            
            if cat_id:
                if cat_id not in category_ids:
                    category_ids[cat_id] = {
                        'id': cat_id,
                        'name': cat_name,
                        'products': []
                    }
                category_ids[cat_id]['products'].append(product_title)
        
        return {
            "status": "success",
            "message": "Category IDs from AliExpress API",
            "categories": list(category_ids.values()),
            "total_categories": len(category_ids)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to debug categories: {str(e)}",
            "categories": []
        }

@app.get("/aliexpress-rates")
async def get_aliexpress_rates():
    """Get AliExpress exchange rates by comparing product prices"""
    try:
        # Get a sample product to extract AliExpress rates
        products = get_todays_deals(page=1, page_size=1)
        
        if products and len(products) > 0:
            product = products[0]
            
            # Extract AliExpress rates from product data
            sale_price_cny = float(product.get('sale_price', 0))
            original_price_cny = float(product.get('original_price', 0))
            
            # If we have CNY prices, we can calculate the rate
            if sale_price_cny > 0:
                # This is AliExpress's internal rate
                # We can use this to calibrate our rates
                print(f"📊 AliExpress Product Sample: {sale_price_cny} CNY")
                
                return {
                    "aliexpress_sample_cny": sale_price_cny,
                    "aliexpress_sample_original_cny": original_price_cny,
                    "note": "Use this data to calibrate exchange rates",
                    "product_id": product.get('product_id'),
                    "product_title": product.get('product_title', '')[:50] + '...'
                }
        
        return {"error": "No products found to extract rates"}
        
    except Exception as e:
        print(f"❌ Error getting AliExpress rates: {e}")
        return {"error": str(e)}

@app.get("/rate-comparison")
async def compare_rates():
    """Compare our rates with AliExpress rates"""
    try:
        # Get our current rates
        our_rates = await get_exchange_rates("CNY")
        
        # Get AliExpress sample
        aliexpress_data = await get_aliexpress_rates()
        
        return {
            "our_rates": our_rates,
            "aliexpress_sample": aliexpress_data,
            "recommendation": "Adjust CNY rate to match AliExpress pricing"
        }
        
    except Exception as e:
        print(f"❌ Error comparing rates: {e}")
        return {"error": str(e)}

@app.get("/exchange-rates")
async def get_exchange_rates(
    base_currency: str = "USD"
):
    """Get exchange rates for currency conversion using CurrencyFreaks API"""
    try:
        # Use CurrencyFreaks service
        rates = await currency_service.get_exchange_rates(base_currency)
        
        print(f"✅ Exchange rates from CurrencyFreaks: {rates}")
        return rates
        
    except Exception as e:
        print(f"❌ Error getting exchange rates: {e}")
        # Final fallback with AliExpress-compatible rates
        return {
            "CNY": 0.1406,  # AliExpress rate (1 CNY = 0.1406 USD, 1/7.11)
            "EUR": 0.85,    # Adjusted proportionally
            "GBP": 0.73,    # Adjusted proportionally  
            "JPY": 110.0    # Adjusted proportionally
        }

@app.get("/currency-info")
async def get_currency_info():
    """Get information about currency service and cache"""
    try:
        cache_info = currency_service.get_cache_info()
        return {
            "status": "success",
            "currency_service": cache_info,
            "message": "Currency service information retrieved successfully"
        }
    except Exception as e:
        print(f"❌ Error getting currency info: {e}")
        return {"error": str(e)}

@app.post("/currency-refresh")
async def refresh_currency_rates():
    """Manually refresh currency rates from CurrencyFreaks API"""
    try:
        await currency_service._update_rates_from_api()
        cache_info = currency_service.get_cache_info()
        return {
            "status": "success",
            "message": "Currency rates refreshed successfully",
            "cache_info": cache_info
        }
    except Exception as e:
        print(f"❌ Error refreshing currency rates: {e}")
        return {"error": str(e)}

@app.get("/convert-currency")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str
):
    """Convert amount from one currency to another"""
    try:
        converted_amount = currency_service.convert_amount(amount, from_currency, to_currency)
        rate = currency_service.get_rate(from_currency, to_currency)
        
        return {
            "original_amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "converted_amount": round(converted_amount, 2),
            "exchange_rate": round(rate, 6),
            "cache_info": currency_service.get_cache_info()
        }
    except Exception as e:
        print(f"❌ Error converting currency: {e}")
        return {"error": str(e)}

@app.get("/currency-file")
async def get_currency_file():
    """Get the content of currency rates cache file"""
    try:
        import os
        import json
        
        cache_file = "currency_rates_cache.json"
        
        if not os.path.exists(cache_file):
            return {
                "status": "error",
                "message": f"Cache file {cache_file} not found",
                "file_exists": False
            }
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        return {
            "status": "success",
            "file_path": cache_file,
            "file_exists": True,
            "content": file_content,
            "message": "Currency rates cache file content retrieved successfully"
        }
        
    except Exception as e:
        print(f"❌ Error reading currency file: {e}")
        return {"error": str(e)}

@app.get("/super-deals")
async def get_super_deals_endpoint(
    page: int = 1,
    pageSize: int = 20
):
    """Get Super Deals from AliExpress"""
    print(f"💎 Getting Super Deals: page={page}, pageSize={pageSize}")
    
    # Call Super Deals API
    products = get_super_deals(
        page=page,
        page_size=pageSize
    )
    
    print(f"✅ Found {len(products)} Super Deals from AliExpress API")
    
    return {
        "items": products,
        "page": page,
        "pageSize": pageSize,
        "hasMore": len(products) == pageSize,  # Assume more if we got full page
        "method": "aliexpress.affiliate.featuredpromo.products.get",
        "source": "aliexpress_super_deals",
        "live": True
    }

@app.get("/todays-deals")
async def get_todays_deals_endpoint(
    page: int = 1,
    pageSize: int = 20
):
    """Get Today's Deals from AliExpress"""
    print(f"🔥 Getting Today's Deals: page={page}, pageSize={pageSize}")
    
    # Call Today's Deals API
    products = get_todays_deals(
        page=page,
        page_size=pageSize
    )
    
    print(f"✅ Found {len(products)} Today's Deals from AliExpress API")
    
    return {
        "items": products,
        "page": page,
        "pageSize": pageSize,
        "hasMore": len(products) == pageSize,  # Assume more if we got full page
        "method": "aliexpress.affiliate.product.query",
        "source": "aliexpress_todays_deals",
        "live": True
    }

@app.get("/diverse-products")
async def get_diverse_products(
    page: int = 1,
    pageSize: int = 10
):
    """Get diverse products from multiple categories"""
    print(f"🌈 Getting diverse products: page={page}, pageSize={pageSize}")
    
    # Try different keyword sets to get diverse products
    keyword_sets = [
        'phone smartphone mobile',
        'laptop computer notebook',
        'fashion clothing dress',
        'shoes sneakers boots',
        'home garden furniture',
        'beauty cosmetics skincare',
        'sports fitness gym',
        'toys games children',
        'automotive car accessories',
        'jewelry watch accessories',
        'camera photography',
        'tablet ipad android'
    ]
    
    all_products = []
    products_per_keyword = max(1, pageSize // len(keyword_sets))
    
    for keywords in keyword_sets:
        try:
            # System parameters
            sys_params = {
                'app_key': ALI_APP_KEY,
                'method': 'aliexpress.affiliate.product.query',
                'format': 'json',
                'v': '2.0',
                'sign_method': 'md5',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                'partner_id': 'apidoc'
            }
            
            # Business parameters
            biz_params = {
                'page_no': 1,
                'page_size': products_per_keyword,
                'target_currency': 'USD',
                'target_language': 'EN',
                'trackingId': 'Alibee',
                'keywords': keywords,
                'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating'
            }
            
            # Combine all parameters
            all_params = {**sys_params, **biz_params}
            
            # Generate signature
            signature = generate_signature(all_params)
            all_params['sign'] = signature
            
            # Make request
            response = requests.get(ALI_BASE_URL, params=all_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print(f"🌈 {keywords} API Response: {json.dumps(data, indent=2)[:200]}...")
            
            # Parse response
            products = []
            if 'aliexpress_affiliate_product_query_response' in data:
                resp = data['aliexpress_affiliate_product_query_response']
                if 'resp_result' in resp and 'result' in resp['resp_result']:
                    result = resp['resp_result']['result']
                    if 'products' in result:
                        products_data = result['products']
                        if isinstance(products_data, list):
                            products = products_data
                        elif isinstance(products_data, dict):
                            products = [products_data]
                        elif isinstance(products_data, str):
                            # If it's a string, try to parse it as JSON
                            try:
                                import json
                                parsed = json.loads(products_data)
                                if isinstance(parsed, list):
                                    products = parsed
                                elif isinstance(parsed, dict):
                                    products = [parsed]
                            except:
                                print(f"🌈 {keywords}: Could not parse products string: {products_data[:100]}...")
                        print(f"🌈 {keywords}: Found {len(products)} products in resp_result.result.products")
                    elif 'product' in result:
                        product_data = result['product']
                        if isinstance(product_data, dict):
                            products = [product_data]
                            print(f"🌈 {keywords}: Found 1 product in resp_result.result.product")
                elif 'result' in resp and 'products' in resp['result']:
                    products_data = resp['result']['products']
                    if isinstance(products_data, list):
                        products = products_data
                    elif isinstance(products_data, dict):
                        products = [products_data]
                    print(f"🌈 {keywords}: Found {len(products)} products in result.products")
                elif 'result' in resp and 'product' in resp['result']:
                    product_data = resp['result']['product']
                    if isinstance(product_data, dict):
                        products = [product_data]
                        print(f"🌈 {keywords}: Found 1 product in result.product")
                else:
                    print(f"🌈 {keywords}: No products found in response structure")
            else:
                print(f"🌈 {keywords}: No aliexpress_affiliate_product_query_response in data")
            
            # Normalize products
            for item in products:
                try:
                    normalized_item = {
                        'product_id': item.get('product_id', ''),
                        'product_title': item.get('product_title', ''),
                        'product_main_image_url': item.get('product_main_image_url', ''),
                        'product_video_url': item.get('product_video_url', ''),
                        'sale_price': float(item.get('sale_price', 0)) if item.get('sale_price') else 0,
                        'sale_price_currency': item.get('sale_price_currency', 'USD'),
                        'original_price': float(item.get('original_price', 0)) if item.get('original_price') else 0,
                        'original_price_currency': item.get('original_price_currency', 'USD'),
                        'lastest_volume': int(item.get('lastest_volume', 0)) if item.get('lastest_volume') else 0,
                        'rating_weighted': _get_product_rating(item),
                        'first_level_category_id': item.get('first_level_category_id', ''),
                        'promotion_link': item.get('promotion_link', ''),
                        'commission_rate': float(str(item.get('commission_rate', 0)).replace('%', '')) if item.get('commission_rate') else 0,
                        'discount': int(str(item.get('discount', 0)).replace('%', '')) if item.get('discount') else 0,
                        'saved_at': None
                    }
                    all_products.append(normalized_item)
                except Exception as e:
                    print(f"Error normalizing diverse product: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching products for {keywords}: {e}")
            continue
    
    # Shuffle products for variety
    import random
    random.shuffle(all_products)
    
    # Paginate results
    start_idx = (page - 1) * pageSize
    end_idx = start_idx + pageSize
    paginated_products = all_products[start_idx:end_idx]
    
    print(f"✅ Found {len(paginated_products)} diverse products from {len(all_products)} total")
    
    return {
        "items": paginated_products,
        "page": page,
        "pageSize": pageSize,
        "hasMore": len(all_products) > end_idx,
        "method": "aliexpress.affiliate.product.query",
        "source": "aliexpress_diverse_products",
        "live": True
    }

@app.get("/search")
async def search_products(
    q: str = None,
    page: int = 1,
    pageSize: int = 10,
    category: str = None
):
    # Use real AliExpress API
    print(f"🔍 Searching AliExpress API: query='{q}', page={page}, pageSize={pageSize}, category='{category}'")
    
    # If category is "all" or no specific search, use diverse products
    if (category == "all" or not category) and not q:
        print("🌈 Using diverse products for homepage")
        # Call the diverse products endpoint internally
        diverse_response = await get_diverse_products(page=page, pageSize=pageSize)
        products = diverse_response["items"]
        method = diverse_response["method"]
        source = diverse_response["source"]
    else:
        # Prepare search query for specific categories
        search_query = q
        if category and category != "all":
            category_keywords = {
                "100001": "electronics gadgets",
                "100002": "fashion clothing", 
                "100003": "home garden",
                "100004": "sports outdoor",
                "100005": "beauty health",
                "100006": "automotive",
                "100007": "toys hobbies",
                "100008": "jewelry accessories",
                "100009": "shoes bags",
                "100010": "computer office",
                "100011": "musical instruments"
            }
            if category in category_keywords:
                if search_query:
                    search_query = f"{search_query} {category_keywords[category]}"
                else:
                    search_query = category_keywords[category]
        
        # Call AliExpress API for search
        products = search_aliexpress_products(
            query=search_query,
            page=page,
            page_size=pageSize
        )
        method = "aliexpress.affiliate.product.query"
        source = "aliexpress_api"
    
    print(f"✅ Found {len(products)} real products from AliExpress API")
    
    return {
        "items": products,
        "page": page,
        "pageSize": pageSize,
        "hasMore": len(products) == pageSize,  # Assume more if we got full page
        "method": method,
        "source": source,
        "live": True
    }
