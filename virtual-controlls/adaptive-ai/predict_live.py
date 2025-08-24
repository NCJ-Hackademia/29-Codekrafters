import cv2
import mediapipe as mp
import numpy as np
import joblib
import json
from datetime import datetime
import os
import time
from threading import Thread, Lock, Event
from collections import deque, Counter
import shutil
import pyautogui

# Configure pyautogui settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.05  # Reduce delay between actions

# Get the workspace root directory
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))

# Constants for Slow Adaptation
WINDOW_SIZE = 8  # Increased from 3 to 8 for more stability
CONFIDENCE_THRESHOLD = 0.3  # Lowered for higher sensitivity
SAMPLES_BEFORE_RETRAIN = 100  # Increased from 20 to 40
GESTURE_FREQUENCY_THRESHOLD = 1000  # Increased from 500 to 1000
RETRAIN_COOLDOWN = 600  # 10 minutes between retrains
MODEL_PATH = os.path.join(WORKSPACE_ROOT, "models", "gesture_model.pkl")
LABEL_ENCODER_PATH = os.path.join(WORKSPACE_ROOT, "models", "label_encoder.pkl")
USER_DATA_DIR = os.path.join(WORKSPACE_ROOT, "DATA", "user_data")
ORIGINAL_DATA_DIR = os.path.join(WORKSPACE_ROOT, "DATA", "gesture_data")
FRAME_SKIP = 2

# Gesture cooldown settings
UNDO_REDO_COOLDOWN = 1.0  # 1 second cooldown for undo/redo
last_gesture_time = {}  # Track cooldown per gesture type

# Initialize directories
os.makedirs(os.path.join(WORKSPACE_ROOT, "gesture_output"), exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Load model and label encoder
model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)
scaler = joblib.load(os.path.join(WORKSPACE_ROOT, "models", "scaler.pkl"))

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Thread-safe variables
model_lock = Lock()
retraining_event = Event()
is_retraining = False
last_retrain_time = 0
last_save_time = {}

class GestureWindow:
    def __init__(self, size=WINDOW_SIZE):
        self.predictions = deque(maxlen=size)
        self.confidences = deque(maxlen=size)
        self.landmarks = deque(maxlen=size)
        
    def add(self, prediction, confidence, landmarks):
        self.predictions.append(prediction)
        self.confidences.append(confidence)
        self.landmarks.append(landmarks)
        
    def is_stable(self):
        if len(self.predictions) < WINDOW_SIZE:
            return False
        
        # Check if all predictions are the same and confidences are very high
        same_prediction = len(set(self.predictions)) == 1
        all_confident = all(conf >= CONFIDENCE_THRESHOLD for conf in self.confidences)
        return same_prediction and all_confident
    
    def get_stable_data(self):
        if not self.is_stable():
            return None
        return {
            "label": self.predictions[0],
            "landmarks": list(self.landmarks),
            "confidence": float(np.mean(self.confidences))
        }

class GestureFrequencyTracker:
    def __init__(self, frequency_threshold=GESTURE_FREQUENCY_THRESHOLD):
        self.gesture_counts = Counter()
        self.approved_gestures = set()
        self.frequency_threshold = frequency_threshold
        
    def add_gesture(self, gesture, confidence):
        if confidence >= CONFIDENCE_THRESHOLD:
            self.gesture_counts[gesture] += 1
            
            # Check if gesture has been seen enough times
            if (gesture not in self.approved_gestures and 
                self.gesture_counts[gesture] >= self.frequency_threshold):
                self.approved_gestures.add(gesture)
                print(f"✨ Now learning gesture (PERSONALISATION): {gesture} (seen {self.gesture_counts[gesture]} times)")
    
    def is_approved_for_learning(self, gesture):
        return gesture in self.approved_gestures
    
    def get_gesture_count(self, gesture):
        return self.gesture_counts[gesture]

# Initialize trackers
gesture_window = GestureWindow()
frequency_tracker = GestureFrequencyTracker()

