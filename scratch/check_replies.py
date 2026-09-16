import sys
sys.path.insert(0, '.')
import sqlite3
from config import Config

conn = sqlite3.connect(Config.DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- CUSTOMERS ---")
for row in cursor.execute("SELECT custid, custname, email FROM customers").fetchall():
    print(dict(row))

print("\n--- AGENTS ---")
for row in cursor.execute("SELECT agent_id, agent_name, email, role, deptid FROM department_agents").fetchall():
    print(dict(row))

print("\n--- TEST REPLIES JOIN ---")
replies = cursor.execute("""
    SELECT r.reply_id, r.ticketno, r.sender_id, u.user_id, u.full_name, u.role
    FROM ticket_replies r
    LEFT JOIN users u ON r.sender_id = u.user_id
    LIMIT 10
""").fetchall()
for r in replies:
    print(dict(r))
