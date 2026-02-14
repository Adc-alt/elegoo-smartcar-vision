import cv2
import numpy as np
from urllib.request import urlopen, Request

CHUNK = 65536
BUF_MAX = 2 * 1024 * 1024
BUF_TRIM = 256 * 1024


class Camera:
    def __init__(self, ip="192.168.4.1"):
        self.camera_url = f"http://{ip}/stream"
        self._stream = None
        self._buffer = b""
        self._use_opencv = True
        self._cap = None
        try:
            cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
            self._cap = cv2.VideoCapture(self.camera_url)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                self._cap.release()
                self._cap = None
                self._use_opencv = False
                self._open_mjpeg_stream()
        except Exception:
            self._cap = None
            self._use_opencv = False
            self._open_mjpeg_stream()

    def _open_mjpeg_stream(self):
        try:
            req = Request(self.camera_url)
            req.add_header("Accept", "multipart/x-mixed-replace")
            self._stream = urlopen(req, timeout=10)
            self._buffer = b""
        except Exception:
            self._stream = None

    def _read_next_mjpeg_frame(self):
        if self._stream is None:
            return None
        try:
            while True:
                if b"\xff\xd8" in self._buffer:
                    start = self._buffer.index(b"\xff\xd8")
                    end = self._buffer.find(b"\xff\xd9", start) + 2
                    if end > start:
                        jpeg = bytes(self._buffer[start:end])
                        self._buffer = self._buffer[end:]
                        frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        return frame
                chunk = self._stream.read(CHUNK)
                if not chunk:
                    return None
                self._buffer += chunk
                if len(self._buffer) > BUF_MAX:
                    self._buffer = self._buffer[-BUF_TRIM:]
        except Exception:
            return None

    def capture(self):
        if self._use_opencv and self._cap is not None and self._cap.isOpened():
            ok, frame = self._cap.read()
            if ok and frame is not None:
                return frame
            self._cap.release()
            self._cap = None
            self._use_opencv = False
            self._open_mjpeg_stream()
        return self._read_next_mjpeg_frame()

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
