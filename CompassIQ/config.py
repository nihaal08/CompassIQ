import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """
    Base configuration class for CompassIQ.
    Reads database credentials and application settings from environment variables.
    """
    SECRET_KEY = os.getenv("SECRET_KEY", "compassiq-development-secret-key")
    DEBUG = False
    TESTING = False

    # MySQL Database Configuration
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "compassiq")

    # ML Artifact Paths
    DATASET_PATH = os.getenv("DATASET_PATH", "dataset/customer_support_data.csv")
    MODEL_DIR = os.getenv("MODEL_DIR", "models")


class DevelopmentConfig(Config):
    """Local development environment configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
