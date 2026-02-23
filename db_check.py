import sqlite3
import os

db_path = "bot.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def check_table(table_name):
    print(f"\n--- Schema for {table_name} ---")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"Column: {col[1]}, Type: {col[2]}, Dflt: {col[4]}")

check_table("users")
check_table("vacancies")

conn.close()
