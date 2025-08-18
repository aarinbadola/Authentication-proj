"""
Simplified Main API - Minimal but Complete
All functionality in ~100 lines
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from services import ocr_service, liveness_service, face_match_service
from database import init_database, store_user_session, get_user_session, delete_user_session, store_verification_result
import cv2, numpy as np, base64, time, re
from pydantic import BaseModel

app = FastAPI(title="Biometric Verification API")
init_database()
sessions = {}  # Active liveness sessions

class UserRegistration(BaseModel):
    name: str
    age: int
    gender: str
    email: str
    phone: str

class OTPVerification(BaseModel):
    session_id: str
    otp: str

@app.get("/")
async def root():
    return {"message": "Biometric Verification API", "version": "1.0"}

@app.post("/register-user")
async def register_user(user_data: UserRegistration):
    # Phone validation - 10 digits only
    clean_phone = re.sub(r'[^\d]', '', user_data.phone)
    if len(clean_phone) != 10:
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")
    
    session_id = f"user_{int(time.time())}_{clean_phone[-4:]}"
    print(f"📱 OTP for {clean_phone}: 9999")
    
    store_user_session(session_id, {
        "name": user_data.name, "phone": clean_phone,
        "age": user_data.age, "gender": user_data.gender, "email": user_data.email,
        "otp_verified": False, "expires_at": time.time() + 1800
    })
    
    return {"session_id": session_id, "message": f"OTP sent to {clean_phone}"}

@app.post("/verify-otp")
async def verify_otp(otp_data: OTPVerification):
    user_session = get_user_session(otp_data.session_id)
    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if otp_data.otp != "9999":
        return {"verified": False, "message": "Invalid OTP"}
    
    user_session["otp_verified"] = True
    store_user_session(otp_data.session_id, user_session)
    return {"verified": True, "user_name": user_session["name"]}

@app.get("/user/{session_id}")
async def get_user_info(session_id: str):
    user_session = get_user_session(session_id)
    if not user_session or not user_session.get("otp_verified"):
        raise HTTPException(status_code=404, detail="User not verified")
    return {"name": user_session["name"]}

@app.post("/liveness/start")
async def start_liveness(session_id: str):
    from services.liveness_service import SimpleLivenessDetector
    detector = SimpleLivenessDetector()
    sessions[session_id] = detector
    
    challenge = detector.challenges[detector.current_challenge]
    instruction = challenge['name']
    if detector.current_challenge == 'head_turn':
        instruction = f"Turn your head {detector.turn_direction}"
    
    return {"session_id": session_id, "challenge": detector.current_challenge, 
            "instruction": instruction, "timeout": challenge['timeout']}

@app.post("/liveness/check")
async def check_liveness_frame(session_id: str, frame_data: dict):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        detector = sessions[session_id]
        
        # Decode frame - handle both formats
        frame_b64 = frame_data.get("frame", "")
        if ',' in frame_b64:
            frame_b64 = frame_b64.split(',')[1]
        
        img_bytes = base64.b64decode(frame_b64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid frame data")
        
        result = detector.process_frame(frame)
        if result['status'] == 'timeout':
            sessions.pop(session_id, None)
        
        return result
    
    except Exception as e:
        sessions.pop(session_id, None)  # Cleanup on error
        raise HTTPException(status_code=500, detail=f"Frame processing failed: {str(e)}")

@app.post("/verify-single-stage")
async def verify_single_stage(user_session_id: str, liveness_session_id: str, aadhaar_image: UploadFile = File(...)):
    try:
        # Check user session
        user_session = get_user_session(user_session_id)
        if not user_session or not user_session.get("otp_verified"):
            raise HTTPException(status_code=401, detail="User not verified")
        
        # Check liveness
        if liveness_session_id not in sessions:
            raise HTTPException(status_code=404, detail="Liveness session not found")
        
        detector = sessions[liveness_session_id]
        if not detector.completed:
            raise HTTPException(status_code=400, detail="Complete liveness first")
        
        best_frame = detector.get_best_frame()
        if best_frame is None:
            raise HTTPException(status_code=400, detail="No quality frame captured")
        
        # Process Aadhaar
        aadhaar_content = await aadhaar_image.read()
        aadhaar_array = np.frombuffer(aadhaar_content, np.uint8)
        aadhaar_frame = cv2.imdecode(aadhaar_array, cv2.IMREAD_COLOR)
        
        if aadhaar_frame is None:
            raise HTTPException(status_code=400, detail="Invalid Aadhaar image")
        
        # Face matching
        face_result = await face_match_service.compare_faces_single_stage(aadhaar_frame, best_frame)
        
        # Final result
        face_match_passed = face_result.get("match_confidence", 0) > 0.6
        verification_success = detector.completed and face_match_passed
        
        result = {
            "verification_id": f"verify_{int(time.time())}_{user_session_id[-6:]}",
            "result": "VERIFIED" if verification_success else "FAILED",
            "user_name": user_session["name"],
            "face_match_confidence": face_result.get("match_confidence", 0),
            "timestamp": time.time()
        }
        
        # Store in database
        store_verification_result({
            "verification_id": result["verification_id"],
            "result": result["result"],
            "user_name": user_session["name"],
            "phone_last4": user_session["phone"][-4:],
            "timestamp": result["timestamp"],
            "face_match_confidence": result["face_match_confidence"]
        })
        
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
    finally:
        # Always cleanup
        sessions.pop(liveness_session_id, None)
        delete_user_session(user_session_id)

@app.get("/stats")
async def get_stats():
    from database import get_stats
    stats = get_stats()
    stats["active_sessions"] = len(sessions)
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)