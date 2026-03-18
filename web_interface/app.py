"""
web_interface/app.py
Aroma & Co. Café Chatbot (Rasa + Gemini AI)
Flask Backend — Port 8000

Endpoints:
  GET  /                             → serves café website (templates/index.html)
  POST /chat                         → Rasa proxy (chatbot messages)
  POST /api/reserve                  → save table reservation from website form
  GET  /api/slots?date=YYYY-MM-DD    → check slot availability for a date
  POST /api/cancel/<ref>             → cancel reservation by ARM- reference
  GET  /api/reservation/<ref>        → get single reservation details
  GET  /api/reservations             → admin: list all reservations
  GET  /api/menu?category=...        → get menu items (optional category filter)
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import sqlite3
import random
import string
import os
import logging

# ── Setup ────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RASA_API_URL = "http://localhost:5005/webhooks/rest/webhook"
DB_PATH      = "database/aroma.db"


# ── DB helper ─────────────────────────────────────────────────
def get_db():
    """Open and return a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # dict-style column access
    return conn


# ════════════════════════════════════════════════════════════
#  MAIN PAGE
# ════════════════════════════════════════════════════════════
@app.route('/')
def home():
    """Serve the Aroma & Co. café website."""
    return render_template('index.html')


# ════════════════════════════════════════════════════════════
#  RASA CHAT PROXY
# ════════════════════════════════════════════════════════════
@app.route('/chat', methods=['POST'])
def chat():
    """
    Forward user messages to the Rasa server and relay the
    bot's response back to the frontend chatbot widget.
    Falls back gracefully if Rasa is unreachable.
    """
    data         = request.json or {}
    user_message = data.get('message', '').strip()
    sender_id    = data.get('sender', 'user')

    if not user_message:
        return jsonify([{"text": "Please type a message. ☕"}])

    try:
        response = requests.post(
            RASA_API_URL,
            json={"sender": sender_id, "message": user_message},
            timeout=8
        )
        bot_responses = response.json()

        if not bot_responses:
            return jsonify([{
                "text": "I'm not sure how to help with that. "
                        "You can ask me about our menu, table bookings, hours, "
                        "events, or WiFi. ☕"
            }])

        return jsonify(bot_responses)

    except requests.exceptions.Timeout:
        logger.warning("Rasa server timeout")
        return jsonify([{
            "text": "I'm taking a little longer than usual. ☕ "
                    "Please try again or call us at +91 98765 43210."
        }])
    except Exception as e:
        logger.error(f"Rasa proxy error: {e}")
        return jsonify([{
            "text": "Sorry, I'm having trouble right now. "
                    "Please call +91 98765 43210 or email hello@aromaandco.in."
        }])


