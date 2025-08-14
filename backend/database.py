from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Silence SQLAlchemy 2.0 warning
import os
os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1'

# Database URL from environment
DATABASE_URL = os.getenv("DB_URL", "sqlite:///./biometric.db")

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class User(Base):
    """User information and personal details"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    verification_sessions = relationship("VerificationSession", back_populates="user")


class VerificationSession(Base):
    """Individual verification attempts"""
    __tablename__ = "verification_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, nullable=False)  # For tracking
    status = Column(String, default="pending")  # pending, in_progress, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Verification steps completion
    ocr_completed = Column(Boolean, default=False)
    liveness_completed = Column(Boolean, default=False)
    face_match_completed = Column(Boolean, default=False)
    
    # Overall verification result
    verification_passed = Column(Boolean, default=False)
    failure_reason = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="verification_sessions")
    documents = relationship("Document", back_populates="session")
    live_images = relationship("LiveImage", back_populates="session")
    verification_results = relationship("VerificationResult", back_populates="session")


class Document(Base):
    """Uploaded government ID documents"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("verification_sessions.id"), nullable=False)
    file_path = Column(String, nullable=False)  # Path to uploaded file
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # jpg, png, pdf, etc.
    file_size = Column(Integer, nullable=False)  # in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # OCR extracted data (encrypted)
    extracted_data_encrypted = Column(LargeBinary, nullable=True)  # JSON data, encrypted
    ocr_confidence = Column(Integer, nullable=True)  # 0-100 confidence score
    
    # Document validation
    is_valid_document = Column(Boolean, default=False)
    document_type = Column(String, nullable=True)  # passport, driver_license, id_card, etc.
    
    # Relationships
    session = relationship("VerificationSession", back_populates="documents")


class LiveImage(Base):
    """Live captured images for liveness detection and face matching"""
    __tablename__ = "live_images"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("verification_sessions.id"), nullable=False)
    file_path = Column(String, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow)
    
    # Liveness detection results
    is_live = Column(Boolean, default=False)
    liveness_confidence = Column(Integer, nullable=True)  # 0-100 confidence score
    liveness_details = Column(Text, nullable=True)  # JSON details about detection
    
    # Face detection
    faces_detected = Column(Integer, default=0)
    face_coordinates = Column(Text, nullable=True)  # JSON with face bounding boxes
    
    # Relationships
    session = relationship("VerificationSession", back_populates="live_images")


class VerificationResult(Base):
    """Final verification results and matching scores"""
    __tablename__ = "verification_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("verification_sessions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Face matching results
    face_match_score = Column(Integer, nullable=True)  # 0-100 similarity score
    face_match_threshold = Column(Integer, default=75)  # Minimum score to pass
    face_match_passed = Column(Boolean, default=False)
    
    # Overall verification score
    overall_score = Column(Integer, nullable=True)  # Combined score from all checks
    risk_level = Column(String, default="medium")  # low, medium, high
    
    # Additional verification details
    verification_details = Column(Text, nullable=True)  # JSON with detailed results
    processing_time = Column(Integer, nullable=True)  # Processing time in milliseconds
    
    # Relationships
    session = relationship("VerificationSession", back_populates="verification_results")


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database with tables"""
    print("Creating database tables...")
    create_tables()
    print("Database initialized successfully!")


# Run this when importing to ensure tables exist
if __name__ == "__main__":
    init_database()