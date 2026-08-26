"""
CompassIQ — Database Connection and Execution Layer
===================================================
Provides robust MySQL connection handling, friendly error diagnostics, execution
helpers, and automatic zero-config schema initialization using PyMySQL with DictCursor.
"""

import os
import sys
import pymysql
import pymysql.cursors
from config import Config


def get_connection(use_database=True):
    """
    Creates and returns a new MySQL database connection.
    Gracefully catches authentication (1045) and connection errors with actionable guidance.
    """
    try:
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB if use_database else None,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return conn
    except pymysql.err.OperationalError as e:
        error_code = e.args[0] if len(e.args) > 0 else None
        error_msg = e.args[1] if len(e.args) > 1 else str(e)

        if error_code == 1045:
            print("\n" + "!" * 75)
            print(" [CompassIQ Database Authentication Error (1045)]")
            print("!" * 75)
            print(f" -> Access denied for user '{Config.MYSQL_USER}'@'{Config.MYSQL_HOST}'.")
            print(" -> Please update your MySQL password in the '.env' file:")
            print("      MYSQL_PASSWORD=your_actual_mysql_root_password")
            print("!" * 75 + "\n")
        elif error_code in (2003, 2002):
            print("\n" + "!" * 75)
            print(" [CompassIQ MySQL Server Unreachable]")
            print("!" * 75)
            print(f" -> Could not connect to MySQL server at {Config.MYSQL_HOST}:{Config.MYSQL_PORT}.")
            print(" -> Please ensure MySQL service / XAMPP / MariaDB is actively running.")
            print("!" * 75 + "\n")
        else:
            print(f"[CompassIQ DB Error] ({error_code}): {error_msg}")
        raise e
    except Exception as e:
        print(f"[CompassIQ DB Unexpected Error] {e}")
        raise e


def query_db(sql: str, args=(), one: bool = False):
    """
    Executes a SELECT query and returns rows as dictionaries.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"[DB Query Error] {e} | SQL: {sql} | ARGS: {args}")
        raise e
    finally:
        if conn:
            conn.close()


def modify_db(sql: str, args=(), return_last_id: bool = False, return_rowcount: bool = False):
    """
    Executes an INSERT, UPDATE, or DELETE query and commits changes.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
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
    Automatically creates the MySQL database if not present, verifies if tables
    exist (e.g. 'users'), and if missing, parses and executes all SQL statements
    from schema.sql including seed accounts and constraints.
    """
    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

    print(f"[CompassIQ DB] Connecting to MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT} (User: '{Config.MYSQL_USER}')...")

    # 1. Connect without database selected and create DB if not exists
    conn = None
    try:
        conn = get_connection(use_database=False)
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
    except Exception as e:
        raise e
    finally:
        if conn:
            conn.close()

    # 2. Check if tables already exist
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'users'
            """, (Config.MYSQL_DB,))
            table_exists = cursor.fetchone()['count'] > 0

        if table_exists:
            print(f"[CompassIQ DB] Database '{Config.MYSQL_DB}' and tables already initialized. Ready.")
            return True

        # 3. If users table does not exist, parse and execute schema.sql
        print(f"[CompassIQ DB] Initializing tables & seed data from {schema_path}...")
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found at {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

        with conn.cursor() as cursor:
            for stmt in statements:
                if stmt.upper().startswith('USE ') or stmt.startswith('--'):
                    continue
                cursor.execute(stmt)
        conn.commit()
        print(f"[CompassIQ DB] Successfully created tables and seeded default accounts into '{Config.MYSQL_DB}'.")
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
