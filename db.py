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
    
    # Generate hash for standard demo password
    demo_password_hash = generate_password_hash('password123', method='scrypt')
    
    # Department Agents & Admin (staff accounts)
    agent_accounts = [
        {
            'email': 'admin@compassiq.com',
            'agent_name': 'System Administrator',
            'role': 'admin',
            'deptid': None,
            'account_status': 'APPROVED'
        },
        {
            'email': 'tech.support@compassiq.com',
            'agent_name': 'Technical Support Agent',
            'role': 'agent',
            'deptid': 1,  # Technical Support
            'account_status': 'APPROVED'
        },
        {
            'email': 'billing.support@compassiq.com',
            'agent_name': 'Billing Support Agent',
            'role': 'agent',
            'deptid': 2,  # Billing Support
            'account_status': 'APPROVED'
        },
        {
            'email': 'account.support@compassiq.com',
            'agent_name': 'Account Support Agent',
            'role': 'agent',
            'deptid': 3,  # Account Support
            'account_status': 'APPROVED'
        },
        {
            'email': 'general.support@compassiq.com',
            'agent_name': 'General Inquiry Agent',
            'role': 'agent',
            'deptid': 4,  # General Inquiry
            'account_status': 'APPROVED'
        }
    ]
    
    # Customer Accounts (external clients)
    customer_accounts = [
        {
            'email': 'alex.morgan@customer.com',
            'custname': 'Alex Morgan',
            'phone_no': '9876543210',
            'account_status': 'APPROVED'
        }
    ]
    
    try:
        cursor = conn.cursor()
        
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
                # Check if agent exists
                cursor.execute("SELECT agent_id FROM department_agents WHERE email = ?", (account['email'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing agent to ensure correct password and status
                    cursor.execute("""
                        UPDATE department_agents 
                        SET password = ?, account_status = ?
                        WHERE email = ?
                    """, (demo_password_hash, account['account_status'], account['email']))
                    print(f"[CompassIQ DB] Updated demo agent: {account['email']}")
                else:
                    # Insert new demo agent
                    cursor.execute("""
                        INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (account['agent_name'], account['email'], demo_password_hash, 
                          account['deptid'], account['role'], account['account_status']))
                    print(f"[CompassIQ DB] Created demo agent: {account['email']}")
        
        # Insert/update customers
        for account in customer_accounts:
            # Check if customer exists
            cursor.execute("SELECT custid FROM customers WHERE email = ?", (account['email'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing customer to ensure correct password and status
                cursor.execute("""
                    UPDATE customers 
                    SET password = ?, account_status = ?
                    WHERE email = ?
                """, (demo_password_hash, account['account_status'], account['email']))
                print(f"[CompassIQ DB] Updated demo customer: {account['email']}")
            else:
                # Insert new demo customer
                cursor.execute("""
                    INSERT INTO customers (custname, email, password, phone_no, account_status)
                    VALUES (?, ?, ?, ?, ?)
                """, (account['custname'], account['email'], demo_password_hash, 
                      account['phone_no'], account['account_status']))
                print(f"[CompassIQ DB] Created demo customer: {account['email']}")
        
        conn.commit()
        print(f"[CompassIQ DB] Standardized demo accounts ensured (password123).")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB Demo Accounts Error] Failed to ensure demo accounts: {e}")
        raise e


# Alias for backward compatibility
init_database = init_db_schema