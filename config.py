import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.environ.get("DEBUG", "True") == "True"
    
    # Firebase settings
    DEFAULT_SCHOOL_ID = os.environ.get("DEFAULT_SCHOOL_ID", "harmony-school")
    
    # Legacy PostgreSQL (keep for reference during migration)
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = int(os.environ.get("DB_PORT", 5432))
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_NAME = os.environ.get("DB_NAME")