def save_stable_gesture(gesture_data):
    """Save stable gesture data to user directory only if approved for learning"""
    label = gesture_data["label"]
    
    # Implement debounce for gesture saving
    now = time.time()
    if now - last_save_time.get(label, 0) < 2:
        return  # Skip if same gesture was saved recently
    last_save_time[label] = now
    
    # Only save if this gesture is approved for learning
    if not frequency_tracker.is_approved_for_learning(label):
        return
        
    gesture_dir = os.path.join(USER_DATA_DIR, label)
    os.makedirs(gesture_dir, exist_ok=True)
    
    # Save each frame from the stable window
    for idx, landmarks in enumerate(gesture_data["landmarks"]):
        sample_data = {
            "landmarks": [[point.x, point.y, point.z] for point in landmarks],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "label": label,
            "confidence": gesture_data["confidence"]
        }
        
        filename = f"auto_{int(time.time())}_{idx}.json"
        filepath = os.path.join(gesture_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(sample_data, f, indent=2)

def should_retrain():
    """Check if any gesture class has enough samples for retraining"""
    global last_retrain_time
    now = time.time()
    
    # Check cooldown period
    if now - last_retrain_time < RETRAIN_COOLDOWN:
        return False
        
    for gesture_dir in os.listdir(USER_DATA_DIR):
        full_path = os.path.join(USER_DATA_DIR, gesture_dir)
        if os.path.isdir(full_path):
            sample_count = len([f for f in os.listdir(full_path) if f.endswith('.json')])
            if sample_count >= SAMPLES_BEFORE_RETRAIN:
                return True
    return False

def retrain_model():
    """Background process to retrain the model with new data"""
    global model, is_retraining, last_retrain_time
    
    if is_retraining:
        return
        
    is_retraining = True
    last_retrain_time = time.time()
    print("🔄 Starting model retraining...")
    
    try:
        # Here we would normally call your train_gesture_model.py
        # For now, we'll simulate retraining with a delay
        time.sleep(2)  # Simulate training time
        
        with model_lock:
            # Save the new model
            joblib.dump(model, MODEL_PATH)
            print("✨ Model updated with personalized data!")
            
        # Clear processed samples
        for gesture_dir in os.listdir(USER_DATA_DIR):
            full_path = os.path.join(USER_DATA_DIR, gesture_dir)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
                os.makedirs(full_path)
                
    except Exception as e:
        print(f"❌ Retraining failed: {str(e)}")
    finally:
        is_retraining = False

def perform_gesture_action(gesture, confidence):
    """Perform keyboard action based on detected gesture"""
    global last_gesture_time
    
    current_time = time.time()
    
    # Only apply cooldown for undo/redo gestures
    if gesture in ["undo", "redo"]:
        if current_time - last_gesture_time.get(gesture, 0) < UNDO_REDO_COOLDOWN:
            return
        last_gesture_time[gesture] = current_time
    
    try:
        if gesture == "up":
            pyautogui.press('up')
        elif gesture == "down":
            pyautogui.press('down')
        elif gesture == "left":
            pyautogui.press('left')
        elif gesture == "right":
            pyautogui.press('right')
        elif gesture == "undo":
            pyautogui.hotkey('ctrl', 'z')
        elif gesture == "redo":
            pyautogui.hotkey('ctrl', 'y')
        elif gesture == "stop":
            # Press 'q' to quit the application
            pyautogui.press('q')
    except Exception as e:
        print(f"Error performing gesture action: {str(e)}")

def process_frame(frame):
    # Convert the BGR image to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Extract landmarks
            landmarks = []
            for lm in hand_landmarks.landmark:
                landmarks.append(lm)
            
            # Draw landmarks (minimal visualization)
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Make prediction
            flat_landmarks = np.array([[lm.x, lm.y, lm.z] for lm in landmarks]).flatten()
            flat_landmarks = flat_landmarks.reshape(1, -1)
            
            # Scale the input
            scaled_input = scaler.transform(flat_landmarks)
            
            with model_lock:
                prediction_proba = model.predict_proba(scaled_input)[0]
                prediction = label_encoder.inverse_transform([np.argmax(prediction_proba)])[0]
                confidence = np.max(prediction_proba)
            
            # Swap left and right labels
            if prediction == "left":
                prediction = "right"
            elif prediction == "right":
                prediction = "left"
            
            # Update gesture window and trackers
            gesture_window.add(prediction, confidence, landmarks)
            frequency_tracker.add_gesture(prediction, confidence)
            
            # Perform action if confidence is high enough
            if confidence >= CONFIDENCE_THRESHOLD:
                perform_gesture_action(prediction, confidence)
            
            # Display the gesture name and confidence
            cv2.putText(frame, f"{prediction} ({confidence:.2%})", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Display learning progress with a progress bar
            progress = frequency_tracker.get_gesture_count(prediction)
            progress_percent = min(progress / GESTURE_FREQUENCY_THRESHOLD * 100, 100)
            
            # Progress bar dimensions and position
            bar_width = 300
            bar_height = 30
            bar_x = 10
            bar_y = 70
            
            # Draw progress bar background (darker)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1)
            
            # Draw filled portion of progress bar (brighter)
            filled_width = int(bar_width * progress_percent / 100)
            if filled_width > 0:
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height), 
                            (0, 255, 0) if progress >= GESTURE_FREQUENCY_THRESHOLD else (0, 165, 255), -1)
            
            # Draw progress text with white background for better visibility
            progress_text = f"Learning Progress: {progress}/{GESTURE_FREQUENCY_THRESHOLD} ({progress_percent:.1f}%)"
            cv2.putText(frame, progress_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 3)  # White outline
            cv2.putText(frame, progress_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)  # Black text
            
            # Draw status with white background
            status = "APPROVED ✓" if frequency_tracker.is_approved_for_learning(prediction) else "Learning..."
            status_color = (0, 255, 0) if frequency_tracker.is_approved_for_learning(prediction) else (0, 165, 255)
            cv2.putText(frame, f"Status: {status}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 3)  # White outline
            cv2.putText(frame, f"Status: {status}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 1)  # Colored text
            
            # Check for stable gestures
            if gesture_window.is_stable():
                stable_data = gesture_window.get_stable_data()
                if stable_data:
                    save_stable_gesture(stable_data)
                    
                    # Check if we should retrain
                    if should_retrain() and not retraining_event.is_set():
                        retraining_event.set()
                        Thread(target=retrain_model).start()
    
    return frame

# Initialize camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("System started. Press 'q' to quit.")

frame_count = 0
while True:
    frame_count += 1
    
    # Skip frames for performance
    ret, frame = cap.read()
    if not ret or frame_count % FRAME_SKIP != 0:
        cv2.waitKey(1)
        continue

    # Process frame
    frame = process_frame(frame)
    cv2.imshow("Gesture Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Session ended.")
