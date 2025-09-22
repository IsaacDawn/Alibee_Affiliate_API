"""
Real Rating Service - دریافت ریت‌های واقعی از AliExpress
"""

import requests
import re
import time
import random
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import json

class RealRatingService:
    """سرویس دریافت ریت‌های واقعی از AliExpress"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def get_product_rating_from_url(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        دریافت ریت واقعی از URL محصول AliExpress
        
        Args:
            product_url (str): لینک محصول
            
        Returns:
            Dict: اطلاعات ریت شامل rating, review_count, etc.
        """
        try:
            print(f"🔍 Fetching real rating from: {product_url}")
            
            # اضافه کردن تاخیر تصادفی برای جلوگیری از بلاک شدن
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # استخراج ریت از HTML
            rating_info = self._extract_rating_from_html(soup)
            
            if rating_info:
                print(f"✅ Found real rating: {rating_info}")
                return rating_info
            else:
                print("❌ No rating found in HTML")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching rating: {str(e)}")
            return None
    
    def _extract_rating_from_html(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        استخراج ریت از HTML صفحه محصول
        
        Args:
            soup (BeautifulSoup): HTML parsed soup
            
        Returns:
            Dict: اطلاعات ریت
        """
        try:
            rating_info = {}
            
            # روش 1: جستجو برای ریت در meta tags
            rating_meta = soup.find('meta', {'property': 'og:rating'})
            if rating_meta:
                rating_info['rating'] = float(rating_meta.get('content', 0))
            
            # روش 2: جستجو برای ریت در JSON-LD
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'aggregateRating' in data:
                        agg_rating = data['aggregateRating']
                        rating_info['rating'] = float(agg_rating.get('ratingValue', 0))
                        rating_info['review_count'] = int(agg_rating.get('reviewCount', 0))
                        break
                except:
                    continue
            
            # روش 3: جستجو برای ریت در کلاس‌های CSS
            rating_elements = soup.find_all(['span', 'div'], class_=re.compile(r'rating|star|score', re.I))
            for element in rating_elements:
                text = element.get_text().strip()
                # جستجو برای الگوهای ریت مثل "4.5", "4.5/5", "4.5 out of 5"
                rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*5', text)
                if rating_match:
                    rating_info['rating'] = float(rating_match.group(1))
                    break
            
            # روش 4: جستجو برای تعداد نظرات
            review_elements = soup.find_all(['span', 'div'], class_=re.compile(r'review|comment', re.I))
            for element in review_elements:
                text = element.get_text().strip()
                # جستجو برای الگوهای تعداد نظرات
                review_match = re.search(r'(\d+(?:,\d+)*)\s*(?:reviews?|comments?)', text, re.I)
                if review_match:
                    review_count = int(review_match.group(1).replace(',', ''))
                    rating_info['review_count'] = review_count
                    break
            
            return rating_info if rating_info else None
            
        except Exception as e:
            print(f"❌ Error extracting rating from HTML: {str(e)}")
            return None
    
    def get_rating_from_product_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        دریافت ریت از product_id
        
        Args:
            product_id (str): شناسه محصول
            
        Returns:
            Dict: اطلاعات ریت
        """
        try:
            # ساخت URL محصول
            product_url = f"https://www.aliexpress.com/item/{product_id}.html"
            return self.get_product_rating_from_url(product_url)
        except Exception as e:
            print(f"❌ Error getting rating for product {product_id}: {str(e)}")
            return None
    
    def batch_get_ratings(self, product_ids: list, delay: float = 2.0) -> Dict[str, Dict[str, Any]]:
        """
        دریافت ریت‌های چندین محصول
        
        Args:
            product_ids (list): لیست شناسه محصولات
            delay (float): تاخیر بین درخواست‌ها
            
        Returns:
            Dict: ریت‌های محصولات
        """
        ratings = {}
        
        for i, product_id in enumerate(product_ids):
            print(f"📦 Processing product {i+1}/{len(product_ids)}: {product_id}")
            
            rating = self.get_rating_from_product_id(product_id)
            if rating:
                ratings[product_id] = rating
            
            # تاخیر بین درخواست‌ها
            if i < len(product_ids) - 1:
                time.sleep(delay)
        
        return ratings

# نمونه سراسری
real_rating_service = RealRatingService()

