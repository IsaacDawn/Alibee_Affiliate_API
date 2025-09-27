#!/usr/bin/env python3
"""
Migration script to update saved_products table schema
This script updates the saved_products table to match the expected schema
"""

import mysql.connector
from config.settings import settings
import sys

def migrate_saved_products():
    """Migrate saved_products table to new schema"""
    try:
        # Get database configuration
        db_config = settings.get_database_config()
        
        # Connect to database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        print("🔄 Starting saved_products table migration...")
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'saved_products'")
        if not cursor.fetchone():
            print("❌ saved_products table does not exist. Creating new table...")
            
            # Create new table with correct schema
            create_table_sql = """
            CREATE TABLE saved_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id VARCHAR(255) NOT NULL UNIQUE,
                product_title TEXT,
                promotion_link TEXT,
                product_category VARCHAR(50),
                custom_title TEXT,
                has_video BOOLEAN DEFAULT FALSE,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_product_id (product_id),
                INDEX idx_category (product_category),
                INDEX idx_saved_at (saved_at),
                INDEX idx_created_at (created_at)
            )
            """
            cursor.execute(create_table_sql)
            print("✅ Created new saved_products table")
        else:
            print("📋 saved_products table exists. Checking schema...")
            
            # Check current columns
            cursor.execute("DESCRIBE saved_products")
            columns = [row[0] for row in cursor.fetchall()]
            print(f"Current columns: {columns}")
            
            # Add missing columns
            required_columns = {
                'product_title': 'TEXT',
                'promotion_link': 'TEXT', 
                'product_category': 'VARCHAR(50)',
                'custom_title': 'TEXT',
                'has_video': 'BOOLEAN DEFAULT FALSE',
                'saved_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
            }
            
            for column_name, column_def in required_columns.items():
                if column_name not in columns:
                    print(f"➕ Adding column: {column_name}")
                    try:
                        cursor.execute(f"ALTER TABLE saved_products ADD COLUMN {column_name} {column_def}")
                    except mysql.connector.Error as e:
                        if e.errno == 1060:  # Duplicate column name
                            print(f"⚠️  Column {column_name} already exists")
                        else:
                            raise
            
            # Add unique constraint on product_id if it doesn't exist
            try:
                cursor.execute("ALTER TABLE saved_products ADD UNIQUE KEY unique_product_id (product_id)")
                print("✅ Added unique constraint on product_id")
            except mysql.connector.Error as e:
                if e.errno == 1061:  # Duplicate key name
                    print("⚠️  Unique constraint on product_id already exists")
                else:
                    raise
            
            # Add indexes if they don't exist
            indexes_to_add = [
                ("idx_category", "product_category"),
                ("idx_saved_at", "saved_at"),
                ("idx_created_at", "created_at")
            ]
            
            for index_name, column in indexes_to_add:
                try:
                    cursor.execute(f"CREATE INDEX {index_name} ON saved_products ({column})")
                    print(f"✅ Added index: {index_name}")
                except mysql.connector.Error as e:
                    if e.errno == 1061:  # Duplicate key name
                        print(f"⚠️  Index {index_name} already exists")
                    else:
                        raise
        
        # Commit changes
        connection.commit()
        print("✅ Migration completed successfully!")
        
        # Verify final schema
        cursor.execute("DESCRIBE saved_products")
        final_columns = cursor.fetchall()
        print("\n📋 Final saved_products table schema:")
        for column in final_columns:
            print(f"  {column[0]} - {column[1]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if connection:
            connection.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    migrate_saved_products()