# ════════════════════════════════════════════════════════════
#  TABLE RESERVATION
# ════════════════════════════════════════════════════════════
@app.route('/api/reserve', methods=['POST'])
def reserve_table():
    """
    Accept a table reservation submitted from the website
    booking form and save it to the database.

    Required JSON: name, date, time, guests
    Optional JSON: phone, email, special_requests
    """
    data    = request.json or {}
    name    = data.get('name',    '').strip()
    phone   = data.get('phone',   '').strip()
    email   = data.get('email',   '').strip()
    date    = data.get('date',    '').strip()
    time    = data.get('time',    '').strip()
    guests  = data.get('guests',  '').strip()
    special = data.get('special_requests', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Name is required.'}), 400
    if not date:
        return jsonify({'success': False, 'message': 'Date is required.'}), 400
    if not time:
        return jsonify({'success': False, 'message': 'Time slot is required.'}), 400
    if not guests:
        return jsonify({'success': False, 'message': 'Number of guests is required.'}), 400

    ref = 'ARM-' + ''.join(random.choices(string.digits, k=4))

    try:
        conn = get_db()
        c    = conn.cursor()

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

        c.execute('''
            INSERT INTO reservations
                (ref, name, phone, email, date, time, guests, special_req)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ref, name, phone, email, date, time, guests, special))

        conn.commit()
        conn.close()

        logger.info(f"New reservation: {ref} | {name} | {date} {time} | {guests} guests")

        return jsonify({
            'success': True,
            'ref'    : ref,
            'message': f'Table reserved for {name} on {date} at {time} for {guests} guest(s).'
        })

    except sqlite3.IntegrityError:
        return reserve_table()   # rare ref collision — retry
    except Exception as e:
        logger.error(f"Reservation error: {e}")
        return jsonify({
            'success': False,
            'message': 'Reservation failed. Please try again or call +91 98765 43210.'
        }), 500


# ════════════════════════════════════════════════════════════
#  SLOT AVAILABILITY
# ════════════════════════════════════════════════════════════
@app.route('/api/slots', methods=['GET'])
def get_slots():
    """
    Return available/unavailable time slots for a given date.
    Max 4 concurrent bookings per slot.
    Query param: date (YYYY-MM-DD)
    """
    date = request.args.get('date', '').strip()

    ALL_SLOTS    = [
        "8:00 AM", "9:30 AM", "11:00 AM", "12:30 PM",
        "2:00 PM", "3:30 PM", "5:00 PM",  "6:30 PM",  "8:00 PM"
    ]
    MAX_PER_SLOT = 4

    if not date:
        return jsonify({
            'slots': [{'time': s, 'available': True} for s in ALL_SLOTS]
        })

    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            "SELECT time, COUNT(*) as cnt FROM reservations "
            "WHERE date=? AND status!='Cancelled' GROUP BY time",
            (date,)
        )
        booked = {row['time']: row['cnt'] for row in c.fetchall()}
        conn.close()

        slots = [
            {
                'time'     : s,
                'available': booked.get(s, 0) < MAX_PER_SLOT,
                'booked'   : booked.get(s, 0),
                'remaining': max(0, MAX_PER_SLOT - booked.get(s, 0))
            }
            for s in ALL_SLOTS
        ]

        return jsonify({'date': date, 'slots': slots})

    except Exception as e:
        logger.error(f"Slot check error: {e}")
        return jsonify({
            'slots': [{'time': s, 'available': True} for s in ALL_SLOTS]
        })


# ════════════════════════════════════════════════════════════
#  CANCEL RESERVATION
# ════════════════════════════════════════════════════════════
@app.route('/api/cancel/<ref>', methods=['POST'])
def cancel_reservation(ref):
    """Cancel a reservation by its ARM- reference code."""
    if not ref:
        return jsonify({'success': False, 'message': 'Reference is required.'}), 400

    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            "UPDATE reservations SET status='Cancelled' WHERE ref=?",
            (ref.upper().strip(),)
        )
        conn.commit()
        affected = c.rowcount
        conn.close()

        if affected:
            logger.info(f"Cancelled reservation: {ref.upper()}")
            return jsonify({
                'success': True,
                'message': f'Reservation {ref.upper()} has been cancelled.'
            })
        return jsonify({
            'success': False,
            'message': f'No reservation found with reference {ref.upper()}.'
        }), 404

    except Exception as e:
        logger.error(f"Cancel error: {e}")
        return jsonify({
            'success': False,
            'message': 'Unable to cancel. Please call +91 98765 43210.'
        }), 500


# ════════════════════════════════════════════════════════════
#  GET SINGLE RESERVATION
# ════════════════════════════════════════════════════════════
@app.route('/api/reservation/<ref>', methods=['GET'])
def get_reservation(ref):
    """Fetch details of a single reservation by ARM- reference."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            'SELECT id, ref, name, phone, email, date, time, guests, '
            'special_req, status, created_at '
            'FROM reservations WHERE ref=?',
            (ref.upper().strip(),)
        )
        row = c.fetchone()
        conn.close()

        if row:
            return jsonify({'success': True, 'reservation': dict(row)})
        return jsonify({'success': False, 'message': 'Reservation not found.'}), 404

    except Exception as e:
        logger.error(f"Get reservation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  ADMIN — LIST ALL RESERVATIONS
# ════════════════════════════════════════════════════════════
@app.route('/api/reservations', methods=['GET'])
def list_reservations():
    """
    Admin: returns all reservations.
    Optional query params: date, status
    """
    date_filter   = request.args.get('date',   '').strip()
    status_filter = request.args.get('status', '').strip()

    try:
        conn = get_db()
        c    = conn.cursor()

        query  = 'SELECT * FROM reservations WHERE 1=1'
        params = []

        if date_filter:
            query  += ' AND date=?'
            params.append(date_filter)
        if status_filter:
            query  += ' AND status=?'
            params.append(status_filter)

        query += ' ORDER BY date DESC, time'

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        return jsonify({
            'success'     : True,
            'count'       : len(rows),
            'reservations': [dict(r) for r in rows]
        })

    except Exception as e:
        logger.error(f"List reservations error: {e}")
        return jsonify({'success': False, 'reservations': [], 'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  MENU ITEMS
# ════════════════════════════════════════════════════════════
@app.route('/api/menu', methods=['GET'])
def get_menu():
    """
    Return café menu items.
    Optional query params: category, vegan=true, featured=true
    """
    category = request.args.get('category', '').strip()
    vegan    = request.args.get('vegan',    '').strip().lower()
    featured = request.args.get('featured', '').strip().lower()

    try:
        conn = get_db()
        c    = conn.cursor()

        query  = ('SELECT name, category, price, description, '
                  'is_vegan, is_featured FROM menu_items WHERE available=1')
        params = []

        if category:
            query  += ' AND LOWER(category)=?'
            params.append(category.lower())
        if vegan == 'true':
            query  += ' AND is_vegan=1'
        if featured == 'true':
            query  += ' AND is_featured=1'

        query += ' ORDER BY category, name'

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'count'  : len(rows),
            'menu'   : [dict(r) for r in rows]
        })

    except Exception as e:
        logger.error(f"Menu fetch error: {e}")
        return jsonify({'success': False, 'menu': [], 'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  RUN
# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    print("\n" + "=" * 50)
    print("  ☕  Aroma & Co. — Flask Web Server")
    print("=" * 50)
    print("  Website  → http://localhost:8000")
    print("  Rasa     → http://localhost:5005")
    print("  DB       → database/aroma.db")
    print("=" * 50 + "\n")
    app.run(debug=True, port=8000)