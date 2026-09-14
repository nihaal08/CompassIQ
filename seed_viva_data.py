"""
CompassIQ — Viva Demo Seed Data Script
========================================
Completely wipes obsolete test records and seeds a rich, viva-ready dataset
with realistic users, tickets, conversation threads, and CSAT ratings.

All passwords are hashed for: Password@123
"""

import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

# Database configuration
DB_PATH = Path(__file__).parent / 'database' / 'storage' / 'compassiq.db'

# Standard demo password
DEMO_PASSWORD = 'Password@123'
DEMO_PASSWORD_HASH = generate_password_hash(DEMO_PASSWORD, method='scrypt')


def get_connection():
    """Create database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def wipe_database(conn):
    """
    Wipe all ticket-related data while preserving users table structure.
    This ensures a clean slate for viva demo data.
    """
    print("[Seed] Wiping existing data...")
    
    # Delete in order of foreign key dependencies
    conn.execute("DELETE FROM ticket_replies")
    conn.execute("DELETE FROM ticket_similar_matches")
    conn.execute("DELETE FROM tickets")
    conn.execute("DELETE FROM users")
    
    conn.commit()
    print("[Seed] All data wiped successfully.")


def seed_users(conn):
    """Seed demo users with standardized credentials."""
    print("[Seed] Creating demo users...")
    
    users = [
        # Admin
        {
            'full_name': 'System Administrator',
            'email': 'admin@compassiq.com',
            'role': 'admin',
            'department': None,
            'account_status': 'APPROVED'
        },
        
        # Technical Department (5 agents + primary)
        {'full_name': 'Technical Support Lead', 'email': 'technical@compassiq.com', 'role': 'agent', 'department': 'Technical', 'account_status': 'APPROVED'},
        {'full_name': 'Tech Agent 1', 'email': 'tech1@compassiq.com', 'role': 'agent', 'department': 'Technical', 'account_status': 'APPROVED'},
        {'full_name': 'Tech Agent 2', 'email': 'tech2@compassiq.com', 'role': 'agent', 'department': 'Technical', 'account_status': 'APPROVED'},
        {'full_name': 'Tech Agent 3', 'email': 'tech3@compassiq.com', 'role': 'agent', 'department': 'Technical', 'account_status': 'APPROVED'},
        {'full_name': 'Tech Agent 4', 'email': 'tech4@compassiq.com', 'role': 'agent', 'department': 'Technical', 'account_status': 'APPROVED'},
        {'full_name': 'Tech Agent 5', 'email': 'tech5@compassiq.com', 'role': 'agent', 'department': 'Technical', 'account_status': 'APPROVED'},
        
        # Billing Department (5 agents + primary)
        {'full_name': 'Billing Support Lead', 'email': 'billing@compassiq.com', 'role': 'agent', 'department': 'Billing', 'account_status': 'APPROVED'},
        {'full_name': 'Billing Agent 1', 'email': 'billing1@compassiq.com', 'role': 'agent', 'department': 'Billing', 'account_status': 'APPROVED'},
        {'full_name': 'Billing Agent 2', 'email': 'billing2@compassiq.com', 'role': 'agent', 'department': 'Billing', 'account_status': 'APPROVED'},
        {'full_name': 'Billing Agent 3', 'email': 'billing3@compassiq.com', 'role': 'agent', 'department': 'Billing', 'account_status': 'APPROVED'},
        {'full_name': 'Billing Agent 4', 'email': 'billing4@compassiq.com', 'role': 'agent', 'department': 'Billing', 'account_status': 'APPROVED'},
        {'full_name': 'Billing Agent 5', 'email': 'billing5@compassiq.com', 'role': 'agent', 'department': 'Billing', 'account_status': 'APPROVED'},
        
        # Account Department (5 agents + primary)
        {'full_name': 'Account Support Lead', 'email': 'account@compassiq.com', 'role': 'agent', 'department': 'Account', 'account_status': 'APPROVED'},
        {'full_name': 'Account Agent 1', 'email': 'account1@compassiq.com', 'role': 'agent', 'department': 'Account', 'account_status': 'APPROVED'},
        {'full_name': 'Account Agent 2', 'email': 'account2@compassiq.com', 'role': 'agent', 'department': 'Account', 'account_status': 'APPROVED'},
        {'full_name': 'Account Agent 3', 'email': 'account3@compassiq.com', 'role': 'agent', 'department': 'Account', 'account_status': 'APPROVED'},
        {'full_name': 'Account Agent 4', 'email': 'account4@compassiq.com', 'role': 'agent', 'department': 'Account', 'account_status': 'APPROVED'},
        {'full_name': 'Account Agent 5', 'email': 'account5@compassiq.com', 'role': 'agent', 'department': 'Account', 'account_status': 'APPROVED'},
        
        # General Inquiry Agent
        {'full_name': 'General Inquiry Agent', 'email': 'general@compassiq.com', 'role': 'agent', 'department': 'General Inquiry', 'account_status': 'APPROVED'},
        
        # Customers
        {'full_name': 'Demo Customer', 'email': 'customer@compassiq.com', 'role': 'customer', 'department': None, 'account_status': 'APPROVED'},
        {'full_name': 'Alex Johnson', 'email': 'alex@compassiq.com', 'role': 'customer', 'department': None, 'account_status': 'APPROVED'},
        {'full_name': 'Maria Garcia', 'email': 'maria@compassiq.com', 'role': 'customer', 'department': None, 'account_status': 'APPROVED'},
        {'full_name': 'David Chen', 'email': 'david@compassiq.com', 'role': 'customer', 'department': None, 'account_status': 'APPROVED'},
        {'full_name': 'Emily Wilson', 'email': 'emily@compassiq.com', 'role': 'customer', 'department': None, 'account_status': 'APPROVED'},
    ]
    
    user_id_map = {}
    
    for user in users:
        cursor = conn.execute(
            """INSERT INTO users (full_name, email, password_hash, role, department, account_status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user['full_name'], user['email'], DEMO_PASSWORD_HASH, 
             user['role'], user['department'], user['account_status'])
        )
        user_id_map[user['email']] = cursor.lastrowid
    
    conn.commit()
    print(f"[Seed] Created {len(users)} demo users.")
    
    return user_id_map


