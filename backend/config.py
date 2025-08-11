import os

# Database Config
DB_URL = os.getenv("DB_URL", "sqlite:///./biometric.db")

# Security Keys
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "mysecretkey")
