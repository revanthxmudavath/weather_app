import sqlite3

DB_FILE = "weather.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_key TEXT NOT NULL,
            location_label TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            units TEXT NOT NULL,
            data_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_FILE)