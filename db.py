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

    # 3. Check if users table exists (even if db file exists, tables might not)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='table' AND name='users'
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
    Ensures standardized demo accounts exist with Password@123.
    Updates existing accounts if they have different credentials.
    This is called during database initialization for viva demo reliability.
    """
    from werkzeug.security import generate_password_hash
    
    # Generate hash for standard demo password
    demo_password_hash = generate_password_hash('Password@123', method='scrypt')
    
    demo_accounts = [
        {
            'email': 'admin@compassiq.com',
            'full_name': 'System Administrator',
            'role': 'admin',
            'department': 'None',
            'account_status': 'APPROVED'
        },
        {
            'email': 'technical@compassiq.com',
            'full_name': 'Technical Support Agent',
            'role': 'agent',
            'department': 'Technical',
            'account_status': 'APPROVED'
        },
        {
            'email': 'billing@compassiq.com',
            'full_name': 'Billing Support Agent',
            'role': 'agent',
            'department': 'Billing',
            'account_status': 'APPROVED'
        },
        {
            'email': 'account@compassiq.com',
            'full_name': 'Account Support Agent',
            'role': 'agent',
            'department': 'Account',
            'account_status': 'APPROVED'
        },
        {
            'email': 'general@compassiq.com',
            'full_name': 'General Inquiry Agent',
            'role': 'agent',
            'department': 'General Inquiry',
            'account_status': 'APPROVED'
        },
        {
            'email': 'customer@compassiq.com',
            'full_name': 'Demo Customer',
            'role': 'customer',
            'department': 'None',
            'account_status': 'APPROVED'
        }
    ]
    
    try:
        cursor = conn.cursor()
        
        for account in demo_accounts:
            # Check if account exists
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (account['email'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing account to ensure correct password and status
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = ?, account_status = ?
                    WHERE email = ?
                """, (demo_password_hash, account['account_status'], account['email']))
                print(f"[CompassIQ DB] Updated demo account: {account['email']}")
            else:
                # Insert new demo account
                cursor.execute("""
                    INSERT INTO users (full_name, email, password_hash, role, department, account_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (account['full_name'], account['email'], demo_password_hash, 
                      account['role'], account['department'], account['account_status']))
                print(f"[CompassIQ DB] Created demo account: {account['email']}")
        
        conn.commit()
        print(f"[CompassIQ DB] Standardized demo accounts ensured (Password@123).")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB Demo Accounts Error] Failed to ensure demo accounts: {e}")
        raise e


# Alias for backward compatibility
init_database = init_db_schema