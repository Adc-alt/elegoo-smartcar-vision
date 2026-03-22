import time

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
        self._cap = None
        # ESP32 MJPEG: urllib multipart read is usually reliable on Windows.
        # cv2.VideoCapture(http://...) often opens but fails to decode frames.
        self._use_opencv = False
        self._last_reconnect = 0.0
        self._open_mjpeg_stream()
        if self._stream is None:
            try:
                self._cap = cv2.VideoCapture(self.camera_url)
                if self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self._use_opencv = True
                else:
                    self._cap.release()
                    self._cap = None
            except Exception:
                self._cap = None

    def _open_mjpeg_stream(self):
        try:
            req = Request(self.camera_url)
            req.add_header("Accept", "multipart/x-mixed-replace")
            self._stream = urlopen(req, timeout=10)
            self._buffer = b""
        except Exception:
            self._stream = None

    def _reconnect_mjpeg(self) -> None:
        """Reopen HTTP stream (EOF, failed decode loop, or never connected). Throttled."""
        now = time.monotonic()
        if self._last_reconnect > 0 and (now - self._last_reconnect < 0.25):
            return
        self._last_reconnect = now
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._buffer = b""
        self._open_mjpeg_stream()

    def _read_next_mjpeg_frame(self):
        if self._stream is None:
            return None
        try:
            while True:
                soi = self._buffer.find(b"\xff\xd8")
                if soi >= 0:
                    eoi = self._buffer.find(b"\xff\xd9", soi + 2)
                    if eoi < 0:
                        pass  # need more bytes after SOI
                    else:
                        end = eoi + 2
                        jpeg = bytes(self._buffer[soi:end])
                        self._buffer = self._buffer[end:]
                        frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            return frame
                        continue  # corrupt JPEG, skip
                else:
                    # No SOI: drop leading noise (multipart headers) but keep tail
                    if len(self._buffer) > BUF_MAX:
                        self._buffer = self._buffer[-BUF_TRIM:]
                    # Not MJPEG/HTML error: avoid blocking forever without JPEG markers
                    if len(self._buffer) > 256_000:
                        self._buffer = b""
                        return None
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
        frame = self._read_next_mjpeg_frame()
        if frame is None and not self._use_opencv:
            self._reconnect_mjpeg()
        return frame

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
