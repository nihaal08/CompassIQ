import sys
sys.path.insert(0, '.')
from app import verify_password
from db import query_db

agent = query_db("SELECT * FROM department_agents WHERE email = 'tech.agent@compassiq.com'", one=True)
stored = agent['password']
print("stored:", repr(stored))
print("provided:", repr('Agent@123'))
print("verify_password result:", verify_password(stored, 'Agent@123'))

from werkzeug.security import check_password_hash
try:
    res = check_password_hash(stored, 'Agent@123')
    print("check_password_hash result:", res)
except Exception as e:
    print("check_password_hash exception:", e)
