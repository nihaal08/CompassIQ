import sys
sys.path.insert(0, '.')
from app import app

with app.test_client() as c:
    res = c.post('/login', data={'email': 'customer@compassiq.com', 'password': 'User@123'})
    with c.session_transaction() as sess:
        print("Customer login status:", res.status_code, "->", res.headers.get('Location'))
        print("Session:", dict(sess))
