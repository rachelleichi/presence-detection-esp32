from flask import Flask, request, render_template, jsonify
import sqlite3

app = Flask(__name__)
DATABASE_FILE = 'presence.db'


@app.route('/', methods=['GET'])
def show_history():
    method_filter = request.args.get('method', None)
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        
        if method_filter:
            c.execute('''
                SELECT filename, presence, fallback_used, method, timestamp, try_id
                FROM presence_logs
                WHERE method = ?
                ORDER BY timestamp DESC
                LIMIT 150
            ''', (method_filter,))
        else:
            c.execute('''
                SELECT filename, presence, fallback_used, method, timestamp, try_id
                FROM presence_logs
                ORDER BY timestamp DESC
                LIMIT 150
            ''')

        records = c.fetchall()
        conn.close()
        print("RECORDS:", records)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'records': records})

        return render_template('history.html', records=records, method_filter=method_filter)
        
    except Exception as e:
        return f"<p><strong>Error:</strong> {e}</p>", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010 )  # Port 50010 for the history server
# -*- coding: utf-8 -*- 
# This script sets up a Flask server to display the history of presence detection results.
# It connects to a SQLite database to retrieve and display records.         
# It also supports filtering by detection method via query parameters.