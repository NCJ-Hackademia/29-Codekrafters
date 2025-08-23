# virtual_mouse_refreshed.py
# Touchless Virtual Mouse + Zoom & Grab Gestures

import cv2
import numpy as np
import mediapipe as mp
import autopy
import pyautogui
import time

# === Configuration ===
CAM_WIDTH, CAM_HEIGHT = 640, 480
FRAME_REDUCTION     = 100
SMOOTHENING         = 7
CLICK_THRESHOLD     = 40
ZOOM_THRESHOLD      = 10    # px change to trigger a scroll
SCROLL_FACTOR       = 20    # scroll “clicks” per threshold step

# Initialize camera
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if hasattr(cv2,'CAP_DSHOW') else 0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

# Mediapipe hands (up to 2)
mp_hands    = mp.solutions.hands
mp_draw     = mp.solutions.drawing_utils
hands       = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# Screen size for cursor mapping
screen_w, screen_h = autopy.screen.size()

# Gesture state
prev_x = prev_y = 0
palm_click_pending = False
zoom_prev_dist    = None
grab_mode         = False

def is_zoom_gesture(lm, label):
    """Thumb+index up only."""
    # Thumb direction depends on hand
    if label == "Right":
        thumb_up = lm[4].x < lm[3].x
    else:
        thumb_up = lm[4].x > lm[3].x
    index_up  = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_up   = lm[16].y < lm[14].y
    pinky_up  = lm[20].y < lm[18].y
    return thumb_up and index_up and not (middle_up or ring_up or pinky_up)

