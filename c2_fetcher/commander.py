import sqlite3
import sys

DB_FILE = "c2_queue.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_url TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            response_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_command(url):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (target_url) VALUES (?)", (url,))
    conn.commit()
    conn.close()
    print(f"[!] Command issued: Target '{url}' added to queue.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python commander.py <URL>")
        print("Example: python commander.py http://localhost:8000")
    else:
        target_url = sys.argv[1]
        add_command(target_url)