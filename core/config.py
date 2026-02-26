import os

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./robotics_lab.db")

    # App Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-prod")
    DEBUG = True
