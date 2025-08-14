from dotenv import load_dotenv
load_dotenv()  

import os
from pathlib import Path

#db config
DB_URL = os.getenv("DB_URL", "sqlite:///./biometric.db")

# Security config

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "mysecretkey-change-in-production")
SECRET_KEY = os.getenv("SECRET_KEY", "jwt-secret-key-change-in-production")

#file upload config
UPLOAD_DIR = Path("uploads")
ID_DOCUMENTS_DIR = UPLOAD_DIR / "id_documents"
LIVE_IMAGES_DIR = UPLOAD_DIR / "live_images"

for directory in [UPLOAD_DIR, ID_DOCUMENTS_DIR, LIVE_IMAGES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# size limits 
MAX_ID_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LIVE_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Allowed  extensions
ALLOWED_ID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_LIVE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# OCR settings
OCR_CONFIDENCE_THRESHOLD = 60 
# Face matching
FACE_MATCH_THRESHOLD = 0.6  
# Liveness detection
LIVENESS_CONFIDENCE_THRESHOLD = 0.7  

# Verification 

VERIFICATION_PASS_THRESHOLD = 0.75  

#dev config
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

def get_upload_path(file_type: str, filename: str) -> Path:
    """Get upload path for a file."""
    if file_type == "id_document":
        return ID_DOCUMENTS_DIR / filename
    elif file_type == "live_image":
        return LIVE_IMAGES_DIR / filename
    return UPLOAD_DIR / filename

def is_valid_file_extension(filename: str, file_type: str) -> bool:
    """Check if file extension is valid."""
    ext = Path(filename).suffix.lower()
    if file_type == "id_document":
        return ext in ALLOWED_ID_EXTENSIONS
    elif file_type == "live_image":
        return ext in ALLOWED_LIVE_EXTENSIONS
    return False
#aarin sample