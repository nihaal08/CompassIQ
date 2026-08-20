# Shared application settings.
class Config:
    SECRET_KEY = "compassiq-secret-key"
    DEBUG = False
    TESTING = False

    # Database connection settings.
    DB_HOST = "localhost"
    DB_PORT = 3306
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "compassiq_db"

    # Data and model locations.
    DATASET_PATH = "dataset/customer_support_data.csv"
    MODEL_DIR = "models"

# Local development settings.
class DevelopmentConfig(Config):
    DEBUG = True

# Production settings.
class ProductionConfig(Config):
    DEBUG = False
