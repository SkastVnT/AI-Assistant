-- Sample ClickHouse Schema for E-commerce Database
-- Database: ecommerce_db

-- Users Table
CREATE TABLE users (
    user_id UInt32,
    username String,
    email String,
    full_name String,
    phone String,
    date_of_birth Date,
    country String,
    city String,
    registration_date DateTime,
    last_login DateTime,
    is_active UInt8,
    total_spent Decimal(12,2)
) ENGINE = MergeTree()
ORDER BY user_id;

-- Products Table
CREATE TABLE products (
    product_id UInt32,
    product_name String,
    category String,
    brand String,
    price Decimal(10,2),
    cost Decimal(10,2),
    stock_quantity UInt32,
    description String,
    rating Float32,
    reviews_count UInt32,
    created_date DateTime,
    updated_date DateTime,
    is_available UInt8
) ENGINE = MergeTree()
ORDER BY product_id;

-- Orders Table
CREATE TABLE orders (
    order_id UInt32,
    user_id UInt32,
    order_date DateTime,
    total_amount Decimal(12,2),
    discount_amount Decimal(10,2),
    tax_amount Decimal(10,2),
    shipping_cost Decimal(10,2),
    final_amount Decimal(12,2),
    payment_method String,
    order_status String,
    shipping_address String,
    tracking_number String,
    delivery_date DateTime
) ENGINE = MergeTree()
ORDER BY order_date;

-- Order Items Table
CREATE TABLE order_items (
    order_item_id UInt32,
    order_id UInt32,
    product_id UInt32,
    quantity UInt32,
    unit_price Decimal(10,2),
    discount Decimal(10,2),
    subtotal Decimal(10,2)
) ENGINE = MergeTree()
ORDER BY order_id;

-- Reviews Table
CREATE TABLE reviews (
    review_id UInt32,
    product_id UInt32,
    user_id UInt32,
    rating UInt8,
    review_text String,
    review_date DateTime,
    helpful_count UInt32,
    verified_purchase UInt8
) ENGINE = MergeTree()
ORDER BY review_date;

-- Categories Table
CREATE TABLE categories (
    category_id UInt32,
    category_name String,
    parent_category_id UInt32,
    description String,
    is_active UInt8
) ENGINE = MergeTree()
ORDER BY category_id;

-- Sample Queries Examples:
-- 1. Top selling products: SELECT product_id, SUM(quantity) FROM order_items GROUP BY product_id ORDER BY SUM(quantity) DESC
-- 2. Monthly revenue: SELECT toMonth(order_date), SUM(final_amount) FROM orders GROUP BY toMonth(order_date)
-- 3. User spending: SELECT user_id, SUM(final_amount) FROM orders GROUP BY user_id ORDER BY SUM(final_amount) DESC
