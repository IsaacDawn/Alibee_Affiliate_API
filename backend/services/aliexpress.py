import hashlib
import hmac
import time
import requests
from typing import Dict, Any, List, Optional
from config.settings import settings

class AliExpressClient:
    """Client for AliExpress API"""
    
    def __init__(self):
        self.app_key = settings.APP_KEY
        self.app_secret = settings.APP_SECRET
        self.base_url = settings.ALIEXPRESS_BASE_URL
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate TOP MD5 signature for API request (like PHP version)"""
        # Sort parameters and remove empty values
        clean_params = {}
        for k, v in params.items():
            if v is not None and v != '':
                clean_params[k] = v
        
        # Sort by key
        sorted_params = sorted(clean_params.items())
        
        # Build signature string: secret + concat(params) + secret
        base = self.app_secret
        for k, v in sorted_params:
            base += k + str(v)
        base += self.app_secret
        
        # Generate MD5 hash and convert to uppercase
        signature = hashlib.md5(base.encode('utf-8')).hexdigest().upper()
        
        return signature
    
    def _make_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a request to AliExpress API"""
        try:
            if not self.app_key or not self.app_secret:
                print("AliExpress API not configured")
                return None
            
            # System parameters (like PHP version)
            sys_params = {
                'app_key': self.app_key,
                'method': method,
                'format': 'json',
                'v': '2.0',
                'sign_method': 'md5',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                'partner_id': 'apidoc'
            }
            
            # Merge with request parameters
            all_params = {**sys_params, **params}
            
            # Generate signature
            signature = self._generate_signature(all_params)
            all_params['sign'] = signature
            
            # Make request
            response = requests.get(self.base_url, params=all_params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"Error making AliExpress request: {e}")
            return None
    
    def search_products(self, 
                       keywords: str = None,
                       category_ids: str = None,
                       page: int = 1,
                       page_size: int = 20,
                       sort: str = None,
                       min_price: float = None,
                       max_price: float = None,
                       has_video: bool = None) -> Optional[Dict[str, Any]]:
        """Search products using AliExpress API"""
        
        params = {
            'page_no': page,
            'page_size': page_size,
            'target_currency': 'USD',
            'target_language': 'EN',
            'trackingId': 'Alibee',
            'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating,rating_percent,positive_feedback_rate,avg_evaluation_rate,avg_rating_percent,product_description,promotion_link'
        }
        
        # Only add sort if provided
        if sort:
            params['sort'] = sort
        
        if keywords:
            params['keywords'] = keywords
        if category_ids:
            params['category_ids'] = category_ids
        if min_price:
            params['min_price'] = min_price
        if max_price:
            params['max_price'] = max_price
        if has_video is not None:
            params['has_video'] = has_video
        
        return self._make_request('aliexpress.affiliate.product.query', params)
    
    def get_hot_products(self,
                        keywords: str = None,
                        category_ids: str = None,
                        page: int = 1,
                        page_size: int = 20,
                        sort: str = None) -> Optional[Dict[str, Any]]:
        """Get hot products (Today's Deals) from AliExpress API"""
        
        params = {
            'page_no': page,
            'page_size': page_size,
            'target_currency': 'USD',
            'target_language': 'EN',
            'trackingId': 'Alibee',
            'fields': 'product_id,product_title,original_price,sale_price,sale_price_currency,target_original_price,target_sale_price,target_sale_price_currency,product_detail_url,product_main_image_url,product_small_image_urls,discount,commission_rate,hot_product_commission_rate,first_level_category_id,first_level_category_name,second_level_category_id,second_level_category_name,shop_id,shop_name,shop_url,product_video_url,sku_id,lastest_volume,app_sale_price,target_app_sale_price,target_app_sale_price_currency,evaluate_rate,rating_weighted,rating,score,average_rating,rating_percent,positive_feedback_rate,avg_evaluation_rate,avg_rating_percent,product_description,promotion_link'
        }
        
        # Only add sort if provided
        if sort:
            params['sort'] = sort
        
        if keywords:
            params['keywords'] = keywords
        if category_ids:
            params['category_ids'] = category_ids
        
        return self._make_request('aliexpress.affiliate.hotproduct.query', params)
    
    def generate_affiliate_link(self, urls: List[str]) -> Optional[Dict[str, Any]]:
        """Generate affiliate links for product URLs"""
        
        params = {
            'source_values': ','.join(urls),
            'promotion_link_type': '1'
        }
        
        return self._make_request('aliexpress.affiliate.link.generate', params)

