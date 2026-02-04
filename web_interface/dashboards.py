from flask import Flask, render_template
import sqlite3
import json

app = Flask(__name__)

@app.route('/dashboard')
def dashboard():
    # Get statistics
    conn = sqlite3.connect('database/orders.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM orders')
    total_orders = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM returns')
    total_returns = cursor.fetchone()[0]
    
    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    order_stats = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         total_orders=total_orders,
                         total_returns=total_returns,
                         order_stats=order_stats)

if __name__ == '__main__':
    app.run(port=8001)