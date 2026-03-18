"""
web_interface/dashboards.py
Aroma & Co. Café Chatbot — Admin Dashboard
Flask App — Port 8001

Endpoints:
  GET  /dashboard          → main dashboard (templates/dashboard.html)
  GET  /api/stats          → JSON stats for charts
  GET  /api/today          → today's reservations JSON
  GET  /api/all            → all reservations with optional filters
  POST /api/update-status  → update reservation status (Confirmed/Cancelled)
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, date, timedelta

app = Flask(__name__)
CORS(app)

DB_PATH = "database/aroma.db"


# ── DB helper ─────────────────────────────────────────────────
def get_db():
    """Open and return a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ════════════════════════════════════════════════════════════
#  DASHBOARD MAIN PAGE
# ════════════════════════════════════════════════════════════
@app.route('/dashboard')
def dashboard():
    """Render the admin dashboard using templates/dashboard.html."""
    try:
        conn = get_db()
        c    = conn.cursor()

        # ── Summary counts ──────────────────────────────
        c.execute("SELECT COUNT(*) FROM reservations")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM reservations WHERE status='Confirmed'")
        confirmed = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM reservations WHERE status='Cancelled'")
        cancelled = c.fetchone()[0]

        today_str = date.today().isoformat()
        c.execute(
            "SELECT COUNT(*) FROM reservations WHERE date=? AND status='Confirmed'",
            (today_str,)
        )
        today_count = c.fetchone()[0]

        # ── Today's reservations ─────────────────────────
        c.execute("""
            SELECT ref, name, phone, time, guests, special_req, status
            FROM reservations
            WHERE date = ?
            ORDER BY time
        """, (today_str,))
        today_res = [dict(r) for r in c.fetchall()]

        # ── Upcoming 7 days ──────────────────────────────
        upcoming_dates = [
            (date.today() + timedelta(days=i)).isoformat()
            for i in range(1, 8)
        ]
        c.execute(f"""
            SELECT ref, name, date, time, guests, status
            FROM reservations
            WHERE date IN ({','.join('?' * len(upcoming_dates))})
            AND status = 'Confirmed'
            ORDER BY date, time
        """, upcoming_dates)
        upcoming = [dict(r) for r in c.fetchall()]

        # ── Bookings by time slot ────────────────────────
        c.execute("""
            SELECT time, COUNT(*) as cnt
            FROM reservations
            WHERE status = 'Confirmed'
            GROUP BY time ORDER BY time
        """)
        slot_data = [dict(r) for r in c.fetchall()]

        # ── Recent 10 reservations ───────────────────────
        c.execute("""
            SELECT ref, name, date, time, guests, special_req, status, created_at
            FROM reservations
            ORDER BY created_at DESC LIMIT 10
        """)
        recent = [dict(r) for r in c.fetchall()]

        conn.close()

        return render_template(
            'dashboard.html',
            total       = total,
            confirmed   = confirmed,
            cancelled   = cancelled,
            today_count = today_count,
            today_res   = today_res,
            upcoming    = upcoming,
            slot_data   = slot_data,
            recent      = recent,
            today_str   = today_str,
        )

    except Exception as e:
        return (
            f"<h2 style='font-family:sans-serif;padding:40px;color:#c8833a'>☕ Dashboard Error</h2>"
            f"<p style='font-family:sans-serif;padding:0 40px;color:#6b3f1f'>{e}</p>"
            f"<p style='font-family:sans-serif;padding:10px 40px;color:#999'>Make sure "
            f"<code>database/aroma.db</code> exists. Run <code>python database/setup_db.py</code> first.</p>"
        ), 500


