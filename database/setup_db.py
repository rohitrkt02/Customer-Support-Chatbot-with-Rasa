import sqlite3
import json
from datetime import datetime, timedelta

def create_databases():
    # Create Orders Database
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
            tracking_number TEXT
        )
    ''')
    
    # Sample data
    orders = [
        ('12345', 'John Doe', 'iPhone 15 Pro', 'Shipped', '2025-10-20', '2025-10-30', 'TRK123456'),
        ('ORD001', 'Jane Smith', 'Samsung Galaxy S24', 'Processing', '2025-10-25', '2025-11-02', 'TRK789012'),
        ('98765', 'Bob Johnson', 'MacBook Air', 'Delivered', '2025-10-15', '2025-10-25', 'TRK345678'),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?)', orders)
    conn.commit()
    conn.close()
    
    # Create Products Database
    conn = sqlite3.connect('database/products.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            price TEXT,
            stock TEXT,
            category TEXT,
            description TEXT
        )
    ''')
    
    products = [
        (1, 'iPhone 15 Pro', '₹1,34,999', 'In Stock', 'Smartphones', 'Latest Apple flagship'),
        (2, 'Samsung Galaxy S24', '₹79,999', 'In Stock', 'Smartphones', 'Samsung flagship phone'),
        (3, 'Redmi Note 12', '₹14,999', 'Limited Stock', 'Smartphones', 'Budget-friendly option'),
        (4, 'MacBook Air M2', '₹99,990', 'In Stock', 'Laptops', 'Apple laptop'),
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?)', products)
    conn.commit()
    conn.close()
    
    print("✅ Databases created successfully!")

if __name__ == "__main__":
    create_databases()