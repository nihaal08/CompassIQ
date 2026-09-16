import sys
sys.path.insert(0, '.')
from app import app
from db import query_db, modify_db

client = app.test_client()

departments_and_agents = [
    ('Technical', 'tech.agent@compassiq.com', 'Agent@123', 1),
    ('Billing', 'billing.agent@compassiq.com', 'Agent@123', 2),
    ('Account', 'account.agent@compassiq.com', 'Agent@123', 3),
    ('General Inquiry', 'general.agent@compassiq.com', 'Agent@123', 4),
    ('Fraud & Security', 'fraud.agent@compassiq.com', 'Agent@123', 5),
    ('Admin', 'admin@compassiq.com', 'Admin@123', None)
]

all_passed = True

print("\n=======================================================")
print("COMPREHENSIVE TICKET DETAILS VERIFICATION ACROSS ALL DEPARTMENTS")
print("=======================================================")

for dept_name, email, pwd, dept_id in departments_and_agents:
    print(f"\n--- Testing Department: {dept_name} ({email}) ---")
    with app.test_client() as c:
        # Login
        res = c.post('/login', data={'email': email, 'password': pwd}, follow_redirects=True)
        assert res.status_code == 200, f"Login failed for {email}"
        print(f" [PASS] Logged in successfully")

        # Query assigned tickets for this department
        if dept_id is not None:
            tickets = query_db("SELECT ticketno, subject, deptid, assigned_agent_id FROM complaints WHERE deptid = ?", (dept_id,))
        else:
            tickets = query_db("SELECT ticketno, subject, deptid, assigned_agent_id FROM complaints")

        print(f" Found {len(tickets)} tickets to test for {dept_name}")

        for t in tickets:
            tkt_id = t['ticketno']

            # 1. HTML details page
            html_res = c.get(f'/agent/tickets/{tkt_id}/details')
            if html_res.status_code != 200:
                print(f" [FAIL] HTML details failed for {tkt_id}: Status {html_res.status_code}")
                all_passed = False
            else:
                assert tkt_id.encode('utf-8') in html_res.data, f"Ticket ID {tkt_id} missing in rendered HTML"
                print(f" [PASS] HTML details for {tkt_id}: HTTP 200 OK")

            # 2. AJAX JSON endpoint
            json_res = c.get(f'/agent/tickets/{tkt_id}/details', headers={
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            })
            if json_res.status_code != 200:
                print(f" [FAIL] AJAX details failed for {tkt_id}: Status {json_res.status_code}")
                all_passed = False
            else:
                data = json_res.get_json()
                assert data['success'] is True, f"AJAX success was False for {tkt_id}"
                assert 'ticket' in data and data['ticket']['ticketno'] == tkt_id
                assert 'customer' in data and 'name' in data['customer']
                assert 'replies' in data and isinstance(data['replies'], list)
                assert 'similar_matches' in data and isinstance(data['similar_matches'], list)
                print(f" [PASS] AJAX details for {tkt_id}: HTTP 200 OK (Replies: {len(data['replies'])}, Similar: {len(data['similar_matches'])})")

# Test 3: Customer Ticket Details
print("\n--- Testing Customer Ticket Details (/customer/tickets/<id>) ---")
with app.test_client() as c:
    c.post('/login', data={'email': 'customer@compassiq.com', 'password': 'User@123'}, follow_redirects=True)
    cust_tickets = query_db("SELECT ticketno FROM complaints WHERE custid = (SELECT custid FROM customers WHERE email = 'customer@compassiq.com')")
    for t in cust_tickets:
        tkt_id = t['ticketno']
        res = c.get(f'/customer/tickets/{tkt_id}', headers={'Accept': 'application/json'})
        assert res.status_code == 200, f"Customer ticket detail failed for {tkt_id}"
        data = res.get_json()
        assert data['success'] is True
        print(f" [PASS] Customer details for {tkt_id}: HTTP 200 OK")

# Test 4: Create a brand new ticket under Fraud & Security and verify immediate details loading
print("\n--- Testing Newly Created Ticket Without Prior Replies or Similar Matches ---")
with app.test_client() as c:
    c.post('/login', data={'email': 'customer@compassiq.com', 'password': 'User@123'}, follow_redirects=True)
    create_res = c.post('/create_ticket', data={
        'subject': 'Suspicious unauthorized debit charge on Mastercard',
        'description': 'Someone stole my Mastercard credentials and initiated an unauthorized charge of $850. Please investigate fraud.'
    }, follow_redirects=True)
    assert create_res.status_code == 200

    # Get newest ticket
    new_tkt = query_db("SELECT ticketno, deptid FROM complaints ORDER BY submitdate DESC LIMIT 1", one=True)
    new_id = new_tkt['ticketno']
    print(f" Created new ticket: {new_id} in deptid={new_tkt['deptid']}")

# Log in as Fraud agent and test details
with app.test_client() as c:
    c.post('/login', data={'email': 'fraud.agent@compassiq.com', 'password': 'Agent@123'}, follow_redirects=True)
    
    html_res = c.get(f'/agent/tickets/{new_id}/details')
    assert html_res.status_code == 200, f"New ticket HTML failed: {html_res.status_code}"
    print(f" [PASS] New ticket {new_id} HTML details: HTTP 200 OK")

    json_res = c.get(f'/agent/tickets/{new_id}/details', headers={
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    })
    assert json_res.status_code == 200, f"New ticket AJAX failed: {json_res.status_code}"
    data = json_res.get_json()
    assert data['success'] is True
    print(f" [PASS] New ticket {new_id} AJAX details: HTTP 200 OK (AI Similar Matches: {len(data['similar_matches'])})")

if all_passed:
    print("\n=======================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! ZERO 500 ERRORS.")
    print("=======================================================")
else:
    print("\n[!] SOME TESTS FAILED")
    sys.exit(1)
