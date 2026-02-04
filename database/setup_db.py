import sqlite3
import json
from datetime import datetime, timedelta

def create_databases():
    """Create and populate databases with enhanced product catalog and orders"""
    
    # ==================== ORDERS DATABASE ====================
    print("📦 Creating Orders Database...")
    conn = sqlite3.connect('database/orders.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            product TEXT,
            status TEXT,
            order_date TEXT,
            expected_delivery TEXT,
            tracking_number TEXT,
            price TEXT,
            quantity INTEGER DEFAULT 1
        )
    ''')
    
    # Enhanced sample orders with more variety
    orders = [
        ('12345', 'John Doe', 'iPhone 15 Pro', 'Shipped', '2025-11-01', '2025-11-15', 'TRK123456', '₹1,34,999', 1),
        ('ORD001', 'Jane Smith', 'Samsung Galaxy S24', 'Processing', '2025-11-05', '2025-11-18', 'TRK789012', '₹79,999', 1),
        ('98765', 'Bob Johnson', 'MacBook Air M2', 'Delivered', '2025-10-20', '2025-10-28', 'TRK345678', '₹99,990', 1),
        ('ORD002', 'Alice Williams', 'Sony WH-1000XM5', 'Shipped', '2025-11-03', '2025-11-16', 'TRK456789', '₹29,990', 2),
        ('ORD003', 'Charlie Brown', 'iPad Pro 12.9', 'Processing', '2025-11-08', '2025-11-20', 'TRK567890', '₹1,12,900', 1),
        ('ORD004', 'David Lee', 'Dell XPS 15', 'Shipped', '2025-11-02', '2025-11-14', 'TRK678901', '₹1,45,990', 1),
        ('ORD005', 'Emma Davis', 'AirPods Pro 2', 'Delivered', '2025-10-25', '2025-11-01', 'TRK789012', '₹24,900', 1),
        ('ORD006', 'Frank Miller', 'OnePlus 12', 'Shipped', '2025-11-04', '2025-11-17', 'TRK890123', '₹64,999', 1),
        ('ORD007', 'Grace Chen', 'Apple Watch Series 9', 'Processing', '2025-11-07', '2025-11-19', 'TRK901234', '₹41,900', 1),
        ('ORD008', 'Henry Wilson', 'Google Pixel 8 Pro', 'Shipped', '2025-11-06', '2025-11-18', 'TRK012345', '₹84,999', 1),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?)', orders)
    
    # Create returns table with more fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            return_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            reason TEXT,
            preferred_action TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            refund_amount TEXT,
            notes TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Orders Database created successfully!")
    
    # ==================== PRODUCTS DATABASE ====================
    print("\n🛍️ Creating Products Database...")
    conn = sqlite3.connect('database/products.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            price TEXT,
            stock TEXT,
            category TEXT,
            description TEXT,
            rating REAL,
            brand TEXT,
            warranty TEXT
        )
    ''')
    
    # Enhanced product catalog with more items
    products = [
        # Smartphones
        (1, 'iPhone 15 Pro', '₹1,34,999', 'In Stock', 'Smartphones', 
         'Latest Apple flagship with A17 Pro chip and titanium design', 4.8, 'Apple', '1 Year'),
        (2, 'Samsung Galaxy S24', '₹79,999', 'In Stock', 'Smartphones', 
         'Premium Android flagship with AI features', 4.7, 'Samsung', '1 Year'),
        (3, 'Redmi Note 12', '₹14,999', 'Limited Stock', 'Smartphones', 
         'Budget-friendly smartphone with 120Hz display', 4.3, 'Xiaomi', '1 Year'),
        (4, 'OnePlus 12', '₹64,999', 'In Stock', 'Smartphones', 
         'Flagship killer with Snapdragon 8 Gen 3', 4.6, 'OnePlus', '1 Year'),
        (5, 'Google Pixel 8 Pro', '₹84,999', 'In Stock', 'Smartphones', 
         'Best-in-class camera with Google Tensor G3', 4.7, 'Google', '1 Year'),
        (6, 'Vivo V30 Pro', '₹41,999', 'In Stock', 'Smartphones', 
         'Camera-focused phone with elegant design', 4.4, 'Vivo', '1 Year'),
        
        # Laptops
        (7, 'MacBook Air M2', '₹99,990', 'In Stock', 'Laptops', 
         'Ultra-thin laptop with Apple M2 chip', 4.9, 'Apple', '1 Year'),
        (8, 'Dell XPS 15', '₹1,45,990', 'In Stock', 'Laptops', 
         'Premium Windows laptop with InfinityEdge display', 4.6, 'Dell', '1 Year'),
        (9, 'HP Pavilion 15', '₹55,990', 'In Stock', 'Laptops', 
         'Value laptop for everyday computing', 4.2, 'HP', '1 Year'),
        (10, 'Lenovo ThinkPad X1', '₹1,25,990', 'Limited Stock', 'Laptops', 
         'Business-grade laptop with military durability', 4.7, 'Lenovo', '3 Years'),
        (11, 'Asus ROG Zephyrus', '₹1,65,990', 'In Stock', 'Laptops', 
         'Gaming powerhouse with RTX 4070', 4.8, 'Asus', '2 Years'),
        
        # Tablets
        (12, 'iPad Pro 12.9', '₹1,12,900', 'In Stock', 'Tablets', 
         'Professional tablet with M2 chip and Liquid Retina XDR display', 4.8, 'Apple', '1 Year'),
        (13, 'Samsung Galaxy Tab S9', '₹76,999', 'In Stock', 'Tablets', 
         'Premium Android tablet with S Pen included', 4.6, 'Samsung', '1 Year'),
        (14, 'iPad Air', '₹59,900', 'In Stock', 'Tablets', 
         'Versatile tablet with M1 chip', 4.7, 'Apple', '1 Year'),
        
        # Headphones & Audio
        (15, 'Sony WH-1000XM5', '₹29,990', 'In Stock', 'Audio', 
         'Industry-leading noise cancelling headphones', 4.8, 'Sony', '1 Year'),
        (16, 'AirPods Pro 2', '₹24,900', 'In Stock', 'Audio', 
         'Premium wireless earbuds with spatial audio', 4.7, 'Apple', '1 Year'),
        (17, 'Bose QC45', '₹28,900', 'In Stock', 'Audio', 
         'Legendary comfort with excellent noise cancellation', 4.6, 'Bose', '1 Year'),
        (18, 'JBL Flip 6', '₹12,999', 'In Stock', 'Audio', 
         'Portable Bluetooth speaker with powerful sound', 4.5, 'JBL', '1 Year'),
        
        # Wearables
        (19, 'Apple Watch Series 9', '₹41,900', 'In Stock', 'Wearables', 
         'Advanced health and fitness tracking', 4.8, 'Apple', '1 Year'),
        (20, 'Samsung Galaxy Watch 6', '₹30,999', 'In Stock', 'Wearables', 
         'Comprehensive health monitoring with Wear OS', 4.5, 'Samsung', '1 Year'),
        (21, 'Fitbit Charge 6', '₹12,999', 'In Stock', 'Wearables', 
         'Fitness tracker with Google integration', 4.4, 'Fitbit', '1 Year'),
        
        # Accessories
        (22, 'Anker PowerCore 20000', '₹3,999', 'In Stock', 'Accessories', 
         'High-capacity portable charger', 4.6, 'Anker', '18 Months'),
        (23, 'Logitech MX Master 3S', '₹8,995', 'In Stock', 'Accessories', 
         'Professional wireless mouse with precision scrolling', 4.7, 'Logitech', '1 Year'),
        (24, 'Apple Magic Keyboard', '₹9,900', 'In Stock', 'Accessories', 
         'Wireless keyboard with numeric keypad', 4.5, 'Apple', '1 Year'),
        (25, 'Samsung T7 SSD 1TB', '₹9,499', 'In Stock', 'Accessories', 
         'Portable solid-state drive with blazing speeds', 4.7, 'Samsung', '3 Years'),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?)', products)
    
    # Create categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT UNIQUE,
            description TEXT,
            item_count INTEGER
        )
    ''')
    
    categories = [
        (1, 'Smartphones', 'Latest mobile phones from top brands', 6),
        (2, 'Laptops', 'Portable computers for work and gaming', 5),
        (3, 'Tablets', 'Touch-screen tablets for productivity', 3),
        (4, 'Audio', 'Headphones, earbuds, and speakers', 4),
        (5, 'Wearables', 'Smartwatches and fitness trackers', 3),
        (6, 'Accessories', 'Chargers, mice, keyboards, and storage', 4),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO categories VALUES (?,?,?,?)', categories)
    
    conn.commit()
    conn.close()
    print("✅ Products Database created successfully!")
    
    # ==================== SUMMARY ====================
    print("\n" + "="*60)
    print("📊 DATABASE SUMMARY")
    print("="*60)
    print(f"✅ Total Orders: {len(orders)}")
    print(f"✅ Total Products: {len(products)}")
    print(f"✅ Product Categories: {len(categories)}")
    print("="*60)
    print("\n🎉 All databases created and populated successfully!")
    print("\nYou can now:")
    print("  1. Track orders: 12345, ORD001, 98765, etc.")
    print("  2. Check products: iPhone 15, MacBook Air, Sony WH-1000XM5, etc.")
    print("  3. Browse categories: Smartphones, Laptops, Audio, etc.")
    print("\n💡 Tip: Run 'rasa train' to update your bot with new data!")

if __name__ == "__main__":
    create_databases()