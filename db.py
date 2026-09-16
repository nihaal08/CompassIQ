"""
CompassIQ — Database Connection and Execution Layer
===================================================
Provides robust SQLite3 connection handling, execution helpers, and automatic
zero-config schema initialization using Python's built-in sqlite3 module.
"""

import os
import sqlite3
from pathlib import Path
from config import Config


def get_connection():
    """
    Creates and returns a new SQLite3 database connection.
    Enables foreign keys and sets row factory for dictionary-like access.
    """
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key constraints
        return conn
    except Exception as e:
        print(f"[CompassIQ DB Error] Failed to connect to database: {e}")
        raise e


def query_db(sql: str, args=(), one: bool = False):
    """
    Executes a SELECT query and returns rows as dictionaries.
    Uses SQLite parameter placeholders (?).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, args)
        rv = cursor.fetchall()
        
        # Convert sqlite3.Row objects to dictionaries
        result = [dict(row) for row in rv]
        return (result[0] if result else None) if one else result
    except Exception as e:
        print(f"[DB Query Error] {e} | SQL: {sql} | ARGS: {args}")
        raise e
    finally:
        if conn:
            conn.close()


def modify_db(sql: str, args=(), return_last_id: bool = False, return_rowcount: bool = False):
    """
    Executes an INSERT, UPDATE, or DELETE query and commits changes.
    Uses SQLite parameter placeholders (?).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, args)
        conn.commit()
        
        if return_last_id:
            return cursor.lastrowid
        if return_rowcount:
            return cursor.rowcount
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB Modify Error] {e} | SQL: {sql} | ARGS: {args}")
        raise e
    finally:
        if conn:
            conn.close()