# ════════════════════════════════════════════════════════════
#  JSON STATS API
# ════════════════════════════════════════════════════════════
@app.route('/api/stats')
def get_stats():
    """Return live dashboard stats as JSON."""
    try:
        conn = get_db()
        c    = conn.cursor()

        today_str = date.today().isoformat()

        c.execute("SELECT COUNT(*) FROM reservations")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM reservations WHERE status='Confirmed'")
        confirmed = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM reservations WHERE status='Cancelled'")
        cancelled = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM reservations WHERE date=? AND status='Confirmed'",
            (today_str,)
        )
        today_count = c.fetchone()[0]

        # Bookings per day — last 7 days
        daily = []
        for i in range(6, -1, -1):
            d = (date.today() - timedelta(days=i)).isoformat()
            c.execute(
                "SELECT COUNT(*) FROM reservations WHERE date=? AND status='Confirmed'",
                (d,)
            )
            daily.append({'date': d, 'count': c.fetchone()[0]})

        # Most popular time slots
        c.execute("""
            SELECT time, COUNT(*) as cnt FROM reservations
            WHERE status='Confirmed' GROUP BY time ORDER BY cnt DESC
        """)
        slots = [dict(r) for r in c.fetchall()]

        # Guest count breakdown
        c.execute("""
            SELECT guests, COUNT(*) as cnt FROM reservations
            WHERE status='Confirmed' GROUP BY guests ORDER BY guests
        """)
        guests = [dict(r) for r in c.fetchall()]

        conn.close()

        return jsonify({
            'total'    : total,
            'confirmed': confirmed,
            'cancelled': cancelled,
            'today'    : today_count,
            'daily'    : daily,
            'slots'    : slots,
            'guests'   : guests,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  TODAY'S RESERVATIONS
# ════════════════════════════════════════════════════════════
@app.route('/api/today')
def today_reservations():
    """Return today's reservations as JSON."""
    try:
        conn      = get_db()
        c         = conn.cursor()
        today_str = date.today().isoformat()

        c.execute(
            "SELECT * FROM reservations WHERE date=? ORDER BY time",
            (today_str,)
        )
        rows = [dict(r) for r in c.fetchall()]
        conn.close()

        return jsonify({'date': today_str, 'reservations': rows, 'count': len(rows)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  ALL RESERVATIONS
# ════════════════════════════════════════════════════════════
@app.route('/api/all')
def all_reservations():
    """
    Return all reservations as JSON.
    Optional query params: date, status
    """
    date_filter   = request.args.get('date',   '').strip()
    status_filter = request.args.get('status', '').strip()

    try:
        conn   = get_db()
        c      = conn.cursor()
        query  = "SELECT * FROM reservations WHERE 1=1"
        params = []

        if date_filter:
            query += " AND date=?"
            params.append(date_filter)
        if status_filter:
            query += " AND status=?"
            params.append(status_filter)

        query += " ORDER BY date DESC, time"

        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()

        return jsonify({'reservations': rows, 'count': len(rows)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  UPDATE RESERVATION STATUS
# ════════════════════════════════════════════════════════════
@app.route('/api/update-status', methods=['POST'])
def update_status():
    """
    Update reservation status.
    JSON body: { "ref": "ARM-1234", "status": "Confirmed" | "Cancelled" }
    """
    data   = request.json or {}
    ref    = data.get('ref',    '').strip().upper()
    status = data.get('status', '').strip()

    if not ref or status not in ('Confirmed', 'Cancelled'):
        return jsonify({'success': False, 'message': 'Invalid ref or status.'}), 400

    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("UPDATE reservations SET status=? WHERE ref=?", (status, ref))
        conn.commit()
        affected = c.rowcount
        conn.close()

        if affected:
            return jsonify({'success': True, 'message': f'{ref} updated to {status}.'})
        return jsonify({'success': False, 'message': 'Reservation not found.'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════
#  RUN
# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    print("\n" + "=" * 50)
    print("  ☕  Aroma & Co. — Admin Dashboard")
    print("=" * 50)
    print("  Dashboard → http://localhost:8001/dashboard")
    print("  Stats API → http://localhost:8001/api/stats")
    print("  Today     → http://localhost:8001/api/today")
    print("=" * 50 + "\n")
    app.run(debug=True, port=8001)