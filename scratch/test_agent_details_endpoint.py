import sys
sys.path.insert(0, '.')
from app import app
from db import query_db

client = app.test_client()

departments_and_agents = [
    ('Technical', 'tech.agent@compassiq.com', 'Agent@123'),
    ('Billing', 'billing.agent@compassiq.com', 'Agent@123'),
    ('Account', 'account.agent@compassiq.com', 'Agent@123'),
    ('General Inquiry', 'general.agent@compassiq.com', 'Agent@123'),
    ('Fraud & Security', 'fraud.agent@compassiq.com', 'Agent@123'),
    ('Admin', 'admin@compassiq.com', 'Admin@123')
]

# Fetch all tickets in the system
all_tickets = query_db("SELECT ticketno, deptid, assigned_agent_id, status FROM complaints")
print(f"Total tickets in complaints: {len(all_tickets)}")

for dept_name, email, pwd in departments_and_agents:
    print(f"\n==========================================")
    print(f"Testing Agent: {email} ({dept_name})")
    print(f"==========================================")
    with app.test_client() as c:
        # Login
        login_res = c.post('/login', data={'email': email, 'password': pwd}, follow_redirects=True)
        if login_res.status_code != 200:
            print(f"  [FAIL] Login failed for {email}: {login_res.status_code}")
            continue
        print(f"  [OK] Logged in successfully.")

        # Test queue dashboard
        dash_res = c.get('/agent/dashboard' if dept_name != 'Admin' else '/admin/dashboard')
        print(f"  [OK] Dashboard status: {dash_res.status_code}")

        # Test each ticket
        for t in all_tickets:
            tkt_id = t['ticketno']
            
            # Direct GET (HTML render)
            html_res = c.get(f'/agent/tickets/{tkt_id}/details')
            
            # AJAX Fetch (JSON requested)
            json_res = c.get(f'/agent/tickets/{tkt_id}/details', headers={
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            })

            # Also check /api/tickets/<ticket_id>
            api_res = c.get(f'/api/tickets/{tkt_id}', headers={'Accept': 'application/json'})

            print(f"  Ticket {tkt_id} (dept {t['deptid']}): HTML={html_res.status_code}, AJAX={json_res.status_code}, API={api_res.status_code}")
            if html_res.status_code == 500:
                print(f"    [ERROR 500 HTML] Content: {html_res.data.decode('utf-8')[:300]}")
            if json_res.status_code == 500:
                print(f"    [ERROR 500 JSON] Content: {json_res.data.decode('utf-8')[:300]}")
