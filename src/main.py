"""
Main - Solo retransmisión de cámara
"""
import time
import cv2

from .camera import Camera


def main():
    """Muestra solo la retransmisión de la cámara."""
    ip = "192.168.4.1"
    print(f"Conectando a cámara en {ip}...")
    camera = Camera(ip=ip)
    print("Mostrando retransmisión. Cierra la ventana o pulsa 'q' para salir.\n")

    try:
        while True:
            img = camera.capture()
            if img is None:
                print("No se pudo capturar imagen")
                time.sleep(0.5)
                continue
            camera.show_image(img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        camera.cleanup()
        print("Cerrado.")


if __name__ == "__main__":
    main()
