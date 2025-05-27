import sqlite3

DB_PATH = 'presence.db'

def clear_all_entries():
    """Clear all entries from the presence_logs table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM presence_logs')
    conn.commit()
    conn.close()
    print("[INFO] All entries have been deleted.")

def clear_last_n_entries(n):
    """Clear the last n entries from the presence_logs table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(''' 
        DELETE FROM presence_logs
        WHERE id IN (
            SELECT id FROM presence_logs ORDER BY id DESC LIMIT ?
        )
    ''', (n,))
    conn.commit()
    conn.close()
    print(f"[INFO] Last {n} entries have been deleted.")

def init_db():
    """Initialize the database and create the necessary tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create presence_logs table with try_id
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS presence_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            presence INTEGER,
            fallback_used INTEGER,
            method TEXT,
            timestamp TEXT,
            try_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()
    print("[INFO] Database initialized.")

if __name__ == '__main__':
    # Initialize the database (if needed)
    init_db()

    # Choose one of the options below based on what you need:
    
    # Option 1: Clear all entries
    clear_all_entries()
    
    # Option 2: Clear last N rows (set N to the number of rows you want to delete)
    #clear_last_n_entries(n)