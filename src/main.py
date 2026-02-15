"""Main - Display BGR en tiempo real + detección bola verde (máscara B/N)."""
import math
import cv2
import numpy as np
from .camera import Camera
from .vision import detect_green_ball

IP = "192.168.4.1"
WINDOW = "BGR + Máscara verde"
# Resolución más baja solo para el procesado (más rápido). Coordenadas se reescalan al original.
SCALE = 0.75


def dy_from_y(y: int) -> float:
    """Calibración y (píxel) → distancia en cm. dy(y) ≈ 7978/(y-109) - 11.34"""
    if y <= 109:
        return float("inf")
    return 7978.0 / (y - 109) - 11.34


def main():
    camera = Camera(ip=IP)
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    try:
        while True:
            img_bgr = camera.capture()
            if img_bgr is None:
                continue
            # Procesar a resolución reducida
            small = cv2.resize(img_bgr, (0, 0), fx=SCALE, fy=SCALE)
            result, mask = detect_green_ball(small)
            # Reescalar coordenadas al tamaño original para dibujar
            display_bgr = img_bgr.copy()
            if result is not None:
                x, y, r = result
                x = int(round(x / SCALE))
                y = int(round(y / SCALE))
                r = int(round(r / SCALE))
                # Hito 2.2A: x' centrado (centro imagen = 0; derecha > 0, izquierda < 0)
                h, w = img_bgr.shape[:2]
                x_prime = x - (w / 2.0)
                # Hito 2.2B: dx (aprox), ángulo beta y distancia total
                dy = dy_from_y(y)
                k = 0.0019  # valor inicial (afinar después)
                dx = k * dy * x_prime
                beta = math.degrees(math.atan2(dx, dy))  # ángulo hacia la bola (grados)
                dist = math.hypot(dx, dy)                 # distancia total en cm
                cv2.putText(
                    display_bgr, f"dy={dy:.1f}cm dx={dx:.1f}cm", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
                cv2.putText(
                    display_bgr, f"beta={beta:.1f}deg dist={dist:.1f}cm", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
                print(f"x={x} y={y}  x'={x_prime:.1f}  dy={dy:.1f}cm  dx={dx:.1f}cm  beta={beta:.1f}deg  dist={dist:.1f}cm")
                cv2.circle(display_bgr, (x, y), r, (0, 255, 0), 2)
                cv2.circle(display_bgr, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(
                    display_bgr, "BGR - bola detectada", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
                # Coordenadas del centro en la imagen (al lado de la bola)
                coord_text = f"({x}, {y})"
                tx, ty = x + r + 10, y
                cv2.putText(
                    display_bgr, coord_text, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                )
            else:
                cv2.putText(
                    display_bgr, "BGR - sin bola", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
                )
            # Máscara B/N (3 canales para concatenar)
            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            cv2.putText(
                mask_bgr, "Mascara B/N", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
            # Mismo tamaño para lado a lado
            h, w = display_bgr.shape[:2]
            if mask_bgr.shape[:2] != (h, w):
                mask_bgr = cv2.resize(mask_bgr, (w, h))
            combined = np.hstack([display_bgr, mask_bgr])
            cv2.imshow(WINDOW, combined)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        camera.cleanup()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
