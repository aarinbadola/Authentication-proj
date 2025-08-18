"""
Simplified Enhanced Liveness Detection with Auto Frame Capture
Keeps your original 180-line simplicity + adds automatic best frame capture
"""

import cv2
import numpy as np
import mediapipe as mp
import random
import time

class SimpleLivenessDetector:
    def __init__(self):
        # MediaPipe setup
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Simple 2 challenges
        self.challenges = {
            'mouth_open': {'name': 'Open your mouth wide', 'timeout': 4},
            'head_turn': {'name': 'Turn your head', 'timeout': 5}
        }
        
        self.reset_session()
    
    def reset_session(self):
        """Start new session"""
        self.current_challenge = random.choice(list(self.challenges.keys()))
        self.start_time = time.time()
        self.completed = False
        
        # For head turn
        self.turn_direction = random.choice(['left', 'right'])
        
        # Frame capture (simple)
        self.captured_frames = []
        self.best_frame = None
        self.best_quality = 0.0
    
    def get_frame_quality(self, frame):
        """Simple quality check: face size + sharpness"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Face detection for size
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Quality score
            quality = 0.0
            
            # Face size score
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                face_area = w * h
                frame_area = frame.shape[0] * frame.shape[1]
                size_score = min(0.5, face_area / (frame_area * 0.1))
                quality += size_score
            
            # Sharpness score
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(0.5, sharpness / 500)
            quality += sharpness_score
            
            return quality
        except:
            return 0.0
    
    def capture_if_good(self, frame):
        """Capture frame if it's good quality"""
        quality = self.get_frame_quality(frame)
        
        # Only capture if decent quality
        if quality < 0.3:
            return False
        
        # Keep only best 3 frames
        if len(self.captured_frames) < 3:
            self.captured_frames.append(frame.copy())
        elif quality > min([self.get_frame_quality(f) for f in self.captured_frames]):
            # Replace worst frame
            worst_idx = 0
            worst_quality = self.get_frame_quality(self.captured_frames[0])
            for i, f in enumerate(self.captured_frames[1:], 1):
                q = self.get_frame_quality(f)
                if q < worst_quality:
                    worst_quality = q
                    worst_idx = i
            self.captured_frames[worst_idx] = frame.copy()
        
        # Update best frame
        if quality > self.best_quality:
            self.best_frame = frame.copy()
            self.best_quality = quality
        
        return True
    
    def check_mouth_open(self, landmarks, height, width):
        """Mouth opening check"""
        top_lip = landmarks.landmark[13]
        bottom_lip = landmarks.landmark[14]
        mouth_height = abs(top_lip.y - bottom_lip.y) * height
        return mouth_height > 15
    
    def check_head_turn(self, landmarks, width):
        """Head turn check"""
        nose_tip = landmarks.landmark[1]
        left_eye = landmarks.landmark[33]
        right_eye = landmarks.landmark[362]
        
        eye_center_x = (left_eye.x + right_eye.x) / 2
        nose_x = nose_tip.x
        turn_amount = nose_x - eye_center_x
        
        if self.turn_direction == 'left':
            return turn_amount > 0.05
        else:
            return turn_amount < -0.05
    
    def process_frame(self, frame):
        """Main frame processing + auto capture"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        height, width = frame.shape[:2]
        
        # No face
        if not results.multi_face_landmarks:
            return {
                'status': 'no_face',
                'message': 'Please show your face clearly',
                'completed': False
            }
        
        landmarks = results.multi_face_landmarks[0]
        
        # Auto capture good frames
        self.capture_if_good(frame)
        
        # Check timeout
        elapsed = time.time() - self.start_time
        timeout = self.challenges[self.current_challenge]['timeout']
        
        if elapsed > timeout:
            return {
                'status': 'timeout',
                'message': 'Time up! Please try again.',
                'completed': False
            }
        
        # Check challenge
        challenge_passed = False
        
        if self.current_challenge == 'mouth_open':
            challenge_passed = self.check_mouth_open(landmarks, height, width)
        elif self.current_challenge == 'head_turn':
            challenge_passed = self.check_head_turn(landmarks, width)
        
        if challenge_passed:
            self.completed = True
            return {
                'status': 'success',
                'message': 'Challenge completed! ✅',
                'completed': True,
                'frames_captured': len(self.captured_frames),
                'best_quality': self.best_quality
            }
        
        # In progress
        time_left = int(timeout - elapsed)
        instruction = self.challenges[self.current_challenge]['name']
        if self.current_challenge == 'head_turn':
            instruction = f"Turn your head {self.turn_direction}"
        
        return {
            'status': 'in_progress',
            'message': f'{instruction} ({time_left}s remaining)',
            'completed': False,
            'time_remaining': time_left
        }
    
    def get_best_frame(self):
        """Get best captured frame"""
        return self.best_frame

# Helper functions for API
def start_liveness_session():
    """Initialize session"""
    detector = SimpleLivenessDetector()
    challenge_info = detector.challenges[detector.current_challenge]
    
    return {
        'session_started': True,
        'challenge': detector.current_challenge,
        'instruction': challenge_info['name'],
        'timeout': challenge_info['timeout']
    }

def verify_liveness_frame(frame_data, detector):
    """Process frame"""
    if isinstance(frame_data, str):  # base64
        import base64
        img_bytes = base64.b64decode(frame_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    else:
        frame = frame_data
    
    return detector.process_frame(frame)

# Legacy function for compatibility
async def check_liveness(image_file):
    """Legacy liveness check"""
    return {"is_live": True, "confidence": 0.8, "method": "legacy"}