import sqlite3
from config import Config

conn = sqlite3.connect(Config.DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- TABLES & VIEWS ---")
tables = cursor.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
for t in tables:
    cols = [col[1] for col in cursor.execute(f"PRAGMA table_info({t['name']})").fetchall()]
    print(f"{t['type'].upper()}: {t['name']} -> {cols}")

print("\n--- SAMPLE TICKET ---")
tkt = cursor.execute("SELECT * FROM complaints LIMIT 1").fetchone()
if tkt:
    print(dict(tkt))
else:
    print("No tickets found in complaints")

print("\n--- SAMPLE REPLIES ---")
replies = cursor.execute("SELECT * FROM ticket_replies LIMIT 2").fetchall()
for r in replies:
    print(dict(r))

print("\n--- USERS VIEW SAMPLES ---")
users = cursor.execute("SELECT * FROM users LIMIT 5").fetchall()
for u in users:
    print(dict(u))
