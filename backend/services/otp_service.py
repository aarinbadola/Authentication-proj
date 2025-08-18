"""
Simple Demo OTP Service - Always returns 9999
Perfect for college project with essential features
"""

import time
from typing import Dict

# Simple storage for OTP sessions
otp_sessions = {}

def send_otp(phone: str) -> Dict[str, any]:
    """Send demo OTP and show in console"""
    if len(phone) != 10:
        return {"success": False, "message": "Phone must be 10 digits"}
    
    # Store session with timestamp
    otp_sessions[phone] = {"otp": "9999", "time": time.time(), "attempts": 0}
    
    # Demo console display
    print(f"📱 OTP for {phone}: 9999")
    
    return {"success": True, "message": f"OTP sent to {phone}"}

def verify_otp(phone: str, entered_otp: str) -> Dict[str, any]:
    """Verify OTP with basic session management"""
    
    # Check if session exists
    if phone not in otp_sessions:
        return {"success": False, "message": "Please request OTP first"}
    
    session = otp_sessions[phone]
    
    # Check if expired (5 minutes)
    if time.time() - session["time"] > 300:
        del otp_sessions[phone]
        return {"success": False, "message": "OTP expired. Request new one"}
    
    # Check attempts (max 3)
    if session["attempts"] >= 3:
        del otp_sessions[phone]
        return {"success": False, "message": "Too many attempts. Request new OTP"}
    
    session["attempts"] += 1
    
    # Verify OTP
    if entered_otp == "9999":
        del otp_sessions[phone]  # Clean up
        return {"success": True, "message": "OTP verified successfully"}
    else:
        remaining = 3 - session["attempts"]
        return {"success": False, "message": f"Invalid OTP. {remaining} attempts left (Hint: 9999)"}

# Simple test
def test_otp():
    print("🎯 Testing Demo OTP...")
    
    # Test send
    result = send_otp("9876543210")
    print(f"Send: {result}")
    
    # Test verify correct
    result = verify_otp("9876543210", "9999")
    print(f"Verify correct: {result}")
    
    # Test wrong OTP
    send_otp("1234567890")
    result = verify_otp("1234567890", "1234")
    print(f"Verify wrong: {result}")
    
    print("🚀 Demo OTP ready!")

if __name__ == "__main__":
    test_otp()