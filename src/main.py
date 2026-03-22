"""Video del coche: OpenCV lee la URL MJPEG (mismo recurso que el navegador)."""
import math
import sys
from pathlib import Path

import cv2

if __package__ is None:
    _repo_root = Path(__file__).resolve().parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from src.stream_reader import STREAM_URL
from src.vision import green_detect

WIN_BGR = "BGR"
WIN_MASK = "mask"

# Calibración: d_y ≈ a + C/(y - y0)  (y = píxel vertical del centro; d_y en cm aprox.)
_DY_A = -10.35
_DY_C = 7285.24
_DY_Y0 = 87.30
# dx = k * dy * x_prime  (x_prime en px respecto al centro de la imagen)
_DX_K = -0.0025


def estimate_dy_cm(y: float) -> float | None:
    if y <= _DY_Y0:
        return None
    return _DY_A + _DY_C / (y - _DY_Y0)


def estimate_dx_cm(x_prime: float, dy_cm: float) -> float:
    return _DX_K * dy_cm * x_prime


# r_turn = d / (2*sin(beta)); si |sin(beta)| es casi 0 (bola al frente), no definimos r
_MIN_ABS_SIN_BETA = 0.02


def turn_radius_cm(d_cm: float, beta_rad: float) -> float | None:
    s = math.sin(beta_rad)
    if abs(s) < _MIN_ABS_SIN_BETA:
        return None
    return d_cm / (2.0 * s)


def main() -> None:
    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("No se abre la URL (WiFi al coche, o prueba /stream en vez de /streaming):", STREAM_URL)
        return
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print(
        "d_y ≈ -10.35 + 7285.24/(y-87.30) cm | dx = -0.0025 * d_y * x' | "
        "d = hypot(dx,dy) | beta = atan2(dx,dy) | "
        "r_turn=d/(2*sin(beta)) si |sin(beta)|>=0.02",
        flush=True,
    )
    cv2.namedWindow(WIN_BGR, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_MASK, cv2.WINDOW_NORMAL)
    placed = False
    try:
        while True:
            ok, frame = cap.read()
            if ok and frame is not None:
                pt, mask, r_ball = green_detect(frame)
                bgr = frame.copy()
                h, w = bgr.shape[:2]
                if pt is not None and r_ball > 0:
                    x, y = pt
                    x_prime = x - (w / 2.0)
                    dy_cm = estimate_dy_cm(float(y))
                    if dy_cm is not None:
                        dx_cm = estimate_dx_cm(x_prime, dy_cm)
                        d_cm = math.hypot(dx_cm, dy_cm)
                        beta_rad = math.atan2(dx_cm, dy_cm)
                        beta_deg = math.degrees(beta_rad)
                        r_turn_cm = turn_radius_cm(d_cm, beta_rad)
                        r_turn_s = (
                            f"{r_turn_cm:.1f}cm"
                            if r_turn_cm is not None
                            else f"n/a(|sinβ|<{_MIN_ABS_SIN_BETA})"
                        )
                        print(
                            f"x={x} y={y} x'={x_prime:.2f} r_px={r_ball} "
                            f"dy={dy_cm:.2f} dx={dx_cm:.3f} d={d_cm:.2f}cm "
                            f"beta={beta_rad:.4f}rad ({beta_deg:.1f}deg) "
                            f"r_turn={r_turn_s}",
                            flush=True,
                        )
                    else:
                        print(
                            f"x={x} y={y} x'={x_prime:.2f} r_px={r_ball} dy=n/a (y<={_DY_Y0})",
                            flush=True,
                        )
                    cv2.circle(bgr, pt, r_ball, (0, 255, 0), 2)
                cv2.putText(bgr, "BGR", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                cv2.putText(mask_bgr, "mask", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                if mask_bgr.shape[:2] != (h, w):
                    mask_bgr = cv2.resize(mask_bgr, (w, h))
                if not placed:
                    cv2.moveWindow(WIN_BGR, 40, 80)
                    cv2.moveWindow(WIN_MASK, 40 + w + 10, 80)
                    placed = True
                cv2.imshow(WIN_BGR, bgr)
                cv2.imshow(WIN_MASK, mask_bgr)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
