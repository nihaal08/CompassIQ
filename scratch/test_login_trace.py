import sys
sys.path.insert(0, '.')
from app import app
from db import query_db

email = 'tech.agent@compassiq.com'
agent = query_db(
    """SELECT a.agent_id, a.agent_name, a.email, a.password, a.deptid, a.role, a.account_status,
              d.deptname as department
       FROM department_agents a
       LEFT JOIN departments d ON a.deptid = d.deptid
       WHERE LOWER(TRIM(a.email)) = ?""",
    (email,),
    one=True
)
print("Agent record from DB:", dict(agent) if agent else None)

from app import verify_password
print("Verify with Agent@123:", verify_password(agent['password'], 'Agent@123') if agent else False)
print("Verify with password123:", verify_password(agent['password'], 'password123') if agent else False)

with app.test_client() as c:
    res = c.post('/login', data={'email': email, 'password': 'Agent@123'})
    print("POST /login status:", res.status_code)
    print("Response headers:", res.headers)
    print("HTML snippet:", res.data.decode('utf-8')[:300])
