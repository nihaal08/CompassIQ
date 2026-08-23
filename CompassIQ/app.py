"""
=============================================================================
CompassIQ - AI Powered Ticket Management System
Phase 1: Flask Application & Database Connectivity Setup
=============================================================================
"""

import os
from flask import Flask, render_template, g, jsonify
import mysql.connector
from mysql.connector import Error
from config import DevelopmentConfig, Config

# 1. Initialize Flask Application
app = Flask(__name__)

# 2. Load Configuration
app.config.from_object(DevelopmentConfig)


# =============================================================================
# Database Helper Functions
# =============================================================================

def get_db_connection():
    """
    Creates and returns a new MySQL database connection using credentials
    loaded from the application configuration.
    
    Returns:
        tuple: (connection_object, error_message)
               If successful, connection_object is returned and error_message is None.
               If failed, connection_object is None and error_message contains details.
    """
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            port=app.config['MYSQL_PORT'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DATABASE']
        )
        if connection.is_connected():
            return connection, None
        return None, "Failed to connect to MySQL database."
    except Error as e:
        return None, str(e)


def get_db():
    """
    Retrieves the unique database connection for the active request context.
    Caches the connection inside Flask's 'g' global object to avoid duplicate
    connections within the same request lifecycle.
    """
    if 'db' not in g:
        conn, err = get_db_connection()
        if err:
            raise ConnectionError(f"Database connection error: {err}")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db_connection(exception=None):
    """
    Automatically closes the database connection when the request context tears down.
    Ensures no dangling connections or memory leaks exist.
    """
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()


# =============================================================================
# Phase 1 Flask Routes
# =============================================================================

@app.route("/", methods=["GET"])
def index():
    """
    Landing page for CompassIQ.
    Renders the main project overview, architecture modules, and action placeholders.
    """
    return render_template("base.html")


@app.route("/test-db", methods=["GET"])
def test_db():
    """
    Tests MySQL database connectivity and reports diagnostic status.
    Displays 'Database connection successful' when accessible.
    """
    conn, error_msg = get_db_connection()

    db_info = {
        "host": app.config['MYSQL_HOST'],
        "port": app.config['MYSQL_PORT'],
        "user": app.config['MYSQL_USER'],
        "database": app.config['MYSQL_DATABASE'],
        "server_version": "Unknown"
    }

    if error_msg:
        # Connection Failed: Return error page without exposing raw passwords
        return render_template(
            "test_db.html",
            success=False,
            error_message=error_msg,
            db_info=db_info,
            tables=[],
            departments=[]
        ), 500

    tables = []
    departments = []

    try:
        cursor = conn.cursor(dictionary=True)

        # Retrieve MySQL Server version
        cursor.execute("SELECT VERSION() AS version;")
        version_result = cursor.fetchone()
        if version_result:
            db_info["server_version"] = version_result["version"]

        # Retrieve existing tables in the database
        cursor.execute("SHOW TABLES;")
        raw_tables = cursor.fetchall()
        for row in raw_tables:
            tables.extend(row.values())

        # Retrieve seeded departments if the departments table exists
        if "departments" in tables:
            cursor.execute("SELECT id, department_name FROM departments ORDER BY id ASC;")
            departments = cursor.fetchall()

        cursor.close()

        return render_template(
            "test_db.html",
            success=True,
            db_info=db_info,
            tables=tables,
            departments=departments
        )

    except Error as e:
        return render_template(
            "test_db.html",
            success=False,
            error_message=f"Database Query Error: {str(e)}",
            db_info=db_info,
            tables=[],
            departments=[]
        ), 500

    finally:
        # Always close direct test connection
        if conn and conn.is_connected():
            conn.close()


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run in debug mode only for local development
    app.run(debug=True, host="127.0.0.1", port=5000)