class AliExpressService:
    """Service class for AliExpress operations"""
    
    def __init__(self):
        self.client = AliExpressClient()
    
    def normalize_product_items(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize product items from AliExpress API response"""
        try:
            if not raw_data:
                return []
            
            # Direct parsing of AliExpress response structure
            products = None
            
            # Structure: aliexpress_affiliate_product_query_response -> resp_result -> result -> products -> product
            if 'aliexpress_affiliate_product_query_response' in raw_data:
                resp = raw_data['aliexpress_affiliate_product_query_response']
                if 'resp_result' in resp and 'result' in resp['resp_result']:
                    result = resp['resp_result']['result']
                    if 'products' in result and 'product' in result['products']:
                        products = result['products']['product']
            
            if not products:
                return []
            
            # Handle both single product and array of products
            items = []
            if isinstance(products, list):
                items = products
            elif isinstance(products, dict):
                if 'product' in products:
                    product_data = products['product']
                    if isinstance(product_data, list):
                        items = product_data
                    else:
                        items = [product_data]
                else:
                    items = [products]
            else:
                items = [products]
            
            # Normalize items
            normalized_items = []
            for item in items:
                    try:
                        # Debug: Log raw rating data
                        raw_rating = item.get('rating_weighted')
                        print(f"🌟 Raw rating from AliExpress API: {raw_rating} (type: {type(raw_rating)})")
                        
                        # Helper function to safely convert rating fields
                        def safe_rating_convert(value):
                            if not value or str(value).strip() == '':
                                return None
                            try:
                                return float(str(value).replace('%', ''))
                            except:
                                return None
                        
                        # Helper function to safely convert percentage fields
                        def safe_percentage_convert(value):
                            if not value or str(value).strip() == '':
                                return None
                            try:
                                return float(str(value).replace('%', ''))
                            except:
                                return None
                        
                        # Helper function to get product score stars from percentage
                        def get_score_stars(score_str):
                            if not score_str or not isinstance(score_str, str):
                                return None
                            s = score_str.strip()
                            if s.endswith("%"):
                                try:
                                    return round((float(s[:-1]) / 100.0) * 5.0, 2)
                                except:
                                    return None
                            return None
                        
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
                            'rating_weighted': safe_rating_convert(item.get('rating_weighted')),
                            'first_level_category_id': item.get('first_level_category_id', ''),
                            'promotion_link': item.get('promotion_link', ''),
                            'commission_rate': safe_percentage_convert(item.get('commission_rate')),
                            'discount': safe_percentage_convert(item.get('discount')),
                            'saved_at': None,
                            # Enhanced fields from demo pattern
                            'product_description': item.get('product_description', ''),
                            'shop_title': item.get('shop_name', ''),
                            'shop_url': item.get('shop_url', ''),
                            'product_detail_url': item.get('product_detail_url', ''),
                            'product_small_image_urls': item.get('product_small_image_urls', []),
                            'first_level_category_name': item.get('first_level_category_name', ''),
                            'second_level_category_name': item.get('second_level_category_name', ''),
                            'evaluate_rate': item.get('evaluate_rate', ''),
                            'rating_percent': item.get('rating_percent', ''),
                            'positive_feedback_rate': item.get('positive_feedback_rate', ''),
                            'avg_evaluation_rate': item.get('avg_evaluation_rate', ''),
                            'avg_rating_percent': item.get('avg_rating_percent', ''),
                            'product_score': item.get('evaluate_rate') or item.get('rating_percent') or item.get('positive_feedback_rate') or item.get('avg_evaluation_rate') or item.get('avg_rating_percent'),
                            'product_score_stars': get_score_stars(item.get('evaluate_rate') or item.get('rating_percent') or item.get('positive_feedback_rate') or item.get('avg_evaluation_rate') or item.get('avg_rating_percent')),
                            'product_category': item.get('second_level_category_name') or item.get('first_level_category_name'),
                            'images_link': item.get('product_small_image_urls', []),
                            'video_link': item.get('product_video_url', ''),
                            'original_currency': item.get('original_price_currency', 'USD')
                        }
                        normalized_items.append(normalized_item)
                    except Exception as e:
                        print(f"Error normalizing product item: {e}")
                        continue
            
            return normalized_items
            
        except Exception as e:
            print(f"Error normalizing product items: {e}")
            return []
    
    def search_products_with_filters(self,
                                   query: str = None,
                                   page: int = 1,
                                   page_size: int = 20,
                                   hot: bool = False,
                                   sort: str = None,
                                   min_price: float = None,
                                   max_price: float = None,
                                   has_video: bool = None) -> Dict[str, Any]:
        """Search products using only keywords - simplified search"""
        
        # Use only the search query as keywords
        final_keywords = query if query and query.strip() else None
        
        # Choose method based on hot flag
        if hot:
            result = self.client.get_hot_products(
                keywords=final_keywords,
                page=page,
                page_size=page_size,
                sort=sort
            )
        else:
            result = self.client.search_products(
                keywords=final_keywords,
                page=page,
                page_size=page_size,
                sort=sort,
                min_price=min_price,
                max_price=max_price,
                has_video=has_video
            )
        
        if not result:
            return {
                'items': [],
                'page': page,
                'pageSize': page_size,
                'hasMore': False,
                'method': 'aliexpress.affiliate.product.query' if not hot else 'aliexpress.affiliate.hotproduct.query',
                'source': 'aliexpress_api',
                'error': 'API request failed'
            }
        
        # Normalize items
        items = self.normalize_product_items(result)
        
        # If no items, try direct parsing
        if not items and result:
            try:
                resp = result.get('aliexpress_affiliate_product_query_response', {})
                if resp:
                    resp_result = resp.get('resp_result', {})
                    if resp_result:
                        inner_result = resp_result.get('result', {})
                        if inner_result:
                            products = inner_result.get('products', {})
                            if products:
                                product_list = products.get('product', [])
                                if product_list:
                                    items = []
                                    for item in product_list:
                                        try:
                                            # Helper functions for safe conversion
                                            def safe_rating_convert(value):
                                                if not value or str(value).strip() == '':
                                                    return None
                                                try:
                                                    return float(str(value).replace('%', ''))
                                                except:
                                                    return None
                                            
                                            def safe_percentage_convert(value):
                                                if not value or str(value).strip() == '':
                                                    return None
                                                try:
                                                    return float(str(value).replace('%', ''))
                                                except:
                                                    return None
                                            
                                            def get_score_stars(score_str):
                                                if not score_str or not isinstance(score_str, str):
                                                    return None
                                                s = score_str.strip()
                                                if s.endswith("%"):
                                                    try:
                                                        return round((float(s[:-1]) / 100.0) * 5.0, 2)
                                                    except:
                                                        return None
                                                return None
                                            
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
                                                'rating_weighted': safe_rating_convert(item.get('rating_weighted')),
                                                'first_level_category_id': item.get('first_level_category_id', ''),
                                                'promotion_link': item.get('promotion_link', ''),
                                                'commission_rate': safe_percentage_convert(item.get('commission_rate')),
                                                'discount': safe_percentage_convert(item.get('discount')),
                                                'saved_at': None,
                                                # Enhanced fields from demo pattern
                                                'product_description': item.get('product_description', ''),
                                                'shop_title': item.get('shop_name', ''),
                                                'shop_url': item.get('shop_url', ''),
                                                'product_detail_url': item.get('product_detail_url', ''),
                                                'product_small_image_urls': item.get('product_small_image_urls', []),
                                                'first_level_category_name': item.get('first_level_category_name', ''),
                                                'second_level_category_name': item.get('second_level_category_name', ''),
                                                'evaluate_rate': item.get('evaluate_rate', ''),
                                                'rating_percent': item.get('rating_percent', ''),
                                                'positive_feedback_rate': item.get('positive_feedback_rate', ''),
                                                'avg_evaluation_rate': item.get('avg_evaluation_rate', ''),
                                                'avg_rating_percent': item.get('avg_rating_percent', ''),
                                                'product_score': item.get('evaluate_rate') or item.get('rating_percent') or item.get('positive_feedback_rate') or item.get('avg_evaluation_rate') or item.get('avg_rating_percent'),
                                                'product_score_stars': get_score_stars(item.get('evaluate_rate') or item.get('rating_percent') or item.get('positive_feedback_rate') or item.get('avg_evaluation_rate') or item.get('avg_rating_percent')),
                                                'product_category': item.get('second_level_category_name') or item.get('first_level_category_name'),
                                                'images_link': item.get('product_small_image_urls', []),
                                                'video_link': item.get('product_video_url', ''),
                                                'original_currency': item.get('original_price_currency', 'USD')
                                            }
                                            items.append(normalized_item)
                                        except Exception as e:
                                            print(f"Error normalizing product item: {e}")
                                            continue
            except Exception as e:
                print(f"Error in direct parsing: {e}")
        
        return {
            'items': items,
            'page': page,
            'pageSize': page_size,
            'hasMore': len(items) >= page_size,
            'method': 'aliexpress.affiliate.product.query' if not hot else 'aliexpress.affiliate.hotproduct.query',
            'source': 'aliexpress_api',
            'total': len(items)
        }

# Create global AliExpress service instance
aliexpress_service = AliExpressService()