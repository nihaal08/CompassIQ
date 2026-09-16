import sys
sys.path.insert(0, '.')
import sqlite3
from config import Config

c = sqlite3.connect(Config.DATABASE_PATH)
sql = c.execute("SELECT sql FROM sqlite_master WHERE name='tickets'").fetchone()
if sql:
    print(sql[0])
else:
    print("No tickets view")
