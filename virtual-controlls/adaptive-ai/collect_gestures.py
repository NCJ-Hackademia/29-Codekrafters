import cv2
import numpy as np
import os
import mediapipe as mp
import argparse
import json

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Collect gesture data for training')
    parser.add_argument('--gesture', type=str, required=True, help='Name of the gesture to collect data for')
    args = parser.parse_args()

    # Initialize MediaPipe
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5)
    mp_draw = mp.solutions.drawing_utils

    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), 'DATA')
    os.makedirs(output_dir, exist_ok=True)

    # Load existing gestures file
    gestures_file = os.path.join(os.path.dirname(__file__), 'custom_gestures.json')
    if os.path.exists(gestures_file):
        with open(gestures_file, 'r') as f:
            gestures = json.load(f)
    else:
        gestures = {}

    # Initialize video capture
    cap = cv2.VideoCapture(0)
    frame_count = 0
    total_frames_needed = 100  # Number of frames to collect for training

    print(f"\nCollecting data for gesture: {args.gesture}")
    print("Press 'q' to quit early")
    print(f"Please perform the gesture. Collecting {total_frames_needed} frames...\n")

    while cap.isOpened() and frame_count < total_frames_needed:
        ret, frame = cap.read()
        if not ret:
            continue

        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Extract landmark coordinates
                landmarks = []
                for lm in hand_landmarks.landmark:
                    landmarks.extend([lm.x, lm.y, lm.z])

                # Save landmarks to file
                output_file = os.path.join(output_dir, f"{args.gesture}_{frame_count}.npy")
                np.save(output_file, landmarks)
                frame_count += 1

        # Display progress
        cv2.putText(frame, f"Frames: {frame_count}/{total_frames_needed}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Collect Gestures', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if frame_count > 0:
        # Update gesture status in the JSON file
        gestures[args.gesture]['trained'] = True
        with open(gestures_file, 'w') as f:
            json.dump(gestures, f, indent=4)
        
        print(f"\nCollected {frame_count} frames for gesture: {args.gesture}")
        print("Data collection complete!")
    else:
        print("\nNo frames were collected. Please try again.")

if __name__ == "__main__":
    main()
