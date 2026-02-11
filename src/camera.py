import cv2
import numpy as np
from urllib.request import urlopen, Request


class Camera:
    def __init__(self, ip="192.168.4.1"):
        self.camera_url = f"http://{ip}/stream"
        self._stream = None
        self._buffer = b""
        self._use_opencv = True
        self._cap = None
        try:
            cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
            print(f"Abriendo stream: {self.camera_url}")
            # Intentar primero con OpenCV (algunos streams lo soportan)
            self._cap = cv2.VideoCapture(self.camera_url)
            if self._cap.isOpened():
                # Buffer de 1 frame para menor latencia
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                print("Stream abierto con VideoCapture.")
            else:
                self._cap.release()
                self._cap = None
                self._use_opencv = False
                self._open_mjpeg_stream()
        except Exception as e:
            print(f"VideoCapture fallo: {e}")
            self._cap = None
            self._use_opencv = False
            self._open_mjpeg_stream()

    def _open_mjpeg_stream(self):
        """Abre el stream HTTP y deja listo para leer frames MJPEG (multipart)."""
        try:
            req = Request(self.camera_url)
            req.add_header("Accept", "multipart/x-mixed-replace")
            self._stream = urlopen(req, timeout=10)
            self._buffer = b""
            print("Stream abierto como MJPEG (multipart).")
        except Exception as e:
            print(f"No se pudo abrir stream MJPEG: {e}")
            self._stream = None

    def _read_next_mjpeg_frame(self):
        """Lee un frame JPEG del stream multipart. Devuelve array BGR o None."""
        if self._stream is None:
            return None
        try:
            # Buscar boundary en la respuesta (suele estar en Content-Type)
            while True:
                if b"\xff\xd8" in self._buffer:
                    start = self._buffer.index(b"\xff\xd8")
                    end = self._buffer.find(b"\xff\xd9", start) + 2
                    if end > start:
                        jpeg = self._buffer[start:end]
                        self._buffer = self._buffer[end:]
                        arr = np.frombuffer(jpeg, dtype=np.uint8)
                        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        return frame
                # Leer en bloques grandes (64 KB) para menos syscalls y más fluido
                chunk = self._stream.read(65536)
                if not chunk:
                    return None
                self._buffer += chunk
                if len(self._buffer) > 2 * 1024 * 1024:
                    self._buffer = self._buffer[-512 * 1024:]
        except Exception as e:
            print(f"Error leyendo frame MJPEG: {e}")
            return None

    def capture(self):
        if self._use_opencv and self._cap is not None and self._cap.isOpened():
            ok, frame = self._cap.read()
            if ok and frame is not None:
                return frame
            # Si falla, probar MJPEG una vez
            self._cap.release()
            self._cap = None
            self._use_opencv = False
            self._open_mjpeg_stream()
        return self._read_next_mjpeg_frame()

    def show_image(self, img):
        if img is not None:
            cv2.imshow("Camera", img)

    def cleanup(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        cv2.destroyAllWindows()
