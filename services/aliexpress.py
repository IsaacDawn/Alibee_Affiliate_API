# AliExpress API service
import os
import time
import hmac
import hashlib
import json
import requests
from typing import Dict, Any, List, Optional
from backend.config.settings import ALIEXPRESS_CONFIG
import logging

logger = logging.getLogger(__name__)

class AliExpressService:
    def __init__(self):
        self.app_key = ALIEXPRESS_CONFIG['APP_KEY']
        self.app_secret = ALIEXPRESS_CONFIG['APP_SECRET']
        self.base_url = ALIEXPRESS_CONFIG['BASE_URL']
        self.timeout = ALIEXPRESS_CONFIG['TIMEOUT']

    def _create_signature(self, params: Dict[str, Any]) -> str:
        """Create MD5 signature for AliExpress API"""
        if not self.app_secret:
            raise ValueError("APP_SECRET not configured")
        
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create base string
        base_string = self.app_secret
        for key, value in sorted_params:
            base_string += f"{key}{value}"
        base_string += self.app_secret
        
        # Create MD5 hash
        return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()

    def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to AliExpress API"""
        if not self.app_key or not self.app_secret:
            raise ValueError("AliExpress API credentials not configured")
        
        # Add common parameters
        params.update({
            'app_key': self.app_key,
            'timestamp': str(int(time.time() * 1000)),
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
        })
        
        # Create signature
        params['sign'] = self._create_signature(params)
        
        try:
            response = requests.post(
                f"{self.base_url}/{method}",
                data=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"AliExpress API request failed: {e}")
            raise

    def search_products(
        self,
        query: str = "phone",
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[str] = None,
        has_video: Optional[bool] = None,
        sort: str = "volume_desc"
    ) -> Dict[str, Any]:
        """Search products using AliExpress API"""
        params = {
            'method': 'aliexpress.affiliate.product.smartmatch',
            'keywords': query,
            'page_no': page,
            'page_size': page_size,
        }
        
        if category_id:
            params['category_ids'] = category_id
        
        if has_video:
            params['has_video'] = 'true'
        
        # Map sort options
        sort_mapping = {
            'volume_desc': 'SALE_PRICE_ASC',
            'discount_desc': 'DISCOUNT_DESC',
            'rating_desc': 'RATING_DESC',
        }
        params['sort'] = sort_mapping.get(sort, 'SALE_PRICE_ASC')
        
        return self._make_request('aliexpress.affiliate.product.smartmatch', params)

    def get_hot_products(
        self,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get hot/trending products"""
        params = {
            'method': 'aliexpress.affiliate.hotproduct.query',
            'page_no': page,
            'page_size': page_size,
        }
        
        if category_id:
            params['category_ids'] = category_id
        
        return self._make_request('aliexpress.affiliate.hotproduct.query', params)

    def normalize_products(self, raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize AliExpress API response to our format"""
        try:
            resp_data = raw_response.get('aliexpress_affiliate_product_smartmatch_response', {})
            result = resp_data.get('resp_result', {})
            
            if not result.get('result'):
                return []
            
            products = result['result'].get('products', {}).get('product', [])
            if not isinstance(products, list):
                products = [products]
            
            normalized = []
            for item in products:
                try:
                    # Extract product information
                    product_id = item.get('product_id', '')
                    title = item.get('product_title', '')
                    image_url = item.get('product_main_image_url', '')
                    video_url = item.get('product_video_url', '')
                    
                    # Price information
                    sale_price = float(item.get('target_sale_price', 0))
                    sale_currency = item.get('target_sale_price_currency', 'USD')
                    original_price = item.get('target_original_price')
                    original_currency = item.get('target_original_price_currency', 'USD')
                    
                    # Product metrics
                    volume = int(item.get('lastest_volume', 0))
                    rating = float(item.get('evaluate_rate', 0))
                    
                    # Category and promotion
                    category_id = item.get('first_level_category_id', '')
                    promotion_link = item.get('promotion_link', '')
                    
                    normalized_item = {
                        'product_id': product_id,
                        'product_title': title,
                        'product_main_image_url': image_url,
                        'product_video_url': video_url,
                        'sale_price': sale_price,
                        'sale_price_currency': sale_currency,
                        'original_price': float(original_price) if original_price else None,
                        'original_price_currency': original_currency,
                        'lastest_volume': volume,
                        'rating_weighted': rating,
                        'first_level_category_id': category_id,
                        'promotion_link': promotion_link,
                    }
                    
                    normalized.append(normalized_item)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error normalizing product item: {e}")
                    continue
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing products: {e}")
            return []

    def is_configured(self) -> bool:
        """Check if AliExpress API is properly configured"""
        return bool(self.app_key and self.app_secret)

# Export singleton instance
aliexpress_service = AliExpressService()
