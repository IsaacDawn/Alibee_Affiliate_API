-- Alibee Affiliate Database Schema
-- MySQL Database Schema for AliExpress Product Management

CREATE DATABASE IF NOT EXISTS alibee_affiliate;
USE alibee_affiliate;

-- Main products table
CREATE TABLE IF NOT EXISTS aliexpress_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL UNIQUE,
    product_title TEXT NOT NULL,
    product_main_image_url TEXT,
    product_video_url TEXT,
    sale_price DECIMAL(10,2),
    sale_price_currency VARCHAR(10) DEFAULT 'USD',
    original_price DECIMAL(10,2),
    original_price_currency VARCHAR(10) DEFAULT 'USD',
    lastest_volume INT,
    rating_weighted DECIMAL(3,2),
    first_level_category_id VARCHAR(50),
    promotion_link TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_product_id (product_id),
    INDEX idx_category (first_level_category_id),
    INDEX idx_volume (lastest_volume),
    INDEX idx_rating (rating_weighted),
    INDEX idx_saved_at (saved_at),
    FULLTEXT idx_title (product_title)
);

-- Categories table for better organization
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id VARCHAR(50) NOT NULL UNIQUE,
    category_name VARCHAR(255) NOT NULL,
    parent_category_id VARCHAR(50),
    level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_category_id (category_id),
    INDEX idx_parent (parent_category_id)
);

-- Affiliate links tracking
CREATE TABLE IF NOT EXISTS affiliate_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    original_url TEXT NOT NULL,
    affiliate_url TEXT NOT NULL,
    clicks INT DEFAULT 0,
    conversions INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_product_id (product_id),
    INDEX idx_clicks (clicks),
    FOREIGN KEY (product_id) REFERENCES aliexpress_products(product_id) ON DELETE CASCADE
);

-- Search history for analytics
CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query VARCHAR(255) NOT NULL,
    results_count INT DEFAULT 0,
    user_ip VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_query (query),
    INDEX idx_created_at (created_at)
);

-- Product favorites/saved items
CREATE TABLE IF NOT EXISTS saved_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    user_session VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_product_id (product_id),
    INDEX idx_user_session (user_session),
    UNIQUE KEY unique_user_product (product_id, user_session),
    FOREIGN KEY (product_id) REFERENCES aliexpress_products(product_id) ON DELETE CASCADE
);

-- Insert some sample categories
INSERT IGNORE INTO categories (category_id, category_name, level) VALUES
('100001', 'Electronics', 1),
('100002', 'Watches & Jewelry', 1),
('100003', 'Phone Accessories', 1),
('100004', 'Home & Garden', 1),
('100005', 'Beauty & Health', 1),
('100006', 'Sports & Outdoors', 1),
('100007', 'Automotive', 1),
('100008', 'Toys & Games', 1),
('100009', 'Fashion', 1),
('100010', 'Tools & Hardware', 1);
