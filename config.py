"""
CompassIQ — Application Configuration Module
============================================
Manages environment variables, database credentials, security keys,
and application defaults with dynamic .env auto-creation and loading.
"""

import os
import shutil
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
DOTENV_EXAMPLE_PATH = os.path.join(BASE_DIR, '.env.example')

# Auto-create .env from .env.example if missing
if not os.path.exists(DOTENV_PATH) and os.path.exists(DOTENV_EXAMPLE_PATH):
    try:
        shutil.copyfile(DOTENV_EXAMPLE_PATH, DOTENV_PATH)
        print("[Config] Created '.env' from '.env.example'.")
    except Exception as e:
        print(f"[Config] Warning creating .env: {e}")

# Load .env variables
if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH, override=True)
else:
    load_dotenv()


class Config:
    # Flask Security Key
    SECRET_KEY = os.getenv('SECRET_KEY', 'compassiq_secret_key_2026')

    # MySQL Database Settings (Supports MYSQL_* and DB_* naming formats)
    DB_HOST = os.getenv('MYSQL_HOST', os.getenv('DB_HOST', 'localhost'))
    DB_PORT = int(os.getenv('MYSQL_PORT', os.getenv('DB_PORT', 3306)))
    DB_USER = os.getenv('MYSQL_USER', os.getenv('DB_USER', 'root'))
    DB_PASSWORD = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', ''))
    DB_NAME = os.getenv('MYSQL_DB', os.getenv('DB_NAME', 'compassiq_db'))

    # Aliases for direct attribute access
    MYSQL_HOST = DB_HOST
    MYSQL_PORT = DB_PORT
    MYSQL_USER = DB_USER
    MYSQL_PASSWORD = DB_PASSWORD
    MYSQL_DB = DB_NAME

    # Session / Cookie settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Model & Storage Paths
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    PLOTS_DIR = os.path.join(BASE_DIR, 'static', 'plots')
