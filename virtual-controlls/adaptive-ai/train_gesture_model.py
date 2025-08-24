import os
import json
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def augment_sample(landmarks, noise_range=0.02, rotation_range=0.1, scale_range=0.1):
    """Add variations to landmarks for data augmentation"""
    landmarks = np.array(landmarks)
    
    # Add random noise
    noise = np.random.normal(0, noise_range, landmarks.shape)
    noisy = landmarks + noise
    
    # Random rotation around z-axis
    theta = np.random.uniform(-rotation_range, rotation_range)
    rotation_matrix = np.array([
        [np.cos(theta), -np.sin(theta), 0],
        [np.sin(theta), np.cos(theta), 0],
        [0, 0, 1]
    ])
    rotated = np.dot(noisy, rotation_matrix)
    
    # Random scaling
    scale = np.random.uniform(1 - scale_range, 1 + scale_range)
    scaled = rotated * scale
    
    return scaled.tolist()

def create_negative_samples(landmarks, num_samples=5):
    """Create negative samples by significantly altering the gesture"""
    negative_samples = []
    for _ in range(num_samples):
        # Add more extreme variations
        noisy = augment_sample(landmarks, 
                             noise_range=0.1,  # More noise
                             rotation_range=0.5,  # More rotation
                             scale_range=0.3)  # More scaling
        negative_samples.append(noisy)
    return negative_samples

# Load data
base_dir ="virtual-controlls/adaptive-ai/DATA"
gesture_types = ['stop', 'left', 'right', 'up', 'down', 'none', 'undo', 'redo']
X = []
y = []

try:
    print(f"Looking for gesture data in: {os.path.abspath(base_dir)}")
    
    for gesture_type in gesture_types:
        data_dir = os.path.join(base_dir, gesture_type)
        if not os.path.exists(data_dir):
            print(f"Warning: Directory {data_dir} not found, skipping...")
            continue
            
        files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        print(f"Found {len(files)} samples for {gesture_type} gesture")
        
        for file in files:
            with open(os.path.join(data_dir, file)) as f:
                try:
                    sample = json.load(f)
                    if "landmarks" not in sample:
                        print(f"Warning: No landmarks found in {file}, skipping...")
                        continue
                        
                    landmarks = sample["landmarks"]
                    
                    # Add original sample
                    flat = [coord for point in landmarks for coord in point]
                    X.append(flat)
                    y.append(gesture_type)
                    
                    # Add augmented positive samples (small variations)
                    for _ in range(2):
                        augmented = augment_sample(landmarks)
                        flat_aug = [coord for point in augmented for coord in point]
                        X.append(flat_aug)
                        y.append(gesture_type)
                        
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON in {file}, skipping...")
                    continue

    if not X:
        raise ValueError("No valid samples were loaded")

    X = np.array(X)
    y = np.array(y)
    
    print(f"\nTotal samples after augmentation: {len(X)}")
    for gesture in gesture_types:
        print(f"{gesture} gestures: {sum(y == gesture)}")

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Train-test split with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_encoded, 
        test_size=0.2, 
        random_state=42,
        stratify=y_encoded
    )

    # Use Random Forest for better generalization
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42
    )

    # Train model
    clf.fit(X_train, y_train)

    # Evaluate on test set
    y_pred = clf.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)
    print(f"\nTest set accuracy: {test_acc:.2f}")
    
    # Print detailed metrics
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Feature importance analysis
    feature_importance = clf.feature_importances_
    top_n = 10
    top_indices = np.argsort(feature_importance)[-top_n:]
    print(f"\nTop {top_n} most important landmarks:")
    for idx in top_indices:
        point_idx = idx // 3
        coord_idx = idx % 3
        coord_name = ['x', 'y', 'z'][coord_idx]
        print(f"Point {point_idx} {coord_name}: {feature_importance[idx]:.4f}")

    # Save model, scaler, and label encoder
    os.makedirs("models", exist_ok=True)
    model_path = os.path.join("models", "gesture_model.pkl")
    scaler_path = os.path.join("models", "scaler.pkl")
    label_encoder_path = os.path.join("models", "label_encoder.pkl")
    
    joblib.dump(clf, model_path)
    joblib.dump(scaler, scaler_path)
    joblib.dump(le, label_encoder_path)
    print("\nSaved files:")
    print(f"Model: {model_path}")
    print(f"Scaler: {scaler_path}")
    print(f"Label Encoder: {label_encoder_path}")

    # Verify the model works
    print("\nVerifying model predictions...")
    # Test on original sample
    test_idx = 0
    test_sample = X[test_idx:test_idx+1]
    test_scaled = scaler.transform(test_sample)
    test_proba = clf.predict_proba(test_scaled)[0]
    print(f"Original {y[test_idx]} gesture confidence: {test_proba[le.transform([y[test_idx]])[0]]:.2f}")
    
    # Test on negative sample
    neg_idx = np.where(y != y[test_idx])[0][0]
    neg_sample = X[neg_idx:neg_idx+1]
    neg_scaled = scaler.transform(neg_sample)
    neg_proba = clf.predict_proba(neg_scaled)[0]
    print(f"Negative {y[neg_idx]} gesture confidence: {neg_proba[le.transform([y[neg_idx]])[0]]:.2f}")

except Exception as e:
    print(f"Error: {str(e)}")
    raise
