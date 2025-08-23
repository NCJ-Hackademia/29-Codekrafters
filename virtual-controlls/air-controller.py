# virtual_mouse_refreshed.py
# Touchless Virtual Mouse + Zoom Gesture via PyAutoGUI.scroll()

import cv2
import numpy as np
import mediapipe as mp
import autopy
import pyautogui    # <— new import
import time

# === Configuration ===
CAM_WIDTH, CAM_HEIGHT = 640, 480
FRAME_REDUCTION     = 100
SMOOTHENING         = 7
CLICK_THRESHOLD     = 40
ZOOM_THRESHOLD      = 10    # px change to trigger a scroll
SCROLL_FACTOR       = 20    # how many “clicks” per step

# Init camera
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if hasattr(cv2,'CAP_DSHOW') else 0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

# Mediapipe hands (up to 2)
mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils
hands    = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

# Screen size for cursor mapping
screen_w, screen_h = autopy.screen.size()

# State
prev_x = prev_y = 0
palm_click_pending = False
zoom_prev_dist    = None

def fingers_up(lm):
    tips = [4,8,12,16,20]
    st = []
    # Thumb: compare x coords
    st.append(1 if lm[tips[0]].x < lm[tips[0]-1].x else 0)
    # Other fingers: tip y < pip y
    for id in tips[1:]:
        st.append(1 if lm[id].y < lm[id-2].y else 0)
    return st

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img     = cv2.flip(frame,1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res     = hands.process(img_rgb)

    hand_count = len(res.multi_hand_landmarks) if res.multi_hand_landmarks else 0

    # --- TWO-HAND ZOOM ---
    if hand_count == 2:
        # draw both
        for hlm in res.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hlm, mp_hands.HAND_CONNECTIONS)

        # get two index-tip positions
        pts = []
        for hlm in res.multi_hand_landmarks:
            lm8 = hlm.landmark[8]
            pts.append((int(lm8.x*CAM_WIDTH), int(lm8.y*CAM_HEIGHT)))

        x1,y1 = pts[0]; x2,y2 = pts[1]
        dist = np.hypot(x2-x1, y2-y1)

        if zoom_prev_dist is None:
            zoom_prev_dist = dist
        else:
            delta = dist - zoom_prev_dist
            if abs(delta) > ZOOM_THRESHOLD:
                steps = int(delta/ZOOM_THRESHOLD) * SCROLL_FACTOR
                pyautogui.scroll(steps)         # <— use PyAutoGUI
                zoom_prev_dist = dist

        palm_click_pending = False

    # --- ONE-HAND MOUSE & CLICKS ---
    elif hand_count == 1:
        zoom_prev_dist = None  # reset zoom state

        hlm = res.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(img, hlm, mp_hands.HAND_CONNECTIONS)
        lm = hlm.landmark
        fu = fingers_up(lm)
        idx, mid = fu[1], fu[2]
        open_palm = all(fu)

        # move cursor
        if idx and not mid and not open_palm:
            x_px = int(lm[8].x * CAM_WIDTH)
            y_px = int(lm[8].y * CAM_HEIGHT)
            x_scr = np.interp(x_px,
                              (FRAME_REDUCTION, CAM_WIDTH-FRAME_REDUCTION),
                              (0, screen_w))
            y_scr = np.interp(y_px,
                              (FRAME_REDUCTION, CAM_HEIGHT-FRAME_REDUCTION),
                              (0, screen_h))
            curr_x = prev_x + (x_scr - prev_x)/SMOOTHENING
            curr_y = prev_y + (y_scr - prev_y)/SMOOTHENING
            autopy.mouse.move(curr_x, curr_y)
            prev_x, prev_y = curr_x, curr_y
            palm_click_pending = False

        # left click (pinch)
        elif idx and mid and not open_palm:
            x1,y1 = int(lm[8].x*CAM_WIDTH), int(lm[8].y*CAM_HEIGHT)
            x2,y2 = int(lm[12].x*CAM_WIDTH), int(lm[12].y*CAM_HEIGHT)
            if np.hypot(x2-x1, y2-y1) < CLICK_THRESHOLD:
                autopy.mouse.click()
            palm_click_pending = False

        # right click (open palm)
        elif open_palm:
            if not palm_click_pending:
                autopy.mouse.click(autopy.mouse.Button.RIGHT)
                palm_click_pending = True
        else:
            palm_click_pending = False

    # --- NO HANDS: reset all ---
    else:
        zoom_prev_dist = None
        palm_click_pending = False

    # draw movement boundary
    cv2.rectangle(img,
                  (FRAME_REDUCTION, FRAME_REDUCTION),
                  (CAM_WIDTH-FRAME_REDUCTION,
                   CAM_HEIGHT-FRAME_REDUCTION),
                  (255,0,255), 2)

    cv2.imshow("Touchless Virtual Mouse", img)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
