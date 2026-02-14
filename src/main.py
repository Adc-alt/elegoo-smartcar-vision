"""Main - Display BGR en tiempo real + detección bola verde (máscara B/N)."""
import cv2
import numpy as np
from .camera import Camera
from .vision import detect_green_ball

IP = "192.168.4.1"
WINDOW = "BGR + Máscara verde"


def main():
    camera = Camera(ip=IP)
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    try:
        while True:
            img_bgr = camera.capture()
            if img_bgr is None:
                continue
            # Detección bola verde (BGR → HSV → máscara → contorno → centro/radio)
            result, mask = detect_green_ball(img_bgr)
            # Frame BGR con overlay de detección
            display_bgr = img_bgr.copy()
            if result is not None:
                x, y, r = result
                cv2.circle(display_bgr, (x, y), r, (0, 255, 0), 2)
                cv2.circle(display_bgr, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(
                    display_bgr, "BGR - bola detectada", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
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
