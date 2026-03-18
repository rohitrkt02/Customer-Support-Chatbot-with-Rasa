"""
database/setup_db.py
Aroma & Co. Café Chatbot (Rasa + Gemini AI)
Creates: database/aroma.db
  - reservations table  (table bookings)
  - menu_items table    (full café menu)
"""

import sqlite3
import os


def create_database():
    print("\n" + "=" * 55)
    print("  ☕  AROMA & CO. — DATABASE SETUP")
    print("=" * 55)

    # Make sure database/ folder exists
    os.makedirs('database', exist_ok=True)

    conn = sqlite3.connect('database/aroma.db')
    c = conn.cursor()

    # ══════════════════════════════════════════════════════
    #  TABLE 1 — RESERVATIONS
    # ══════════════════════════════════════════════════════
    print("\n📅 Creating reservations table...")

    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ref         TEXT UNIQUE,
            name        TEXT NOT NULL,
            phone       TEXT,
            email       TEXT,
            date        TEXT NOT NULL,
            time        TEXT NOT NULL,
            guests      TEXT NOT NULL,
            special_req TEXT,
            status      TEXT DEFAULT "Confirmed",
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    sample_reservations = [
        ('ARM-0001', 'Rohit Gupta',    '+91 98765 43210', 'rohit@email.com',   '2026-03-22', '8:00 PM',  '2', 'Window seat please',     'Confirmed'),
        ('ARM-0002', 'Priya Sharma',   '+91 91234 56789', 'priya@email.com',   '2026-03-23', '12:30 PM', '4', 'Birthday celebration',    'Confirmed'),
        ('ARM-0003', 'Arjun Singh',    '+91 99887 76655', 'arjun@email.com',   '2026-03-24', '5:00 PM',  '2', '',                        'Confirmed'),
        ('ARM-0004', 'Sneha Verma',    '+91 88776 65544', 'sneha@email.com',   '2026-03-25', '9:30 AM',  '3', 'Vegan options needed',    'Confirmed'),
        ('ARM-0005', 'Rahul Mishra',   '+91 77665 54433', 'rahul@email.com',   '2026-03-18', '8:00 PM',  '2', '',                        'Cancelled'),
        ('ARM-0006', 'Nisha Agarwal',  '+91 99001 23456', 'nisha@email.com',   '2026-03-26', '3:30 PM',  '5', 'Anniversary celebration', 'Confirmed'),
        ('ARM-0007', 'Vikram Tiwari',  '+91 98112 34567', 'vikram@email.com',  '2026-03-27', '12:30 PM', '2', 'Quiet corner table',      'Confirmed'),
        ('ARM-0008', 'Anjali Kapoor',  '+91 97223 45678', 'anjali@email.com',  '2026-03-28', '8:00 PM',  '6', 'Office team lunch',       'Confirmed'),
    ]

    c.executemany('''
        INSERT OR IGNORE INTO reservations
            (ref, name, phone, email, date, time, guests, special_req, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_reservations)

    print(f"  ✅ {len(sample_reservations)} sample reservations inserted")

    # ══════════════════════════════════════════════════════
    #  TABLE 2 — MENU ITEMS
    # ══════════════════════════════════════════════════════
    print("\n🍽️  Creating menu_items table...")

    c.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            price       TEXT NOT NULL,
            description TEXT,
            available   INTEGER DEFAULT 1,
            is_vegan    INTEGER DEFAULT 0,
            is_featured INTEGER DEFAULT 0
        )
    ''')

    menu_items = [
        # ── COFFEE ────────────────────────────────────────────────────────────
        # (name, category, price, description, available, is_vegan, is_featured)
        ('Espresso Classico',          'Coffee',   '₹120',   'Pure bold 25ml shot from our Ethiopian blend.',               1, 1, 0),
        ('Signature Latte',            'Coffee',   '₹220',   'Velvety microfoam over double ristretto. Our bestseller.',    1, 1, 1),
        ('Cold Brew Reserve',          'Coffee',   '₹280',   '18-hour slow-steeped Colombian served over large ice.',       1, 1, 1),
        ('Honey Cardamom Flat White',  'Coffee',   '₹260',   'Spiced, golden and surprisingly comforting.',                 1, 1, 0),
        ('Matcha Cortado',             'Coffee',   '₹290',   'Ceremonial grade matcha meets a shot of espresso.',           1, 1, 0),
        ('Dark Mocha',                 'Coffee',   '₹250',   '72% Valrhona cocoa with our house espresso.',                 1, 1, 0),

        # ── FOOD ──────────────────────────────────────────────────────────────
        ('Butter Croissant',           'Food',     '₹160',   'French-style, laminated 27 times. Flaky beyond belief.',      1, 0, 1),
        ('Truffle Mushroom Toast',     'Food',     '₹380',   'Sourdough, whipped ricotta, mushrooms & black truffle oil.',  1, 1, 1),
        ('Seasonal Grain Bowl',        'Food',     '₹350',   'Farro, roasted veggies, tahini dressing. Vegan.',             1, 1, 0),
        ('Eggs Benedict',              'Food',     '₹420',   'Poached farm eggs, hollandaise, smoked salmon on brioche.',   1, 0, 0),
        ('Brown Butter Banana Cake',   'Food',     '₹290',   'Warm slice served with vanilla bean gelato.',                 1, 0, 0),
        ('Cheese & Charcuterie Board', 'Food',     '₹680',   'Seasonal selection, house preserves, artisan crackers.',      1, 0, 0),

        # ── SPECIALS ──────────────────────────────────────────────────────────
        ('Rose Saffron Latte',         'Specials', '₹320',   'Saffron-infused milk, rose water & pistachio. Lucknow special.', 1, 1, 1),
        ('Espresso Tonic',             'Specials', '₹300',   'Double shot over premium Indian tonic, lemon peel.',          1, 1, 1),
        ('Masala Spice Brew',          'Specials', '₹220',   'Single origin coffee with fresh desi spice blend.',           1, 1, 0),
        ('Blueberry Lavender Latte',   'Specials', '₹310',   'House blueberry compote, lavender syrup, oat milk over ice.', 1, 1, 0),
        ('Hojicha Latte',              'Specials', '₹280',   'Roasted Japanese green tea. Toasty and gentle.',              1, 1, 0),
        ('Celebration Brunch Set',     'Specials', '₹1,200', 'Curated spread for two — coffee, food, dessert, juice.',      1, 0, 0),

        # ── DRINKS ────────────────────────────────────────────────────────────
        ('Sparkling Lemonade',         'Drinks',   '₹180',   'House-pressed lemons, cane sugar, Perrier.',                  1, 1, 0),
        ('Summer Berry Cooler',        'Drinks',   '₹220',   'Strawberry, raspberry, mint, elderflower over crushed ice.',  1, 1, 0),
        ('Alphonso Mango Lassi',       'Drinks',   '₹200',   'Real Alphonso mangoes blended with rich yoghurt.',            1, 1, 0),
        ('Single Estate Darjeeling',   'Drinks',   '₹160',   'First flush, delicate muscatel notes. Served in ceramic.',    1, 1, 0),
        ('Fresh Pressed Juice',        'Drinks',   '₹160',   'Seasonal selection. Ask your server what is fresh today.',    1, 1, 0),
        ('House Kombucha',             'Drinks',   '₹240',   'Ginger-lemon, brewed in-house. Gut-friendly and fizzy.',      1, 1, 0),
    ]

    c.executemany('''
        INSERT OR IGNORE INTO menu_items
            (name, category, price, description, available, is_vegan, is_featured)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', menu_items)

    print(f"  ✅ {len(menu_items)} menu items inserted")
    print(f"     ☕ Coffee   : {sum(1 for m in menu_items if m[1]=='Coffee')} items")
    print(f"     🥐 Food     : {sum(1 for m in menu_items if m[1]=='Food')} items")
    print(f"     🌸 Specials : {sum(1 for m in menu_items if m[1]=='Specials')} items")
    print(f"     🍹 Drinks   : {sum(1 for m in menu_items if m[1]=='Drinks')} items")

    conn.commit()
    conn.close()

    # ══════════════════════════════════════════════════════
    #  SUMMARY
    # ══════════════════════════════════════════════════════
    print("\n" + "=" * 55)
    print("  ✅  DATABASE SETUP COMPLETE — aroma.db")
    print("=" * 55)
    print("\n📋 Sample booking refs to test:")
    print("   ARM-0001 (Confirmed)  ARM-0002 (Confirmed)")
    print("   ARM-0005 (Cancelled)  ARM-0006 (Confirmed)")
    print("\n🚀 Next steps:")
    print("   1. Set API key → export GEMINI_API_KEY=your_key")
    print("   2. Train model → rasa train")
    print("   3. Terminal 1  → rasa run actions")
    print("   4. Terminal 2  → rasa run --enable-api --cors \"*\"")
    print("   5. Terminal 3  → python web_interface/app.py")
    print("   6. Browser     → http://localhost:8000")
    print()


if __name__ == "__main__":
    create_database()