def seed_tickets(conn, user_id_map):
    """Seed realistic tickets with diverse states and CSAT ratings."""
    print("[Seed] Creating demo tickets...")
    
    tickets = [
        # Technical Department Tickets
        {
            'customer_email': 'alex@compassiq.com',
            'assigned_agent_email': 'technical@compassiq.com',
            'subject': 'VPN connection drops with error 502',
            'description': 'My VPN connection keeps dropping intermittently with error code 502. This is affecting my remote work productivity.',
            'category': 'Technical',
            'priority': 'Critical',
            'department': 'Technical',
            'status': 'Resolved',
            'csat_score': 5,
            'feedback': 'Excellent support! Issue resolved quickly.',
            'resolution_notes': 'Updated gateway routing and flushed DNS cache. Connection stable for 24 hours.',
            'created_at': datetime.now() - timedelta(days=3),
            'resolved_at': datetime.now() - timedelta(days=2)
        },
        {
            'customer_email': 'maria@compassiq.com',
            'assigned_agent_email': 'tech1@compassiq.com',
            'subject': 'Production server high memory utilization',
            'description': 'Our production server is showing 95% memory utilization and applications are becoming unresponsive.',
            'category': 'Technical',
            'priority': 'High',
            'department': 'Technical',
            'status': 'In Progress',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(days=1),
            'resolved_at': None
        },
        {
            'customer_email': 'david@compassiq.com',
            'assigned_agent_email': None,
            'subject': 'Docker container crash during build',
            'description': 'Docker containers crash during the build process with exit code 137 (OOM killed).',
            'category': 'Technical',
            'priority': 'Medium',
            'department': 'Technical',
            'status': 'Submitted',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(hours=6),
            'resolved_at': None
        },
        {
            'customer_email': 'emily@compassiq.com',
            'assigned_agent_email': 'tech2@compassiq.com',
            'subject': 'Database timeout on analytics query',
            'description': 'Analytics queries are timing out after 30 seconds. Need optimization help.',
            'category': 'Technical',
            'priority': 'High',
            'department': 'Technical',
            'status': 'Resolved',
            'csat_score': 4,
            'feedback': 'Good resolution, but response time could be faster.',
            'resolution_notes': 'Added missing indexes on frequently queried columns. Query time reduced to 2 seconds.',
            'created_at': datetime.now() - timedelta(days=5),
            'resolved_at': datetime.now() - timedelta(days=4)
        },
        
        # Billing Department Tickets
        {
            'customer_email': 'customer@compassiq.com',
            'assigned_agent_email': 'billing@compassiq.com',
            'subject': 'Double charged for monthly subscription',
            'description': 'I was charged twice for my monthly subscription on September 1st. Please refund the duplicate charge.',
            'category': 'Billing',
            'priority': 'High',
            'department': 'Billing',
            'status': 'Resolved',
            'csat_score': 5,
            'feedback': 'Refund processed quickly. Thank you!',
            'resolution_notes': 'Processed refund transaction ID #RF99281. Duplicate charge reversed.',
            'created_at': datetime.now() - timedelta(days=4),
            'resolved_at': datetime.now() - timedelta(days=3)
        },
        {
            'customer_email': 'alex@compassiq.com',
            'assigned_agent_email': 'billing2@compassiq.com',
            'subject': 'Invoice #INV-2026-088 not showing tax breakdown',
            'description': 'Invoice PDF does not show the GST tax breakdown. Need this for accounting purposes.',
            'category': 'Billing',
            'priority': 'Medium',
            'department': 'Billing',
            'status': 'In Progress',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(days=2),
            'resolved_at': None
        },
        {
            'customer_email': 'maria@compassiq.com',
            'assigned_agent_email': None,
            'subject': 'Payment failed via credit card gateway',
            'description': 'Credit card payment failed with error: "Card declined by issuer". Card is valid and has sufficient funds.',
            'category': 'Billing',
            'priority': 'Critical',
            'department': 'Billing',
            'status': 'Submitted',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(hours=3),
            'resolved_at': None
        },
        {
            'customer_email': 'david@compassiq.com',
            'assigned_agent_email': 'billing3@compassiq.com',
            'subject': 'Request to update billing address on annual plan',
            'description': 'Need to update billing address to new office location.',
            'category': 'Billing',
            'priority': 'Low',
            'department': 'Billing',
            'status': 'Resolved',
            'csat_score': 4,
            'feedback': 'Address updated successfully.',
            'resolution_notes': 'Billing address updated in account profile and payment system.',
            'created_at': datetime.now() - timedelta(days=6),
            'resolved_at': datetime.now() - timedelta(days=5)
        },
        {
            'customer_email': 'alex@compassiq.com',
            'assigned_agent_email': 'billing@compassiq.com',
            'subject': 'Duplicate billing charge on my card statement',
            'description': 'I checked my bank statement today and noticed I was charged twice for my subscription renewal. Please refund the duplicate transaction immediately.',
            'category': 'Billing',
            'priority': 'High',
            'department': 'Billing',
            'status': 'Submitted',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(hours=2),
            'resolved_at': None
        },
        
        # Account Department Tickets
        {
            'customer_email': 'emily@compassiq.com',
            'assigned_agent_email': 'account@compassiq.com',
            'subject': '2FA authenticator lost after phone reset',
            'description': 'I reset my phone and lost my 2FA authenticator app. Cannot access my account.',
            'category': 'Account',
            'priority': 'Critical',
            'department': 'Account',
            'status': 'Resolved',
            'csat_score': 5,
            'feedback': 'Excellent verification process. Account recovered safely.',
            'resolution_notes': 'Identity verified via secondary channel; recovery codes reset. User can now re-enroll 2FA.',
            'created_at': datetime.now() - timedelta(days=2),
            'resolved_at': datetime.now() - timedelta(days=1)
        },
        {
            'customer_email': 'customer@compassiq.com',
            'assigned_agent_email': 'account1@compassiq.com',
            'subject': 'Cannot update profile email address',
            'description': 'When I try to update my email address in profile settings, I get an error: "Email already in use".',
            'category': 'Account',
            'priority': 'Medium',
            'department': 'Account',
            'status': 'In Progress',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(days=1),
            'resolved_at': None
        },
        {
            'customer_email': 'alex@compassiq.com',
            'assigned_agent_email': None,
            'subject': 'SSO login loop on Google Workspace',
            'description': 'When attempting SSO login via Google Workspace, I get redirected in a loop and never reach the dashboard.',
            'category': 'Account',
            'priority': 'High',
            'department': 'Account',
            'status': 'Submitted',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(hours=12),
            'resolved_at': None
        },
        {
            'customer_email': 'maria@compassiq.com',
            'assigned_agent_email': 'account2@compassiq.com',
            'subject': 'Account unlock request after multiple password attempts',
            'description': 'Account locked after multiple incorrect password attempts. Need unlock.',
            'category': 'Account',
            'priority': 'Medium',
            'department': 'Account',
            'status': 'Resolved',
            'csat_score': 3,
            'feedback': 'Account unlocked, but process took longer than expected.',
            'resolution_notes': 'Account unlocked after identity verification. Password reset email sent.',
            'created_at': datetime.now() - timedelta(days=3),
            'resolved_at': datetime.now() - timedelta(days=2)
        },
        
        # General Inquiry Tickets
        {
            'customer_email': 'david@compassiq.com',
            'assigned_agent_email': 'general@compassiq.com',
            'subject': 'API rate limits for custom integrations',
            'description': 'What are the API rate limits for third-party integrations? Need documentation.',
            'category': 'General Inquiry',
            'priority': 'Low',
            'department': 'General Inquiry',
            'status': 'Resolved',
            'csat_score': 5,
            'feedback': 'Documentation provided was comprehensive.',
            'resolution_notes': 'Sent API documentation link and rate limit details.',
            'created_at': datetime.now() - timedelta(days=7),
            'resolved_at': datetime.now() - timedelta(days=6)
        },
        {
            'customer_email': 'emily@compassiq.com',
            'assigned_agent_email': None,
            'subject': 'Warranty coverage for hardware devices',
            'description': 'What is the standard warranty coverage period for hardware devices?',
            'category': 'General Inquiry',
            'priority': 'Low',
            'department': 'General Inquiry',
            'status': 'Submitted',
            'csat_score': None,
            'feedback': None,
            'resolution_notes': None,
            'created_at': datetime.now() - timedelta(hours=8),
            'resolved_at': None
        },
    ]
    
    ticket_id_map = {}
    
    for ticket in tickets:
        customer_id = user_id_map[ticket['customer_email']]
        assigned_agent_id = user_id_map.get(ticket['assigned_agent_email']) if ticket['assigned_agent_email'] else None
        
        # Generate ticket ID
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{len(ticket_id_map) + 1:04d}"
        
        cursor = conn.execute(
            """INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, 
               predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, 
               satisfaction_score, customer_feedback, created_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, customer_id, ticket['subject'], ticket['description'],
             ticket['category'], ticket['priority'], ticket['department'], ticket['status'],
             assigned_agent_id, ticket['resolution_notes'], ticket['csat_score'],
             ticket['feedback'], ticket['created_at'], ticket['resolved_at'])
        )
        
        ticket_id_map[ticket_id] = {
            'ticket_id': ticket_id,
            'customer_id': customer_id,
            'assigned_agent_id': assigned_agent_id
        }
    
    conn.commit()
    print(f"[Seed] Created {len(tickets)} demo tickets.")
    
    return ticket_id_map


def seed_replies(conn, ticket_id_map, user_id_map):
    """Seed conversation thread records for resolved tickets."""
    print("[Seed] Creating conversation threads...")
    
    replies = [
        # VPN ticket (resolved with CSAT 5)
        {
            'ticket_id': 'TKT-20260913-0001',
            'sender_email': 'alex@compassiq.com',
            'message': 'My VPN connection keeps dropping intermittently with error code 502. This is affecting my remote work productivity.',
            'created_at': datetime.now() - timedelta(days=3)
        },
        {
            'ticket_id': 'TKT-20260913-0001',
            'sender_email': 'technical@compassiq.com',
            'message': 'Hello Alex, thank you for reporting this issue. We are investigating the gateway routing configuration. Can you provide the timestamps of the disconnections?',
            'created_at': datetime.now() - timedelta(days=3, hours=2)
        },
        {
            'ticket_id': 'TKT-20260913-0001',
            'sender_email': 'alex@compassiq.com',
            'message': 'Most disconnections happen between 9 AM and 11 AM. I can share the logs if needed.',
            'created_at': datetime.now() - timedelta(days=3, hours=3)
        },
        {
            'ticket_id': 'TKT-20260913-0001',
            'sender_email': 'technical@compassiq.com',
            'message': 'We have identified the issue. Updated gateway routing and flushed DNS cache. Connection should be stable now. Please let us know if you experience any further issues.',
            'created_at': datetime.now() - timedelta(days=2)
        },
        
        # Double charge ticket (resolved with CSAT 5)
        {
            'ticket_id': 'TKT-20260913-0005',
            'sender_email': 'customer@compassiq.com',
            'message': 'I was charged twice for my monthly subscription on September 1st. Please refund the duplicate charge.',
            'created_at': datetime.now() - timedelta(days=4)
        },
        {
            'ticket_id': 'TKT-20260913-0005',
            'sender_email': 'billing@compassiq.com',
            'message': 'Thank you for reporting this. I have reviewed your account and confirmed the duplicate charge. Processing refund now.',
            'created_at': datetime.now() - timedelta(days=4, hours=1)
        },
        {
            'ticket_id': 'TKT-20260913-0005',
            'sender_email': 'billing@compassiq.com',
            'message': 'Refund processed successfully. Transaction ID: #RF99281. The amount should appear in your account within 3-5 business days.',
            'created_at': datetime.now() - timedelta(days=3)
        },
        
        # 2FA ticket (resolved with CSAT 5)
        {
            'ticket_id': 'TKT-20260913-0009',
            'sender_email': 'emily@compassiq.com',
            'message': 'I reset my phone and lost my 2FA authenticator app. Cannot access my account.',
            'created_at': datetime.now() - timedelta(days=2)
        },
        {
            'ticket_id': 'TKT-20260913-0009',
            'sender_email': 'account@compassiq.com',
            'message': 'Hi Emily, for security purposes, we need to verify your identity before recovering 2FA. Can you provide your account email and last 4 digits of the registered phone number?',
            'created_at': datetime.now() - timedelta(days=2, hours=1)
        },
        {
            'ticket_id': 'TKT-20260913-0009',
            'sender_email': 'emily@compassiq.com',
            'message': 'Email: emily@compassiq.com, Phone: ****1234',
            'created_at': datetime.now() - timedelta(days=2, hours=2)
        },
        {
            'ticket_id': 'TKT-20260913-0009',
            'sender_email': 'account@compassiq.com',
            'message': 'Identity verified. I have reset your recovery codes. Please log in using your password and the new recovery codes. Then re-enroll your 2FA authenticator.',
            'created_at': datetime.now() - timedelta(days=1)
        },
    ]
    
    for reply in replies:
        # Find the actual ticket ID from the map (need to match by order)
        ticket_data = None
        for tid, data in ticket_id_map.items():
            if reply['ticket_id'] in tid or tid.endswith(reply['ticket_id'].split('-')[-1]):
                ticket_data = data
                break
        
        if not ticket_data:
            continue
        
        sender_id = user_id_map[reply['sender_email']]
        
        conn.execute(
            """INSERT INTO ticket_replies (ticket_id, sender_id, message, created_at)
               VALUES (?, ?, ?, ?)""",
            (ticket_data['ticket_id'], sender_id, reply['message'], reply['created_at'])
        )
    
    conn.commit()
    print(f"[Seed] Created {len(replies)} conversation replies.")
    
    # Get actual ticket IDs from database
    actual_tickets = conn.execute("SELECT ticket_id, subject FROM tickets ORDER BY ticket_id").fetchall()
    ticket_data = {t[0]: t[1] for t in actual_tickets}
    ticket_ids = list(ticket_data.keys())
    
    if len(ticket_ids) < 14:
        print(f"[Seed] Warning: Expected 14 tickets, found {len(ticket_ids)}")
        # Use the tickets we have
        ticket_ids = ticket_ids
    
    # Create sample similar matches for demo tickets using actual ticket IDs
    print("[Seed] Creating similar historical matches...")
    similar_matches = []
    
    # Find the specific billing ticket for the demo
    billing_ticket_id = None
    for tid, subject in ticket_data.items():
        if 'Duplicate billing charge' in subject or 'duplicate' in subject.lower():
            billing_ticket_id = tid
            break
    
    # If we found the billing ticket, add the specific demo matches
    if billing_ticket_id:
        similar_matches.extend([
            (billing_ticket_id, 'HIST-BILL-801', 0.924, 'Double charge on annual subscription invoice', 'Customer was billed twice for the annual renewal fee on transaction TXN-9942. Identified gateway sync duplicate charge. Initiated automated reversal for invoice INV-9942 and credited 500 reward points to the customer wallet.', 2),
            (billing_ticket_id, 'HIST-BILL-802', 0.868, 'Subscription renewal payment deducted twice', 'My credit card was debited two times during auto-renewal of the premium plan. Verified payment processor log. Issued immediate refund for the secondary debit transaction within 3-5 business days.', 3),
            (billing_ticket_id, 'HIST-BILL-803', 0.795, 'Duplicate transaction on billing cycle checkout', 'Payment gateway timed out but card statement shows duplicate charges for the same order. Canceled redundant pending authorization capture at the acquirer bank level and updated customer ledger.', 4),
        ])
        print(f"[Seed] Added specific demo matches for billing ticket: {billing_ticket_id}")
    
    # Add generic matches for other tickets
    for i, ticket_id in enumerate(ticket_ids):
        if ticket_id == billing_ticket_id:
            continue  # Skip the billing ticket as we already added specific matches
            
        similar_matches.extend([
            (ticket_id, f'HIST-{i+1}-001', 0.92 - (i * 0.01), f'Similar issue pattern {i+1}', f'Historical resolution for issue pattern {i+1}', 4 + i),
            (ticket_id, f'HIST-{i+1}-002', 0.87 - (i * 0.01), f'Related problem {i+1}', f'Historical context for problem {i+1}', 6 + i),
            (ticket_id, f'HIST-{i+1}-003', 0.81 - (i * 0.01), f'Prior case {i+1}', f'Historical solution for case {i+1}', 3 + i),
        ])
    
    for match in similar_matches:
        conn.execute(
            """INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours)
               VALUES (?, ?, ?, ?, ?, ?)""",
            match
        )
    
    conn.commit()
    print(f"[Seed] Created {len(similar_matches)} similar historical matches.")


def main():
    """Main seed function."""
    print("=" * 70)
    print("COMPASSIQ — VIVA DEMO SEED DATA SCRIPT")
    print("=" * 70)
    
    if not DB_PATH.exists():
        print(f"[Error] Database not found at: {DB_PATH}")
        print("Please initialize the database first by running the application.")
        sys.exit(1)
    
    conn = get_connection()
    
    try:
        # Wipe existing data
        wipe_database(conn)
        
        # Seed users
        user_id_map = seed_users(conn)
        
        # Seed tickets
        ticket_id_map = seed_tickets(conn, user_id_map)
        
        # Seed conversation replies
        seed_replies(conn, ticket_id_map, user_id_map)
        
        print("\n" + "=" * 70)
        print("SEED DATA COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nDemo Credentials:")
        print(f"  All accounts use password: {DEMO_PASSWORD}")
        print(f"\nPrimary Demo Accounts:")
        print(f"  Admin: admin@compassiq.com")
        print(f"  Technical: technical@compassiq.com")
        print(f"  Billing: billing@compassiq.com")
        print(f"  Account: account@compassiq.com")
        print(f"  General: general@compassiq.com")
        print(f"  Customer: customer@compassiq.com")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"[Error] Seeding failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
