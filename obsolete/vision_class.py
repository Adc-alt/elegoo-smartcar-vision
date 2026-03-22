"""Clase Vision legacy (análisis por momentos / posición left-center-right). No usada por main."""
import cv2
import numpy as np
from typing import Dict

_EMPTY = {
    "green_detected": False,
    "green_position": "none",
    "green_center": None,
    "green_area": 0.0,
}


class Vision:
    def __init__(self):
        self.lower_green = np.array([40, 50, 50])
        self.upper_green = np.array([80, 255, 255])
        self._kernel = np.ones((5, 5), np.uint8)

    def analyze(self, image: np.ndarray) -> Dict:
        if image is None:
            return _EMPTY.copy()
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return _EMPTY.copy()
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return {"green_detected": True, "green_position": "none", "green_center": None, "green_area": float(area)}
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        w = image.shape[1]
        if cx < w // 3:
            pos = "left"
        elif cx > 2 * w // 3:
            pos = "right"
        else:
            pos = "center"
        return {"green_detected": True, "green_position": pos, "green_center": (cx, cy), "green_area": float(area)}

    def set_green_range(self, lower: np.ndarray, upper: np.ndarray):
        self.lower_green = lower
        self.upper_green = upper

    def visualize_tracking(self, image: np.ndarray, analysis: Dict) -> np.ndarray:
        if image is None:
            return image
        out = image.copy()
        if not analysis.get("green_detected"):
            return out
        center = analysis.get("green_center")
        if center:
            cv2.circle(out, center, 10, (0, 255, 0), -1)
            cv2.circle(out, center, 20, (0, 255, 0), 2)
            cv2.putText(out, analysis.get("green_position", "none"), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return out
