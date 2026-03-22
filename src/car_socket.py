"""TCP al coche (puerto 100): envío de JSON en hilo aparte para no bloquear OpenCV."""
from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any, Dict, Optional

CONNECT_WAIT_S = 0.3
SEND_TIMEOUT_S = 0.08


class CarSocket:
    def __init__(self, host: str = "192.168.4.1", port: int = 100) -> None:
        self._host = host
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._q: queue.Queue[Optional[Dict[str, Any]]] = queue.Queue(maxsize=1)
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> bool:
        self.close()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect((self._host, self._port))
            s.settimeout(SEND_TIMEOUT_S)
            self._sock = s
            time.sleep(CONNECT_WAIT_S)
            return True
        except OSError:
            self._sock = None
            return False

    def start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run, name="car-socket", daemon=True)
        self._worker.start()

    def stop_worker(self) -> None:
        self._stop.set()
        try:
            self._q.put_nowait(None)
        except queue.Full:
            pass
        if self._worker:
            self._worker.join(timeout=1.5)
            self._worker = None
        try:
            while True:
                self._q.get_nowait()
        except queue.Empty:
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                break
            self._send_now(item)

    def _send_now(self, payload: Dict[str, Any]) -> None:
        if not self._sock:
            return
        try:
            line = json.dumps(payload, separators=(",", ":"))
            self._sock.sendall(line.encode("utf-8"))
        except OSError:
            self.close()

    def offer_json(self, payload: Dict[str, Any]) -> None:
        """Encola el último comando; descarta el anterior si aún no se envió."""
        if not self._sock:
            return
        try:
            self._q.put_nowait(payload)
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            try:
                self._q.put_nowait(payload)
            except queue.Full:
                pass

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def shutdown(self) -> None:
        self.stop_worker()
        self.close()
