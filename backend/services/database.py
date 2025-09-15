# Database service layer
import mysql.connector
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from backend.config.database import DB_CONFIG, TABLES
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.config = DB_CONFIG

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            connection = mysql.connector.connect(**self.config)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection:
                connection.close()

    def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = None
                
                return result
            finally:
                cursor.close()

    def execute_update(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.rowcount
            finally:
                cursor.close()

    def upsert_product(self, product_data: Dict[str, Any]) -> bool:
        """Insert or update a product in the database"""
        query = f"""
        INSERT INTO {TABLES['PRODUCTS']} (
            product_id, product_title, product_main_image_url, product_video_url,
            sale_price, sale_price_currency, original_price, original_price_currency,
            lastest_volume, rating_weighted, first_level_category_id, promotion_link
        ) VALUES (
            %(product_id)s, %(product_title)s, %(product_main_image_url)s, %(product_video_url)s,
            %(sale_price)s, %(sale_price_currency)s, %(original_price)s, %(original_price_currency)s,
            %(lastest_volume)s, %(rating_weighted)s, %(first_level_category_id)s, %(promotion_link)s
        ) ON DUPLICATE KEY UPDATE
            product_title = VALUES(product_title),
            product_main_image_url = VALUES(product_main_image_url),
            product_video_url = VALUES(product_video_url),
            sale_price = VALUES(sale_price),
            sale_price_currency = VALUES(sale_price_currency),
            original_price = VALUES(original_price),
            original_price_currency = VALUES(original_price_currency),
            lastest_volume = VALUES(lastest_volume),
            rating_weighted = VALUES(rating_weighted),
            first_level_category_id = VALUES(first_level_category_id),
            promotion_link = VALUES(promotion_link),
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            affected_rows = self.execute_update(query, product_data)
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Error upserting product: {e}")
            return False

    def get_products(
        self, 
        filters: Dict[str, Any], 
        page: int = 1, 
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Get products with filters and pagination"""
        offset = (page - 1) * page_size
        
        # Build WHERE clause
        where_conditions = ["1=1"]
        params = []
        
        if filters.get('q'):
            where_conditions.append("product_title LIKE %s")
            params.append(f"%{filters['q']}%")
        
        if filters.get('categoryId'):
            where_conditions.append("first_level_category_id = %s")
            params.append(filters['categoryId'])
        
        if filters.get('hasVideo'):
            where_conditions.append("product_video_url IS NOT NULL AND product_video_url <> ''")
        
        # Build ORDER BY clause
        sort_options = {
            'volume_desc': 'lastest_volume DESC',
            'discount_desc': 'discount DESC',
            'rating_desc': 'rating_weighted DESC',
        }
        order_by = sort_options.get(filters.get('sort', 'volume_desc'), 'lastest_volume DESC')
        
        query = f"""
        SELECT product_id, product_title, product_main_image_url, product_video_url,
               sale_price, sale_price_currency, original_price, original_price_currency,
               lastest_volume, rating_weighted, first_level_category_id, promotion_link,
               saved_at, fetched_at
        FROM {TABLES['PRODUCTS']}
        WHERE {' AND '.join(where_conditions)}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
        """
        
        params.extend([page_size, offset])
        results = self.execute_query(query, tuple(params))
        
        # Check if there are more results
        has_more = len(results) == page_size if results else False
        
        return results or [], has_more

    def save_product(self, product_id: str, product_data: Dict[str, Any]) -> bool:
        """Save a product to saved_products table"""
        query = f"""
        INSERT INTO {TABLES['SAVED_PRODUCTS']} (
            product_id, product_title, product_main_image_url, product_video_url,
            sale_price, sale_price_currency, original_price, original_price_currency,
            lastest_volume, rating_weighted, first_level_category_id, promotion_link
        ) VALUES (
            %(product_id)s, %(product_title)s, %(product_main_image_url)s, %(product_video_url)s,
            %(sale_price)s, %(sale_price_currency)s, %(original_price)s, %(original_price_currency)s,
            %(lastest_volume)s, %(rating_weighted)s, %(first_level_category_id)s, %(promotion_link)s
        ) ON DUPLICATE KEY UPDATE
            product_title = VALUES(product_title),
            product_main_image_url = VALUES(product_main_image_url),
            product_video_url = VALUES(product_video_url),
            sale_price = VALUES(sale_price),
            sale_price_currency = VALUES(sale_price_currency),
            original_price = VALUES(original_price),
            original_price_currency = VALUES(original_price_currency),
            lastest_volume = VALUES(lastest_volume),
            rating_weighted = VALUES(rating_weighted),
            first_level_category_id = VALUES(first_level_category_id),
            promotion_link = VALUES(promotion_link),
            saved_at = CURRENT_TIMESTAMP
        """
        
        try:
            affected_rows = self.execute_update(query, product_data)
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Error saving product: {e}")
            return False

    def unsave_product(self, product_id: str) -> bool:
        """Remove a product from saved_products table"""
        query = f"DELETE FROM {TABLES['SAVED_PRODUCTS']} WHERE product_id = %s"
        
        try:
            affected_rows = self.execute_update(query, (product_id,))
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Error unsaving product: {e}")
            return False

    def get_saved_products_count(self) -> int:
        """Get count of saved products"""
        query = f"SELECT COUNT(*) as count FROM {TABLES['SAVED_PRODUCTS']}"
        result = self.execute_query(query, fetch_one=True)
        return result['count'] if result else 0

    def get_total_products_count(self) -> int:
        """Get count of total products"""
        query = f"SELECT COUNT(*) as count FROM {TABLES['PRODUCTS']}"
        result = self.execute_query(query, fetch_one=True)
        return result['count'] if result else 0

    def get_saved_products_for_items(self, product_ids: List[str]) -> Dict[str, str]:
        """Get saved_at timestamps for given product IDs"""
        if not product_ids:
            return {}
        
        placeholders = ','.join(['%s'] * len(product_ids))
        query = f"""
        SELECT product_id, saved_at
        FROM {TABLES['SAVED_PRODUCTS']}
        WHERE product_id IN ({placeholders})
        """
        
        results = self.execute_query(query, tuple(product_ids))
        return {row['product_id']: row['saved_at'] for row in results} if results else {}

# Export singleton instance
db_service = DatabaseService()
