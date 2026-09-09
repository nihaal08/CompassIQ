import sqlite3
from pathlib import Path
from config import Config

# Use the new database path from config
conn = sqlite3.connect(Config.DATABASE_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cursor.fetchall())
conn.close()