def init_db_schema(schema_path: str = None):
    """
    Automatically initializes the SQLite database if not present.
    Checks if the database file or 'users' table exists, and if missing,
    executes schema.sql via executescript() to create tables and seed data.
    """
    if schema_path is None:
        schema_path = Config.SCHEMA_PATH

    print(f"[CompassIQ DB] Database path: {Config.DATABASE_PATH}")
    print(f"[CompassIQ DB] Schema path: {schema_path}")

    # 1. Check if database file exists
    db_exists = Path(Config.DATABASE_PATH).exists()
    
    # 2. If database doesn't exist, create it and initialize schema
    if not db_exists:
        print(f"[CompassIQ DB] Database file not found. Creating new database...")
        try:
            # Create the database file by connecting
            conn = get_connection()
            conn.close()
            print(f"[CompassIQ DB] Created database file: {Config.DATABASE_PATH}")
        except Exception as e:
            print(f"[CompassIQ DB Error] Failed to create database file: {e}")
            raise e

    # 3. Check if customers table exists (even if db file exists, tables might not)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name='customers'
        """)
        table_exists = cursor.fetchone()['count'] > 0

        if table_exists:
            print(f"[CompassIQ DB] Database schema already initialized. Ready.")
            # Ensure standardized demo accounts exist even if schema exists
            ensure_demo_accounts(conn)
            return True

        # 4. If users table does not exist, execute schema.sql
        print(f"[CompassIQ DB] Initializing tables & seed data from {schema_path}...")
        if not Path(schema_path).exists():
            raise FileNotFoundError(f"Schema file not found at {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Execute the entire schema as a script
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"[CompassIQ DB] Successfully created tables and seeded default accounts.")
        
        # Ensure standardized demo accounts exist after schema creation
        ensure_demo_accounts(conn)
        
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[CompassIQ DB Init Error] Failed executing schema: {e}")
        raise e
    finally:
        if conn:
            conn.close()


def ensure_demo_accounts(conn):
    """
    Ensures standardized demo accounts exist with password123.
    Updates existing accounts if they have different credentials.
    This is called during database initialization for viva demo reliability.
    Separates staff (department_agents) from clients (customers).
    """
    from werkzeug.security import generate_password_hash
    
    # Pre-generate hashes for standard demo credentials
    admin_pwd_hash = generate_password_hash('Admin@123', method='scrypt')
    agent_pwd_hash = generate_password_hash('Agent@123', method='scrypt')
    user_pwd_hash = generate_password_hash('User@123', method='scrypt')
    
    # Clean, strictly standardized demo accounts (1 per role/department)
    agent_accounts = [
        {
            'email': 'admin@compassiq.com',
            'agent_name': 'System Administrator',
            'role': 'admin',
            'deptid': None,
            'password_hash': admin_pwd_hash,
            'account_status': 'APPROVED'
        },
        {
            'email': 'tech.agent@compassiq.com',
            'agent_name': 'Technical Support Agent',
            'role': 'agent',
            'deptid': 1,  # Technical
            'password_hash': agent_pwd_hash,
            'account_status': 'APPROVED'
        },
        {
            'email': 'billing.agent@compassiq.com',
            'agent_name': 'Billing Support Agent',
            'role': 'agent',
            'deptid': 2,  # Billing
            'password_hash': agent_pwd_hash,
            'account_status': 'APPROVED'
        },
        {
            'email': 'account.agent@compassiq.com',
            'agent_name': 'Account Support Agent',
            'role': 'agent',
            'deptid': 3,  # Account
            'password_hash': agent_pwd_hash,
            'account_status': 'APPROVED'
        },
        {
            'email': 'general.agent@compassiq.com',
            'agent_name': 'General Inquiry Agent',
            'role': 'agent',
            'deptid': 4,  # General Inquiry
            'password_hash': agent_pwd_hash,
            'account_status': 'APPROVED'
        },
        {
            'email': 'fraud.agent@compassiq.com',
            'agent_name': 'Fraud & Security Agent',
            'role': 'agent',
            'deptid': 5,  # Fraud & Security
            'password_hash': agent_pwd_hash,
            'account_status': 'APPROVED'
        }
    ]
    
    customer_accounts = [
        {
            'email': 'customer@compassiq.com',
            'custname': 'Customer Client',
            'phone_no': '9876543210',
            'password_hash': user_pwd_hash,
            'account_status': 'APPROVED'
        }
    ]
    
    try:
        cursor = conn.cursor()

        # Ensure departments table contains Fraud & Security (deptid = 5)
        cursor.execute("SELECT deptid FROM departments WHERE deptid = 5")
        d5 = cursor.fetchone()
        if d5:
            cursor.execute("UPDATE departments SET deptname = 'Fraud & Security', sla_target_hours = 12 WHERE deptid = 5")
        else:
            cursor.execute("INSERT OR REPLACE INTO departments (deptid, deptname, sla_target_hours) VALUES (5, 'Fraud & Security', 12)")
        
        # Ensure customer_feedback column exists in complaints table
        cursor.execute("PRAGMA table_info(complaints)")
        complaints_cols = [col['name'] for col in cursor.fetchall()]
        if 'customer_feedback' not in complaints_cols:
            cursor.execute("ALTER TABLE complaints ADD COLUMN customer_feedback TEXT DEFAULT NULL")
            print("[CompassIQ DB] Added customer_feedback column to complaints table.")
        
        # Ensure department_agents table exists before inserting
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name='department_agents'
        """)
        agents_table_exists = cursor.fetchone()['count'] > 0
        
        # Insert/update department agents
        if agents_table_exists:
            for account in agent_accounts:
                cursor.execute("SELECT agent_id FROM department_agents WHERE LOWER(email) = LOWER(?)", (account['email'],))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute("""
                        UPDATE department_agents 
                        SET password = ?, account_status = ?, role = ?, deptid = ?, agent_name = ?
                        WHERE LOWER(email) = LOWER(?)
                    """, (account['password_hash'], account['account_status'], account['role'], account['deptid'], account['agent_name'], account['email']))
                    print(f"[CompassIQ DB] Updated demo agent: {account['email']}")
                else:
                    cursor.execute("""
                        INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (account['agent_name'], account['email'], account['password_hash'], 
                          account['deptid'], account['role'], account['account_status']))
                    print(f"[CompassIQ DB] Created demo agent: {account['email']}")
        
        # Insert/update customer
        for account in customer_accounts:
            cursor.execute("SELECT custid FROM customers WHERE LOWER(email) = LOWER(?)", (account['email'],))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE customers 
                    SET password = ?, account_status = ?, custname = ?
                    WHERE LOWER(email) = LOWER(?)
                """, (account['password_hash'], account['account_status'], account['custname'], account['email']))
                print(f"[CompassIQ DB] Updated demo customer: {account['email']}")
            else:
                cursor.execute("""
                    INSERT INTO customers (custname, email, password, phone_no, account_status)
                    VALUES (?, ?, ?, ?, ?)
                """, (account['custname'], account['email'], account['password_hash'], 
                      account['phone_no'], account['account_status']))
                print(f"[CompassIQ DB] Created demo customer: {account['email']}")
                
        # Remap foreign keys before purging duplicate accounts
        # 1. Remap complaints custid to retained customer@compassiq.com
        cursor.execute("SELECT custid FROM customers WHERE LOWER(email) = 'customer@compassiq.com'")
        primary_cust = cursor.fetchone()
        if primary_cust:
            p_custid = primary_cust['custid']
            cursor.execute("UPDATE complaints SET custid = ? WHERE custid != ?", (p_custid, p_custid))
            cursor.execute("UPDATE ticket_replies SET sender_id = ? WHERE sender_id IN (SELECT custid FROM customers WHERE custid != ?)", (p_custid, p_custid))

        # 2. Remap assigned agents in complaints to retained agents per department
        cursor.execute("SELECT agent_id FROM department_agents WHERE LOWER(email) = 'tech.agent@compassiq.com'")
        tech_agent = cursor.fetchone()
        if tech_agent:
            cursor.execute("UPDATE complaints SET assigned_agent_id = ? WHERE deptid = 1", (tech_agent['agent_id'],))

        cursor.execute("SELECT agent_id FROM department_agents WHERE LOWER(email) = 'billing.agent@compassiq.com'")
        bill_agent = cursor.fetchone()
        if bill_agent:
            cursor.execute("UPDATE complaints SET assigned_agent_id = ? WHERE deptid = 2", (bill_agent['agent_id'],))

        cursor.execute("SELECT agent_id FROM department_agents WHERE LOWER(email) = 'account.agent@compassiq.com'")
        acct_agent = cursor.fetchone()
        if acct_agent:
            cursor.execute("UPDATE complaints SET assigned_agent_id = ? WHERE deptid = 3", (acct_agent['agent_id'],))

        cursor.execute("SELECT agent_id FROM department_agents WHERE LOWER(email) = 'general.agent@compassiq.com'")
        gen_agent = cursor.fetchone()
        if gen_agent:
            cursor.execute("UPDATE complaints SET assigned_agent_id = ? WHERE deptid = 4", (gen_agent['agent_id'],))

        cursor.execute("SELECT agent_id FROM department_agents WHERE LOWER(email) = 'fraud.agent@compassiq.com'")
        fraud_agent = cursor.fetchone()
        if fraud_agent:
            cursor.execute("UPDATE complaints SET assigned_agent_id = ? WHERE deptid = 5", (fraud_agent['agent_id'],))

        # 3. Purge duplicate department agents and customers
        cursor.execute("""
            DELETE FROM department_agents 
            WHERE LOWER(email) NOT IN (
                'admin@compassiq.com', 
                'tech.agent@compassiq.com', 
                'billing.agent@compassiq.com', 
                'account.agent@compassiq.com', 
                'general.agent@compassiq.com',
                'fraud.agent@compassiq.com'
            )
        """)
        cursor.execute("""
            DELETE FROM customers 
            WHERE LOWER(email) NOT IN ('customer@compassiq.com')
        """)
        print("[CompassIQ DB] Duplicate demo accounts purged and foreign keys remapped.")
                
        # Ensure unified users view exists with clean role, department, and active status
        cursor.execute("DROP VIEW IF EXISTS users;")
        cursor.execute("""
            CREATE VIEW users AS
            SELECT 
                custid AS user_id,
                custname AS full_name,
                email,
                password AS password_hash,
                'customer' AS role,
                NULL AS department,
                phone_no AS bill_no_product_id,
                'active' AS account_status,
                created_at
            FROM customers
            UNION ALL
            SELECT 
                agent_id AS user_id,
                agent_name AS full_name,
                email,
                password AS password_hash,
                role,
                CASE 
                    WHEN deptid = 1 THEN 'Technical'
                    WHEN deptid = 2 THEN 'Billing'
                    WHEN deptid = 3 THEN 'Account'
                    WHEN deptid = 4 THEN 'General Inquiry'
                    WHEN deptid = 5 THEN 'Fraud & Security'
                    WHEN (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid) LIKE '%Technical%' THEN 'Technical'
                    WHEN (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid) LIKE '%Billing%' THEN 'Billing'
                    WHEN (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid) LIKE '%Account%' THEN 'Account'
                    WHEN (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid) LIKE '%General%' THEN 'General Inquiry'
                    WHEN (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid) LIKE '%Fraud%' THEN 'Fraud & Security'
                    WHEN (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid) LIKE '%Security%' THEN 'Fraud & Security'
                    ELSE (SELECT deptname FROM departments WHERE departments.deptid = department_agents.deptid)
                END AS department,
                NULL AS bill_no_product_id,
                'active' AS account_status,
                created_at
            FROM department_agents;
        """)
        conn.commit()
        print(f"[CompassIQ DB] Standardized demo accounts ensured.")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB Demo Accounts Error] Failed to ensure demo accounts: {e}")
        raise e


# Alias for backward compatibility
init_database = init_db_schema