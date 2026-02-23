import sqlite3
import os

db_path = "bot.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Adding 'is_admin' column to 'users' table...")
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    conn.commit()
    print("Success!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("Column 'is_admin' already exists.")
    else:
        print(f"Error: {e}")
finally:
    conn.close()
