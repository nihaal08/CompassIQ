import os
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'instance' / 'compassiq.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(data_csv=BASE_DIR / 'data' / 'enhanced_customer_support_data.csv'):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users table (with department column for agent classification)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'agent', 'admin')),
            department TEXT CHECK(department IN ('Technical', 'Billing', 'Account', 'General Inquiry') OR department IS NULL),
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration check: Ensure department column exists in existing SQLite DBs
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'department' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN department TEXT')

    # 2. Tickets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            predicted_category TEXT,
            category_confidence REAL DEFAULT 0.0,
            priority TEXT NOT NULL,
            predicted_priority TEXT,
            priority_confidence REAL DEFAULT 0.0,
            channel TEXT DEFAULT 'Web',
            status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
            assigned_department TEXT,
            assigned_agent_id INTEGER,
            assigned_agent_name TEXT,
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolution_time_hours REAL,
            satisfaction_score INTEGER,
            feedback TEXT,
            resolution_notes TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(tickets)")
    ticket_columns = [col[1] for col in cursor.fetchall()]
    if 'assigned_department' not in ticket_columns:
        cursor.execute('ALTER TABLE tickets ADD COLUMN assigned_department TEXT')
    cursor.execute('''
        UPDATE tickets
        SET assigned_department = CASE category
            WHEN 'Fraud' THEN 'Admin'
            WHEN 'Technical' THEN 'Technical Support'
            WHEN 'Billing' THEN 'Billing'
            WHEN 'Account' THEN 'Account Support'
            ELSE 'General Inquiry'
        END,
        assigned_agent_id = CASE WHEN category = 'Fraud' THEN NULL ELSE assigned_agent_id END,
        assigned_agent_name = CASE WHEN category = 'Fraud' THEN 'Administrator' ELSE assigned_agent_name END
        WHERE assigned_department IS NULL
    ''')

    # 3. Ticket Comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            author_id INTEGER,
            author_name TEXT NOT NULL,
            author_role TEXT NOT NULL,
            comment_text TEXT NOT NULL,
            is_internal INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        )
    ''')

    # 4. Predictions Log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_code TEXT NOT NULL,
            predicted_category TEXT,
            category_confidence REAL,
            predicted_priority TEXT,
            priority_confidence REAL,
            similar_ticket_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. Knowledge Base table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            problem_description TEXT NOT NULL,
            solution_steps TEXT NOT NULL,
            author_agent TEXT NOT NULL,
            tags TEXT,
            status TEXT DEFAULT 'Published',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 6. Audit Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_email TEXT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Re-seed or update Default Users with department classification
    default_pwd = generate_password_hash('password123')

    users_data = [
        ('System Administrator', 'admin@compassiq.ai', default_pwd, 'admin', None, 'active'),
        ('Sarah Jenkins (Technical Agent)', 'agent@compassiq.ai', default_pwd, 'agent', 'Technical', 'active'),
        ('David Kim (Billing Agent)', 'david.kim@compassiq.ai', default_pwd, 'agent', 'Billing', 'active'),
        ('Elena Rodriguez (Account Agent)', 'elena.rodriguez@compassiq.ai', default_pwd, 'agent', 'Account', 'active'),
        ('Marcus Vance (General Agent)', 'general.agent@compassiq.ai', default_pwd, 'agent', 'General Inquiry', 'active'),
        ('John Doe (Customer)', 'customer@compassiq.ai', default_pwd, 'customer', None, 'active'),
        ('George Simon', 'george.simon@example.com', default_pwd, 'customer', None, 'active'),
        ('Scott Thompson', 'scott.thompson@example.com', default_pwd, 'customer', None, 'active')
    ]

    for name, email, pwd, role, dept, status in users_data:
        existing = cursor.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if not existing:
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, department, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, pwd, role, dept, status))
        else:
            cursor.execute('''
                UPDATE users SET role = ?, department = ? WHERE email = ?
            ''', (role, dept, email))
    conn.commit()

    # Seed Knowledge Base if empty
    cursor.execute('SELECT COUNT(*) FROM knowledge_base')
    if cursor.fetchone()[0] == 0:
        print("Seeding Knowledge Base articles...")
        kb_articles = [
            ("Resolving Application Startup Crashes on Settings Tab", "Technical",
             "Application closes abruptly whenever user navigates to the configuration panel.",
             "1. Inspect backend microservice logs.\n2. Purge local browser/application local storage cache.\n3. Restart background process worker.",
             "Sarah Jenkins (Technical Agent)", "crash, technical, settings", "Published"),
            ("Processing Prorated Subscription Refund Requests", "Billing",
             "Customer requests refund for unused tier billing cycle.",
             "1. Verify payment transaction token in payment gateway.\n2. Calculate prorated refund balance.\n3. Issue credit note and notify account holder via email.",
             "David Kim (Billing Agent)", "billing, refund, payment", "Published"),
            ("Resetting Locked User Credentials & MFA Security", "Account",
             "Customer locked out due to multiple invalid authentication attempts.",
             "1. Confirm user identity via verification code.\n2. Trigger secure password reset link.\n3. Clear failed login lock in security portal.",
             "Elena Rodriguez (Account Agent)", "account, login, password", "Published")
        ]
        cursor.executemany('''
            INSERT INTO knowledge_base (title, category, problem_description, solution_steps, author_agent, tags, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', kb_articles)
        conn.commit()

    # Seed Tickets Table from dataset if empty
    cursor.execute('SELECT COUNT(*) FROM tickets')
    if cursor.fetchone()[0] == 0 and os.path.exists(data_csv):
        print(f"Seeding tickets database from {data_csv}...")
        df = pd.read_csv(data_csv)
        sample_df = df.head(500)

        tickets_data = []
        for idx, row in sample_df.iterrows():
            t_code = str(row.get('Ticket_ID', f'TKT-{100000+idx}'))
            c_name = str(row.get('Customer_Name', 'Customer User'))
            c_email = str(row.get('Customer_Email', 'customer@example.com'))
            subject = str(row.get('Ticket_Subject', 'Support Request'))
            desc = str(row.get('Ticket_Description', 'Description not provided.'))
            cat = str(row.get('Issue_Category', 'General Inquiry'))
            prio = str(row.get('Priority_Level', 'Medium'))
            chan = str(row.get('Ticket_Channel', 'Web'))
            agent = str(row.get('Assigned_Agent', 'Sarah Jenkins'))
            res_time = float(row.get('Resolution_Time_Hours', 12.0))
            sat = int(row.get('Satisfaction_Score', 5))
            sub_date = str(row.get('Submission_Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            status = 'Resolved' if idx % 3 != 0 else ('In Progress' if idx % 2 == 0 else 'Open')
            
            resolution_note = ""
            if status in ['Resolved', 'Closed']:
                resolution_note = "Resolved following standard operating procedure and historical knowledge base guidelines."

            assigned_department = {
                'Fraud': 'Admin',
                'Technical': 'Technical Support',
                'Billing': 'Billing',
                'Account': 'Account Support',
                'General Inquiry': 'General Inquiry'
            }.get(cat, 'General Inquiry')
            assigned_agent_id = None if assigned_department == 'Admin' else 2
            assigned_agent_name = 'Administrator' if assigned_department == 'Admin' else agent

            tickets_data.append((
                t_code, 5, c_name, c_email, subject, desc, cat, cat, 92.5, prio, prio, 88.0,
                chan, status, assigned_department, assigned_agent_id, assigned_agent_name,
                sub_date, res_time, sat, "Thank you for the quick support!", resolution_note
            ))

        cursor.executemany('''
            INSERT INTO tickets (
                ticket_code, customer_id, customer_name, customer_email, subject, description,
                category, predicted_category, category_confidence, priority, predicted_priority, priority_confidence,
                channel, status, assigned_department, assigned_agent_id, assigned_agent_name, submission_date,
                resolution_time_hours, satisfaction_score, feedback, resolution_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tickets_data)
        conn.commit()
        print(f"Successfully seeded {len(tickets_data)} tickets into database.")

    conn.close()
    print("Database initialization complete!")

if __name__ == '__main__':
    init_db()
