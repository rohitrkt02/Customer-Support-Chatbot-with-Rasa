"""
database/setup_db.py
Aroma & Co. — Customer Support Chatbot
Creates and seeds all three databases:
  • orders.db   → orders, returns, reservations tables
  • products.db → products table
"""

import sqlite3


def create_databases():
    print("🚀 Setting up Aroma & Co. databases...\n")

    # ═══════════════════════════════════════════════════
    #  orders.db  (orders + returns + reservations)
    # ═══════════════════════════════════════════════════
    print("📦 Creating orders.db ...")
    conn = sqlite3.connect('database/orders.db')
    c = conn.cursor()

    # ── orders ──────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id          TEXT PRIMARY KEY,
            customer_name     TEXT,
            product           TEXT,
            status            TEXT,
            order_date        TEXT,
            expected_delivery TEXT,
            tracking_number   TEXT,
            price             TEXT,
            quantity          INTEGER DEFAULT 1
        )
    ''')

    orders = [
        ('12345',  'John Doe',       'iPhone 15 Pro',        'Shipped',    '2025-11-01', '2025-11-15', 'TRK123456', '₹1,34,999', 1),
        ('ORD001', 'Jane Smith',     'Samsung Galaxy S24',   'Processing', '2025-11-05', '2025-11-18', 'TRK789012', '₹79,999',   1),
        ('98765',  'Bob Johnson',    'MacBook Air M2',        'Delivered',  '2025-10-20', '2025-10-28', 'TRK345678', '₹99,990',   1),
        ('ORD002', 'Alice Williams', 'Sony WH-1000XM5',      'Shipped',    '2025-11-03', '2025-11-16', 'TRK456789', '₹29,990',   2),
        ('ORD003', 'Charlie Brown',  'iPad Pro 12.9',        'Processing', '2025-11-08', '2025-11-20', 'TRK567890', '₹1,12,900', 1),
        ('ORD004', 'David Lee',      'Dell XPS 15',          'Shipped',    '2025-11-02', '2025-11-14', 'TRK678901', '₹1,45,990', 1),
        ('ORD005', 'Emma Davis',     'AirPods Pro 2',        'Delivered',  '2025-10-25', '2025-11-01', 'TRK789012', '₹24,900',   1),
        ('ORD006', 'Frank Miller',   'OnePlus 12',           'Shipped',    '2025-11-04', '2025-11-17', 'TRK890123', '₹64,999',   1),
        ('ORD007', 'Grace Chen',     'Apple Watch Series 9', 'Processing', '2025-11-07', '2025-11-19', 'TRK901234', '₹41,900',   1),
        ('ORD008', 'Henry Wilson',   'Google Pixel 8 Pro',   'Shipped',    '2025-11-06', '2025-11-18', 'TRK012345', '₹84,999',   1),
    ]
    c.executemany('INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?)', orders)

    # ── returns ─────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            return_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id         TEXT,
            reason           TEXT,
            preferred_action TEXT,
            status           TEXT DEFAULT "Pending",
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── reservations (café) ─────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ref         TEXT UNIQUE,
            name        TEXT,
            phone       TEXT,
            email       TEXT,
            date        TEXT,
            time        TEXT,
            guests      TEXT,
            special_req TEXT,
            status      TEXT DEFAULT "Confirmed",
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    sample_reservations = [
        ('ARM-0001', 'Rohit Gupta',  '+91 98765 43210', 'rohit@email.com', '2026-03-22', '8:00 PM',  '2', 'Window seat please',  'Confirmed'),
        ('ARM-0002', 'Priya Sharma', '+91 91234 56789', 'priya@email.com', '2026-03-23', '12:30 PM', '4', 'Birthday celebration', 'Confirmed'),
        ('ARM-0003', 'Arjun Singh',  '+91 99887 76655', 'arjun@email.com', '2026-03-24', '5:00 PM',  '2', '',                    'Confirmed'),
        ('ARM-0004', 'Sneha Verma',  '+91 88776 65544', 'sneha@email.com', '2026-03-25', '9:30 AM',  '3', 'Vegan options needed', 'Confirmed'),
        ('ARM-0005', 'Rahul Mishra', '+91 77665 54433', 'rahul@email.com', '2026-03-18', '8:00 PM',  '2', '',                    'Cancelled'),
    ]
    c.executemany(
        'INSERT OR IGNORE INTO reservations (ref,name,phone,email,date,time,guests,special_req,status) VALUES (?,?,?,?,?,?,?,?,?)',
        sample_reservations
    )

    conn.commit()
    conn.close()
    print(f"  ✅ orders       : {len(orders)} records")
    print(f"  ✅ reservations : {len(sample_reservations)} sample records")

    # ═══════════════════════════════════════════════════
    #  products.db
    # ═══════════════════════════════════════════════════
    print("\n🛍️  Creating products.db ...")
    conn = sqlite3.connect('database/products.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id  INTEGER PRIMARY KEY,
            name        TEXT,
            price       TEXT,
            stock       TEXT,
            category    TEXT,
            description TEXT,
            rating      REAL,
            brand       TEXT,
            warranty    TEXT
        )
    ''')

    products = [
        # Smartphones
        (1,  'iPhone 15 Pro',          '₹1,34,999', 'In Stock',      'Smartphones', 'Latest Apple flagship with A17 Pro chip and titanium design', 4.8, 'Apple',    '1 Year'),
        (2,  'Samsung Galaxy S24',     '₹79,999',   'In Stock',      'Smartphones', 'Premium Android flagship with AI features',                   4.7, 'Samsung',  '1 Year'),
        (3,  'Redmi Note 12',          '₹14,999',   'Limited Stock', 'Smartphones', 'Budget-friendly smartphone with 120Hz display',               4.3, 'Xiaomi',   '1 Year'),
        (4,  'OnePlus 12',             '₹64,999',   'In Stock',      'Smartphones', 'Flagship killer with Snapdragon 8 Gen 3',                     4.6, 'OnePlus',  '1 Year'),
        (5,  'Google Pixel 8 Pro',     '₹84,999',   'In Stock',      'Smartphones', 'Best-in-class camera with Google Tensor G3',                  4.7, 'Google',   '1 Year'),
        # Laptops
        (6,  'MacBook Air M2',         '₹99,990',   'In Stock',      'Laptops',     'Ultra-thin laptop with Apple M2 chip',                        4.9, 'Apple',    '1 Year'),
        (7,  'Dell XPS 15',            '₹1,45,990', 'In Stock',      'Laptops',     'Premium Windows laptop with InfinityEdge display',            4.6, 'Dell',     '1 Year'),
        (8,  'HP Pavilion 15',         '₹55,990',   'In Stock',      'Laptops',     'Value laptop for everyday computing',                         4.2, 'HP',       '1 Year'),
        (9,  'Lenovo ThinkPad X1',     '₹1,25,990', 'Limited Stock', 'Laptops',     'Business-grade laptop with military durability',              4.7, 'Lenovo',   '3 Years'),
        (10, 'Asus ROG Zephyrus',      '₹1,65,990', 'In Stock',      'Laptops',     'Gaming powerhouse with RTX 4070',                             4.8, 'Asus',     '2 Years'),
        # Tablets
        (11, 'iPad Pro 12.9',          '₹1,12,900', 'In Stock',      'Tablets',     'Professional tablet with M2 chip',                            4.8, 'Apple',    '1 Year'),
        (12, 'Samsung Galaxy Tab S9',  '₹76,999',   'In Stock',      'Tablets',     'Premium Android tablet with S Pen included',                  4.6, 'Samsung',  '1 Year'),
        (13, 'iPad Air',               '₹59,900',   'In Stock',      'Tablets',     'Versatile tablet with M1 chip',                               4.7, 'Apple',    '1 Year'),
        # Audio
        (14, 'Sony WH-1000XM5',        '₹29,990',   'In Stock',      'Audio',       'Industry-leading noise cancelling headphones',                4.8, 'Sony',     '1 Year'),
        (15, 'AirPods Pro 2',          '₹24,900',   'In Stock',      'Audio',       'Premium wireless earbuds with spatial audio',                 4.7, 'Apple',    '1 Year'),
        (16, 'Bose QC45',              '₹28,900',   'In Stock',      'Audio',       'Legendary comfort with excellent noise cancellation',         4.6, 'Bose',     '1 Year'),
        (17, 'JBL Flip 6',             '₹12,999',   'In Stock',      'Audio',       'Portable Bluetooth speaker with powerful sound',              4.5, 'JBL',      '1 Year'),
        # Wearables
        (18, 'Apple Watch Series 9',   '₹41,900',   'In Stock',      'Wearables',   'Advanced health and fitness tracking',                        4.8, 'Apple',    '1 Year'),
        (19, 'Samsung Galaxy Watch 6', '₹30,999',   'In Stock',      'Wearables',   'Comprehensive health monitoring with Wear OS',                4.5, 'Samsung',  '1 Year'),
        (20, 'Fitbit Charge 6',        '₹12,999',   'In Stock',      'Wearables',   'Fitness tracker with Google integration',                     4.4, 'Fitbit',   '1 Year'),
        # Accessories
        (21, 'Anker PowerCore 20000',  '₹3,999',    'In Stock',      'Accessories', 'High-capacity portable charger',                              4.6, 'Anker',    '18 Months'),
        (22, 'Logitech MX Master 3S',  '₹8,995',    'In Stock',      'Accessories', 'Professional wireless mouse with precision scrolling',        4.7, 'Logitech', '1 Year'),
        (23, 'Samsung T7 SSD 1TB',     '₹9,499',    'In Stock',      'Accessories', 'Portable SSD with blazing speeds',                            4.7, 'Samsung',  '3 Years'),
        (24, 'Apple Magic Keyboard',   '₹9,900',    'In Stock',      'Accessories', 'Wireless keyboard with numeric keypad',                       4.5, 'Apple',    '1 Year'),
    ]
    c.executemany('INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?)', products)

    conn.commit()
    conn.close()
    print(f"  ✅ products     : {len(products)} records")

    # ═══════════════════════════════════════════════════
    #  SUMMARY
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  ☕  DATABASE SETUP COMPLETE — Aroma & Co.")
    print("=" * 60)
    print("\n📋 Test data available:")
    print("  Order IDs   : 12345, ORD001, 98765, ORD002 ... ORD008")
    print("  Booking Refs: ARM-0001, ARM-0002, ARM-0003, ARM-0004")
    print("\n✅ Next step: run  python database/setup_db.py  then  rasa train\n")


if __name__ == "__main__":
    create_databases()