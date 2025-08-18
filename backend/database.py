"""
Simplified Database for Biometric Verification System
Minimal code with essential functionality only
"""

import sqlite3
import time
from typing import Dict, Optional

DATABASE_NAME = "biometric_verification.db"

# In-memory user sessions (temporary storage for security)
user_sessions: Dict[str, dict] = {}

def init_database():
    """Initialize database with required tables"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Verification results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verification_id TEXT,
            result TEXT,
            user_name TEXT,
            phone_last4 TEXT,
            timestamp REAL,
            face_match_confidence REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Simple stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            total_verifications INTEGER DEFAULT 0,
            successful_verifications INTEGER DEFAULT 0,
            total_sessions INTEGER DEFAULT 0
        )
    """)
    
    # Initialize stats if empty
    cursor.execute("SELECT COUNT(*) FROM stats")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO stats VALUES (0, 0, 0)")
    
    conn.commit()
    conn.close()
    return True

def store_user_session(session_id: str, session_data: dict):
    """Store user session temporarily in memory"""
    user_sessions[session_id] = session_data
    update_stats("total_sessions", 1)
    return True

def get_user_session(session_id: str) -> Optional[dict]:
    """Get user session if not expired"""
    session_data = user_sessions.get(session_id)
    if not session_data:
        return None
    
    # Check expiry
    current_time = time.time()
    if current_time > session_data.get("expires_at", 0):
        user_sessions.pop(session_id, None)
        return None
    
    return session_data

def delete_user_session(session_id: str):
    """Delete user session (cleanup)"""
    user_sessions.pop(session_id, None)
    return True

def store_verification_result(verification_data: dict):
    """Store final verification result"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO verification_results 
        (verification_id, result, user_name, phone_last4, timestamp, face_match_confidence) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        verification_data.get("verification_id"),
        verification_data.get("result"),
        verification_data.get("user_name"),
        verification_data.get("phone_last4"),
        verification_data.get("timestamp"),
        verification_data.get("face_match_confidence")
    ))
    
    conn.commit()
    conn.close()
    
    # Update stats
    update_stats("total_verifications", 1)
    if verification_data.get("result") == "VERIFIED":
        update_stats("successful_verifications", 1)
    
    return True

def update_stats(stat_name: str, increment: int = 1):
    """Update statistics"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute(f"UPDATE stats SET {stat_name} = {stat_name} + ?", (increment,))
    
    conn.commit()
    conn.close()
    return True

def get_stats() -> dict:
    """Get system statistics"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM stats")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"total_verifications": 0, "successful_verifications": 0, "success_rate": 0}
    
    total, successful, sessions = row
    success_rate = round((successful / total * 100) if total > 0 else 0, 1)
    
    return {
        "total_verifications": total,
        "successful_verifications": successful,
        "total_sessions": sessions,
        "success_rate": f"{success_rate}%",
        "active_sessions": len(user_sessions)
    }

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    current_time = time.time()
    expired = [sid for sid, data in user_sessions.items() 
               if current_time > data.get("expires_at", 0)]
    
    for session_id in expired:
        user_sessions.pop(session_id)
    
    return len(expired)

# Simple test function
def test_database():
    """Test basic functionality"""
    print("🎯 Testing Database...")
    
    if init_database():
        print("✅ Database initialized")
    
    # Test session
    test_session = {
        "name": "Test User",
        "phone": "1234567890",
        "created_at": time.time(),
        "expires_at": time.time() + 1800
    }
    
    store_user_session("test_123", test_session)
    if get_user_session("test_123"):
        print("✅ Session storage works")
    
    delete_user_session("test_123")
    print("✅ Database ready!")

if __name__ == "__main__":
    test_database()