def is_palm_open(lm, label):
    """All five fingers extended."""
    # Thumb
    if label == "Right":
        thumb_ok = lm[4].x < lm[3].x
    else:
        thumb_ok = lm[4].x > lm[3].x
    # Other fingers
    idx_ok    = lm[8].y  < lm[6].y
    mid_ok    = lm[12].y < lm[10].y
    ring_ok   = lm[16].y < lm[14].y
    pinky_ok  = lm[20].y < lm[18].y
    return thumb_ok and idx_ok and mid_ok and ring_ok and pinky_ok

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img     = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res     = hands.process(img_rgb)

    hand_count = len(res.multi_hand_landmarks) if res.multi_hand_landmarks else 0

    # --- TWO-HAND GESTURES: Grab OR Zoom ---
    if hand_count == 2:
        landmarks  = res.multi_hand_landmarks
        handedness = res.multi_handedness

        # Draw both hands
        for hlm in landmarks:
            mp_draw.draw_landmarks(img, hlm, mp_hands.HAND_CONNECTIONS)

        zoom_states = []
        open_states = []
        pts = []

        # Evaluate each hand
        for i, hlm in enumerate(landmarks):
            label = handedness[i].classification[0].label
            lm = hlm.landmark
            zoom_states.append(is_zoom_gesture(lm, label))
            open_states.append(is_palm_open(lm, label))
            pts.append((int(lm[8].x * CAM_WIDTH), int(lm[8].y * CAM_HEIGHT)))

        # --- Grab Gesture: both palms open ---
        if open_states[0] and open_states[1]:
            # Compute average point for drag
            avg_x = (pts[0][0] + pts[1][0]) / 2
            avg_y = (pts[0][1] + pts[1][1]) / 2
            # Map to screen coords
            scr_x = np.interp(avg_x,
                              (FRAME_REDUCTION, CAM_WIDTH - FRAME_REDUCTION),
                              (0, screen_w))
            scr_y = np.interp(avg_y,
                              (FRAME_REDUCTION, CAM_HEIGHT - FRAME_REDUCTION),
                              (0, screen_h))

            if not grab_mode:
                # Start drag
                autopy.mouse.toggle(autopy.mouse.Button.LEFT, down=True)
                grab_mode = True
            # Drag to new position
            autopy.mouse.move(scr_x, scr_y)
            # Reset other states
            zoom_prev_dist = None
            palm_click_pending = False

        # --- Zoom Gesture: thumbs+index only ---
        elif zoom_states[0] and zoom_states[1]:
            # Reset grab if needed
            if grab_mode:
                autopy.mouse.toggle(autopy.mouse.Button.LEFT, down=False)
                grab_mode = False

            x1, y1 = pts[0]
            x2, y2 = pts[1]
            curr_dist = np.hypot(x2 - x1, y2 - y1)

            if zoom_prev_dist is None:
                zoom_prev_dist = curr_dist
            else:
                delta = curr_dist - zoom_prev_dist
                if abs(delta) > ZOOM_THRESHOLD:
                    steps = int(delta / ZOOM_THRESHOLD) * SCROLL_FACTOR
                    pyautogui.scroll(steps)
                    zoom_prev_dist = curr_dist

            palm_click_pending = False

        # --- No two-hand gesture: reset states ---
        else:
            if grab_mode:
                autopy.mouse.toggle(autopy.mouse.Button.LEFT, down=False)
                grab_mode = False
            zoom_prev_dist = None
            palm_click_pending = False

    # --- SINGLE-HAND: Cursor & Clicks ---
    elif hand_count == 1:
        # Reset two-hand states
        if grab_mode:
            autopy.mouse.toggle(autopy.mouse.Button.LEFT, down=False)
            grab_mode = False
        zoom_prev_dist = None

        hlm = res.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(img, hlm, mp_hands.HAND_CONNECTIONS)
        lm = hlm.landmark

        idx_up = lm[8].y  < lm[6].y
        mid_up = lm[12].y < lm[10].y
        open_p = is_palm_open(lm, res.multi_handedness[0].classification[0].label)

        # Move cursor
        if idx_up and not mid_up and not open_p:
            x_px = int(lm[8].x * CAM_WIDTH)
            y_px = int(lm[8].y * CAM_HEIGHT)
            x_scr = np.interp(x_px,
                              (FRAME_REDUCTION, CAM_WIDTH - FRAME_REDUCTION),
                              (0, screen_w))
            y_scr = np.interp(y_px,
                              (FRAME_REDUCTION, CAM_HEIGHT - FRAME_REDUCTION),
                              (0, screen_h))
            curr_x = prev_x + (x_scr - prev_x) / SMOOTHENING
            curr_y = prev_y + (y_scr - prev_y) / SMOOTHENING
            autopy.mouse.move(curr_x, curr_y)
            prev_x, prev_y = curr_x, curr_y
            palm_click_pending = False

        # Left click (pinch)
        elif idx_up and mid_up and not open_p:
            x1, y1 = int(lm[8].x * CAM_WIDTH), int(lm[8].y * CAM_HEIGHT)
            x2, y2 = int(lm[12].x * CAM_WIDTH), int(lm[12].y * CAM_HEIGHT)
            if np.hypot(x2 - x1, y2 - y1) < CLICK_THRESHOLD:
                autopy.mouse.click()
            palm_click_pending = False

        # Right click (open palm)
        elif open_p:
            if not palm_click_pending:
                autopy.mouse.click(autopy.mouse.Button.RIGHT)
                palm_click_pending = True
        else:
            palm_click_pending = False

    # --- NO HANDS: reset all ---
    else:
        if grab_mode:
            autopy.mouse.toggle(autopy.mouse.Button.LEFT, down=False)
            grab_mode = False
        zoom_prev_dist = None
        palm_click_pending = False

    # Draw interaction boundary
    cv2.rectangle(
        img,
        (FRAME_REDUCTION, FRAME_REDUCTION),
        (CAM_WIDTH - FRAME_REDUCTION, CAM_HEIGHT - FRAME_REDUCTION),
        (255, 0, 255),
        2
    )

    cv2.imshow("Touchless Virtual Mouse", img)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break

cap.release()
cv2.destroyAllWindows()
