"""BGR → HSV, máscara verde; solo contornos bastante circulares; círculo envolvente completo."""
import cv2
import numpy as np

# H acotado al verde (excluye suelo amarillento); S alto = no reflejos apagados del suelo
_LOWER = np.array([40, 90, 55], dtype=np.uint8)
_UPPER = np.array([80, 255, 255], dtype=np.uint8)
_MIN_AREA = 400
_MIN_CIRC = 0.58  # 1 = círculo perfecto; rechaza manchas alargadas

_K_OPEN = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
_K_CLOSE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))


def green_detect(img_bgr: np.ndarray) -> tuple[tuple[int, int] | None, np.ndarray, int]:
    """(centro, máscara, radio). Radio = círculo mínimo que rodea todo el blob aceptado."""
    hsv = cv2.cvtColor(cv2.GaussianBlur(img_bgr, (5, 5), 0), cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, _LOWER, _UPPER)
    mask = cv2.medianBlur(mask, 5)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _K_OPEN)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _K_CLOSE)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, mask, 0
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < _MIN_AREA:
        return None, mask, 0
    peri = cv2.arcLength(c, True)
    if peri <= 0:
        return None, mask, 0
    if (4.0 * np.pi * area / (peri * peri)) < _MIN_CIRC:
        return None, mask, 0
    (cx, cy), r = cv2.minEnclosingCircle(c)
    return (int(cx), int(cy)), mask, int(r)
