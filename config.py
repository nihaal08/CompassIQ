"""
CompassIQ — Application Configuration Module
============================================
Manages environment variables, database configuration, security keys,
and application defaults with dynamic .env auto-creation and loading.
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (parent of this file)
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables if .env exists
DOTENV_PATH = BASE_DIR / '.env'
if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH, override=True)
else:
    load_dotenv()


class Config:
    # Flask Security Key
    SECRET_KEY = 'compassiq-mca-secret-key'
    
    # CSRF Protection Settings - Disabled for viva demo reliability
    WTF_CSRF_ENABLED = False
    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_TIME_LIMIT = None

    # SQLite3 Database Settings - Updated with new structure
    DATABASE_DIR = BASE_DIR / 'database' / 'storage'
    DATABASE_PATH = str(DATABASE_DIR / 'compassiq.db')
    
    # Ensure database directory exists
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    # Schema file path for initialization
    SCHEMA_DIR = BASE_DIR / 'database' / 'schema'
    SCHEMA_PATH = str(SCHEMA_DIR / 'schema.sql')

    # Session / Cookie settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Model & Storage Paths
    MODELS_DIR = BASE_DIR / 'models'
    PLOTS_DIR = BASE_DIR / 'static' / 'plots'