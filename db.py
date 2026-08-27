"""
CompassIQ — Database Connection and Execution Layer
===================================================
Provides robust SQLite3 connection handling, execution helpers, and automatic
zero-config schema initialization using Python's built-in sqlite3 module.
"""

import os
import sqlite3
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
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

    print(f"[CompassIQ DB] Database path: {Config.DATABASE_PATH}")

    # 1. Check if database file exists
    db_exists = os.path.exists(Config.DATABASE_PATH)
    
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
            return True

        # 4. If users table does not exist, execute schema.sql
        print(f"[CompassIQ DB] Initializing tables & seed data from {schema_path}...")
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found at {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Execute the entire schema as a script
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"[CompassIQ DB] Successfully created tables and seeded default accounts.")
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[CompassIQ DB Init Error] Failed executing schema: {e}")
        raise e
    finally:
        if conn:
            conn.close()


# Alias for backward compatibility
init_database = init_db_schema