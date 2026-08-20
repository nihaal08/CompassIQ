"""
CompassIQ - Application Configuration
=======================================
Central configuration for the Flask application and database.

Usage:
    from config import Config
    app.config.from_object(Config)
"""

import os


class Config:
    """
    Base configuration class.
    Sensitive values should be set via environment variables
    in production — never hardcode credentials in version control.
    """

    # --------------------------------------------------------
    # FLASK
    # --------------------------------------------------------

    # Secret key for session management (change in production)
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "compassiq-secret-key-change-in-production"
    )

    DEBUG = False

    TESTING = False


    # --------------------------------------------------------
    # DATABASE (MySQL)
    # --------------------------------------------------------

    DB_HOST     = os.environ.get("DB_HOST",     "localhost")
    DB_PORT     = int(os.environ.get("DB_PORT", "3306"))
    DB_USER     = os.environ.get("DB_USER",     "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME     = os.environ.get("DB_NAME",     "compassiq_db")


    # --------------------------------------------------------
    # AI MODEL PATHS
    # --------------------------------------------------------

    BASE_DIR  = os.path.dirname(os.path.abspath(__file__))

    MODEL_DIR = os.path.join(BASE_DIR, "models")

    DATASET_PATH = os.path.join(
        BASE_DIR,
        "dataset",
        "customer_support_data.csv"
    )


    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    TICKETS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Configuration for local development."""

    DEBUG = True


class ProductionConfig(Config):
    """Configuration for production deployment."""

    DEBUG = False
