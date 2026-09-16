import sys
sys.path.insert(0, '.')
from app import app

departments_and_agents = [
    ('Technical', 'tech.agent@compassiq.com', 'Agent@123'),
    ('Billing', 'billing.agent@compassiq.com', 'Agent@123'),
    ('Account', 'account.agent@compassiq.com', 'Agent@123'),
    ('General Inquiry', 'general.agent@compassiq.com', 'Agent@123'),
    ('Fraud & Security', 'fraud.agent@compassiq.com', 'Agent@123'),
    ('Admin', 'admin@compassiq.com', 'Admin@123')
]

for dept, email, pwd in departments_and_agents:
    with app.test_client() as c:
        res = c.post('/login', data={'email': email, 'password': pwd})
        with c.session_transaction() as sess:
            user_id = sess.get('user_id')
            role = sess.get('role')
            department = sess.get('department')
            print(f"{email}: HTTP {res.status_code} -> Location: {res.headers.get('Location')}, Session: user_id={user_id}, role={role}, dept={department}")
