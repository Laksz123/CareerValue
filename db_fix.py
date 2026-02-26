import sqlite3
import os

db_path = "bot.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

migrations = [
    ("users", "is_admin", "BOOLEAN DEFAULT 0"),
    ("vacancy_posts", "reply_markup_json", "TEXT"),
]

for table, column, col_type in migrations:
    try:
        print(f"Adding '{column}' to '{table}'...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
        print(f"  Success!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"  Column '{column}' already exists.")
        else:
            print(f"  Error: {e}")

conn.close()
