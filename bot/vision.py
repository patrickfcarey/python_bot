# vision.py

import cv2
import numpy as np
import pytesseract
from mss import mss
from game_state import GameState
from config import AUTOMAP_REGION, LOADING_BRIGHTNESS_THRESHOLD, TEMPLATE_PATH, DEBUG

class Vision:
    def __init__(self):
        self.sct = mss()
        self.teammate_template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_UNCHANGED)

    def grab_frame(self):
        img = np.array(self.sct.grab(AUTOMAP_REGION))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def is_loading(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        return mean_brightness < LOADING_BRIGHTNESS_THRESHOLD

    def get_player_position(self, frame):
        # Placeholder: player marker detection could be template-based
        h, w, _ = frame.shape
        return (w // 2, h // 2)

    def find_teammates(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        template = cv2.cvtColor(self.teammate_template, cv2.COLOR_BGR2GRAY)
        w, h = template.shape[::-1]

        res = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)

        teammates = []
        for pt in zip(*loc[::-1]):
            x_center = pt[0] + w // 2
            y_center = pt[1] + h // 2

            # OCR check for nameplate
            crop = frame[pt[1]:pt[1]+h, pt[0]:pt[0]+w*3]
            text = pytesseract.image_to_string(crop).strip()
            if text:
                teammates.append((x_center, y_center))
        return teammates

    def extract_game_state(self, frame, level_number):
        player_pos = self.get_player_position(frame)
        teammates = self.find_teammates(frame)

        relative_vectors = []
        for t in teammates:
            dx = t[0] - player_pos[0]
            dy = t[1] - player_pos[1]
            relative_vectors.append((dx, dy))

        return GameState(
            automap_matrix=frame,
            teammate_positions=teammates,
            player_position=player_pos,
            relative_vectors=relative_vectors,
            level_number=level_number,
            loading=self.is_loading(frame)
        )