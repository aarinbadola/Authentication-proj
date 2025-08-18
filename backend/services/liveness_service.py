# services/liveness_service.py
"""
Complete Liveness Detection Service
Handles face detection, movement tracking, and frame quality assessment
"""

import cv2
import numpy as np
import time
import math
from typing import Dict, List, Optional, Tuple

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️ MediaPipe not available - using OpenCV fallback")

class LivenessDetector:
    """
    Liveness detection using face landmarks and movement analysis
    Supports both MediaPipe and OpenCV backends
    """
    
    def __init__(self):
        self.use_mediapipe = MEDIAPIPE_AVAILABLE
        self.frame_count = 0
        self.start_time = time.time()
        self.face_positions = []
        self.face_sizes = []
        self.movement_threshold = 15
        self.completed = False
        self.best_frame = None
        self.best_frame_score = 0
        
        # Initialize detection backends
        if self.use_mediapipe:
            self._init_mediapipe()
        else:
            self._init_opencv()
    
    def _init_mediapipe(self):
        """Initialize MediaPipe face detection"""
        try:
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_drawing = mp.solutions.drawing_utils
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1, 
                min_detection_confidence=0.5
            )
            print("✅ MediaPipe face detection initialized")
        except Exception as e:
            print(f"⚠️ MediaPipe initialization failed: {e}")
            self.use_mediapipe = False
            self._init_opencv()
    
    def _init_opencv(self):
        """Initialize OpenCV face detection as fallback"""
        try:
            # Try to load Haar cascade
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            print("✅ OpenCV face detection initialized")
        except Exception as e:
            print(f"⚠️ OpenCV initialization failed: {e}")
            # Create a mock detector for testing
            self.face_cascade = None
    
    def detect_faces_mediapipe(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using MediaPipe"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detector.process(rgb_frame)
        
        faces = []
        if results.detections:
            h, w, _ = frame.shape
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                faces.append((x, y, width, height))
        
        return faces
    
    def detect_faces_opencv(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using OpenCV"""
        if self.face_cascade is None:
            # Mock detection for testing
            h, w = frame.shape[:2]
            # Return a centered mock face
            mock_size = min(w, h) // 3
            x = (w - mock_size) // 2
            y = (h - mock_size) // 2
            return [(x, y, mock_size, mock_size)]
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )
        return [(x, y, w, h) for x, y, w, h in faces]
    
    def calculate_frame_quality(self, frame: np.ndarray, face_box: Tuple[int, int, int, int]) -> float:
        """Calculate frame quality score based on various factors"""
        x, y, w, h = face_box
        
        # Extract face region
        face_region = frame[y:y+h, x:x+w]
        if face_region.size == 0:
            return 0.0
        
        # Convert to grayscale for analysis
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Calculate sharpness using Laplacian variance
        sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        
        # Calculate brightness (avoid too dark or too bright)
        brightness = np.mean(gray_face)
        brightness_score = 1.0 - abs(brightness - 128) / 128
        
        # Size score (prefer larger faces)
        frame_area = frame.shape[0] * frame.shape[1]
        face_area = w * h
        size_score = min(face_area / (frame_area * 0.05), 1.0)  # Max at 5% of frame
        
        # Center score (prefer centered faces)
        frame_center_x, frame_center_y = frame.shape[1] // 2, frame.shape[0] // 2
        face_center_x, face_center_y = x + w // 2, y + h // 2
        distance = math.sqrt((face_center_x - frame_center_x)**2 + (face_center_y - frame_center_y)**2)
        max_distance = math.sqrt(frame.shape[1]**2 + frame.shape[0]**2) / 2
        center_score = 1.0 - (distance / max_distance)
        
        # Combined score
        quality_score = (sharpness/1000 * 0.4 + brightness_score * 0.3 + 
                        size_score * 0.2 + center_score * 0.1)
        
        return min(quality_score, 1.0)
    
    def check_movement(self, current_face: Tuple[int, int, int, int]) -> bool:
        """Check if sufficient movement has been detected"""
        if len(self.face_positions) < 2:
            return False
        
        x, y, w, h = current_face
        center_x, center_y = x + w // 2, y + h // 2
        
        # Check movement from first position
        first_x, first_y = self.face_positions[0]
        movement = math.sqrt((center_x - first_x)**2 + (center_y - first_y)**2)
        
        return movement > self.movement_threshold
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Process a single frame for liveness detection
        Returns status and instructions
        """
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        
        # Detect faces
        if self.use_mediapipe:
            faces = self.detect_faces_mediapipe(frame)
        else:
            faces = self.detect_faces_opencv(frame)
        
        # No face detected
        if not faces:
            return {
                "status": "no_face",
                "instruction": "Please position your face in the camera",
                "frame_count": self.frame_count,
                "elapsed_time": elapsed_time
            }
        
        # Multiple faces detected
        if len(faces) > 1:
            return {
                "status": "multiple_faces",
                "instruction": "Multiple faces detected. Please ensure only you are in frame",
                "frame_count": self.frame_count,
                "elapsed_time": elapsed_time
            }
        
        # Single face detected - process it
        face = faces[0]
        x, y, w, h = face
        center_x, center_y = x + w // 2, y + h // 2
        
        # Store face position and size
        self.face_positions.append((center_x, center_y))
        self.face_sizes.append(w * h)
        
        # Keep only recent positions (last 30 frames)
        if len(self.face_positions) > 30:
            self.face_positions = self.face_positions[-30:]
            self.face_sizes = self.face_sizes[-30:]
        
        # Calculate frame quality
        quality_score = self.calculate_frame_quality(frame, face)
        
        # Update best frame if this one is better
        if quality_score > self.best_frame_score:
            self.best_frame_score = quality_score
            self.best_frame = frame.copy()
        
        # Check if liveness is completed
        movement_detected = self.check_movement(face)
        sufficient_frames = self.frame_count >= 10
        minimum_time = elapsed_time >= 3.0
        
        if movement_detected and sufficient_frames and minimum_time:
            if not self.completed:
                self.completed = True
                return {
                    "status": "completed",
                    "instruction": "Liveness verification completed!",
                    "frame_count": self.frame_count,
                    "elapsed_time": elapsed_time,
                    "quality_score": quality_score,
                    "best_frame_score": self.best_frame_score
                }
        
        # Still processing
        instructions = []
        if not sufficient_frames:
            instructions.append("Keep your face steady")
        if not movement_detected:
            instructions.append("Slowly turn your head left and right")
        if not minimum_time:
            instructions.append("Continue for a few more seconds")
        
        instruction = " and ".join(instructions) if instructions else "Processing..."
        
        return {
            "status": "processing",
            "instruction": instruction,
            "frame_count": self.frame_count,
            "elapsed_time": elapsed_time,
            "quality_score": quality_score,
            "movement_detected": movement_detected,
            "progress": min((self.frame_count / 10) * 100, 100)
        }
    
    def get_best_frame(self) -> Optional[np.ndarray]:
        """Get the best quality frame captured during liveness detection"""
        return self.best_frame
    
    def reset(self):
        """Reset the detector for a new session"""
        self.frame_count = 0
        self.start_time = time.time()
        self.face_positions = []
        self.face_sizes = []
        self.completed = False
        self.best_frame = None
        self.best_frame_score = 0

# Utility functions for backward compatibility
def create_liveness_detector() -> LivenessDetector:
    """Factory function to create a liveness detector"""
    return LivenessDetector()

def process_liveness_frame(detector: LivenessDetector, frame: np.ndarray) -> Dict:
    """Process a frame for liveness detection"""
    return detector.process_frame(frame)

# Test function
def test_liveness_service():
    """Test the liveness service functionality"""
    print("🧪 Testing Liveness Service...")
    
    try:
        detector = LivenessDetector()
        print(f"✅ LivenessDetector created successfully")
        print(f"   Backend: {'MediaPipe' if detector.use_mediapipe else 'OpenCV'}")
        
        # Create a test frame (simple colored rectangle)
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[:] = (100, 150, 200)  # Fill with color
        
        result = detector.process_frame(test_frame)
        print(f"✅ Frame processing successful")
        print(f"   Status: {result['status']}")
        print(f"   Instruction: {result['instruction']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Liveness service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_liveness_service()