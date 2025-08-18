"""
Simplified Main API - Minimal but Complete
All functionality in ~100 lines
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from services import ocr_service, liveness_service, face_match_service
from database import init_database, store_user_session, get_user_session, delete_user_session, store_verification_result, get_stats
import cv2, numpy as np, base64, time, re
from pydantic import BaseModel
from pydantic import BaseModel

class UserRegistration(BaseModel):
    name: str
    age: int
    gender: str
    email: str
    phone: str

class OTPVerification(BaseModel):
    session_id: str
    otp: str

# ADD THESE NEW MODELS:
class LivenessStart(BaseModel):
    user_session_id: str

class LivenessCheck(BaseModel):
    session_id: str
    frame_data: str = ""

app = FastAPI(title="Biometric Verification API")
init_database()
user_sessions = {}  # In-memory user sessions for simplicity

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
    
    # Store in memory for simplicity
    user_sessions[session_id] = {
        "name": user_data.name, "phone": clean_phone,
        "age": user_data.age, "gender": user_data.gender, "email": user_data.email,
        "otp_verified": False, "expires_at": time.time() + 1800,
        "liveness_completed": False, "best_frame": None
    }
    
    return {"session_id": session_id, "message": f"OTP sent to {clean_phone}"}

@app.post("/verify-otp")
async def verify_otp(otp_data: OTPVerification):
    if otp_data.session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_session = user_sessions[otp_data.session_id]
    
    if otp_data.otp != "9999":
        return {"verified": False, "message": "Invalid OTP"}
    
    user_session["otp_verified"] = True
    return {"verified": True, "user_name": user_session["name"]}

@app.get("/user/{session_id}")
async def get_user_info(session_id: str):
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_session = user_sessions[session_id]
    if not user_session.get("otp_verified"):
        raise HTTPException(status_code=404, detail="User not verified")
    
    return {"name": user_session["name"]}

@app.post("/liveness/start")
async def start_liveness(request: LivenessStart):
    user_session_id = request.user_session_id
    
    if user_session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="User session not found")
    
    user_session = user_sessions[user_session_id]
    if not user_session.get("otp_verified"):
        raise HTTPException(status_code=401, detail="Complete OTP verification first")
    
    # Try to create liveness detector with better error handling
    detector = None
    use_real_liveness = False
    error_message = ""
    
    try:
        # First try to import
        from services.liveness_service import LivenessDetector
        print("✅ LivenessDetector import successful")
        
        # Then try to instantiate
        detector = LivenessDetector()
        print("✅ LivenessDetector created successfully")
        use_real_liveness = True
        
    except ImportError as e:
        error_message = f"Import failed: {str(e)}"
        print(f"⚠️ {error_message}")
    except AttributeError as e:
        error_message = f"LivenessDetector class not found: {str(e)}"
        print(f"⚠️ {error_message}")
    except Exception as e:
        error_message = f"Initialization failed: {str(e)}"
        print(f"⚠️ {error_message}")
        import traceback
        traceback.print_exc()
    
    # Create liveness session ID
    liveness_session_id = f"live_{int(time.time())}"
    
    # Store liveness info in user session
    user_sessions[user_session_id]['liveness_detector'] = detector
    user_sessions[user_session_id]['liveness_session_id'] = liveness_session_id
    user_sessions[user_session_id]['liveness_completed'] = False
    user_sessions[user_session_id]['use_real_liveness'] = use_real_liveness
    user_sessions[user_session_id]['liveness_error'] = error_message
    
    if use_real_liveness:
        return {
            "session_id": liveness_session_id,
            "challenge": "head_turn",
            "instruction": "Turn your head left and right slowly",
            "mode": "real_liveness",
            "backend": "MediaPipe" if hasattr(detector, 'use_mediapipe') and detector.use_mediapipe else "OpenCV"
        }
    else:
        # Mock mode for testing when liveness service fails
        return {
            "session_id": liveness_session_id,
            "challenge": "mock_challenge",
            "instruction": "Mock liveness mode - service unavailable",
            "mode": "mock_liveness",
            "error": error_message,
            "note": "You can still test other endpoints"
        }

@app.post("/liveness/check")
async def check_liveness_frame(request: LivenessCheck):
    session_id = request.session_id
    frame_data = request.frame_data
    
    # Find user session by liveness session ID
    user_session_id = None
    for uid, session in user_sessions.items():
        if session.get('liveness_session_id') == session_id:
            user_session_id = uid
            break
    
    if not user_session_id:
        raise HTTPException(status_code=404, detail="Liveness session not found")
    
    user_session = user_sessions[user_session_id]
    
    # If using mock mode, simulate completion after a few frames
    if not user_session.get('use_real_liveness', False):
        # Mock liveness completion
        mock_frame_count = user_session.get('mock_frame_count', 0) + 1
        user_session['mock_frame_count'] = mock_frame_count
        
        if mock_frame_count >= 5:  # Complete after 5 mock frames
            user_session['liveness_completed'] = True
            # Create a simple mock frame for testing
            mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            mock_frame[:] = (100, 150, 200)  # Fill with color
            user_session['best_frame'] = mock_frame
            
            return {
                "status": "completed",
                "instruction": "Mock liveness completed!",
                "frame_count": mock_frame_count,
                "mode": "mock"
            }
        else:
            return {
                "status": "processing",
                "instruction": f"Mock processing... ({mock_frame_count}/5)",
                "frame_count": mock_frame_count,
                "mode": "mock"
            }
    
    # Real liveness processing
    try:
        detector = user_session.get('liveness_detector')
        if not detector:
            raise HTTPException(status_code=500, detail="Liveness detector not initialized")
        
        # Decode frame if provided
        if frame_data:
            try:
                if ',' in frame_data:
                    frame_data = frame_data.split(',')[1]  # Remove data:image/jpeg;base64,
                
                img_bytes = base64.b64decode(frame_data)
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    raise ValueError("Could not decode frame")
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid frame data: {str(e)}")
        else:
            # Create a test frame if no frame provided
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (100, 150, 200)
        
        # Process frame
        result = detector.process_frame(frame)
        
        # If completed, store best frame
        if result.get('status') == 'completed':
            user_session['liveness_completed'] = True
            best_frame = detector.get_best_frame()
            if best_frame is not None:
                user_session['best_frame'] = best_frame
            else:
                user_session['best_frame'] = frame  # Use current frame as fallback
            print(f"✅ Real liveness completed for {user_session_id}")
        
        return result
        
    except Exception as e:
        print(f"❌ Liveness check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Frame processing failed: {str(e)}")

@app.post("/verify-single-stage")
async def verify_single_stage(
    session_id: str = Form(...),
    aadhaar_image: UploadFile = File(...)
):
    # Check user session
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="User session not found")
    
    user_session = user_sessions[session_id]
    
    # Check OTP verified
    if not user_session.get("otp_verified"):
        raise HTTPException(status_code=401, detail="Complete OTP verification first")
    
    # Check liveness completed
    if not user_session.get('liveness_completed', False):
        raise HTTPException(status_code=400, detail="Complete liveness verification first")
    
    # Get best frame from liveness
    best_frame = user_session.get('best_frame')
    if best_frame is None:
        raise HTTPException(status_code=400, detail="No live frame captured")
    
    try:
        # Read Aadhaar image
        aadhaar_content = await aadhaar_image.read()
        aadhaar_array = np.frombuffer(aadhaar_content, np.uint8)
        aadhaar_frame = cv2.imdecode(aadhaar_array, cv2.IMREAD_COLOR)
        
        if aadhaar_frame is None:
            raise HTTPException(status_code=400, detail="Invalid Aadhaar image")
        
        print(f"🔍 Processing verification for {session_id}")
        
        # Extract Aadhaar text
        try:
            from services.ocr_service import extract_aadhaar_text
            aadhaar_text = extract_aadhaar_text(aadhaar_frame)
        except Exception as e:
            print(f"⚠️ OCR failed: {e}")
            aadhaar_text = {}
        
        # Face matching
        try:
            from services.face_match_service import match_faces
            face_result = match_faces(aadhaar_frame, best_frame)
            face_match_passed = face_result.get("match", False)
            similarity = face_result.get("similarity", 0.0)
        except Exception as e:
            print(f"⚠️ Face matching failed: {e}")
            face_match_passed = False
            similarity = 0.0
        
        # Result
        verification_success = face_match_passed
        
        result = {
            "verification_id": f"verify_{int(time.time())}_{session_id[-6:]}",
            "result": "VERIFIED" if verification_success else "FAILED",
            "user_name": user_session["name"],
            "similarity_score": similarity,
            "aadhaar_data": aadhaar_text,
            "timestamp": time.time()
        }
        
        # Store result
        try:
            store_verification_result({
                "verification_id": result["verification_id"],
                "result": result["result"],
                "user_name": user_session["name"],
                "phone_last4": user_session["phone"][-4:],
                "timestamp": result["timestamp"],
                "face_match_confidence": similarity
            })
        except Exception as e:
            print(f"⚠️ Database storage failed: {e}")
        
        print(f"✅ Verification result: {result['result']} ({similarity:.3f})")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    try:
        stats = get_stats()
        stats["active_sessions"] = len(user_sessions)
        return stats
    except Exception as e:
        return {"active_sessions": len(user_sessions), "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)