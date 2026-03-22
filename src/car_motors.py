"""HTTP POST /motors al WebServer del ESP32 (p. ej. puerto 80), en hilo + cola (último comando).

Una conexión TCP nueva por POST con Connection: close — muchos WebServer en ESP32 no mantienen
keep-alive bien; reutilizar HTTPConnection provocaba RemoteDisconnected / timeouts en ráfaga.
"""
from __future__ import annotations

import http.client
import json
import queue
import threading
import time
from typing import Any, Dict, Optional, Tuple

# Respuestas del ESP suelen ser JSON corto; leer de una vez basta.
_MAX_BODY_LOG_LEN = 400
# Con --verbose-http, no imprimir cada POST OK más de una vez por intervalo.
_VERBOSE_OK_INTERVAL_S = 0.4
# Errores de red/HTTP: no inundar consola si el bucle repite rápido.
_ERROR_LOG_INTERVAL_S = 2.0
_OK_FALSE_WARN_INTERVAL_S = 1.0

# Probe por si el firmware no sirve GET / pero sí POST /motors.
_STOP_PROBE_BODY = json.dumps(
    {
        "motors": {
            "left": {"action": "stop", "speed": 0},
            "right": {"action": "stop", "speed": 0},
        }
    },
    separators=(",", ":"),
).encode("utf-8")


def _read_http_response(conn: http.client.HTTPConnection) -> Tuple[int, str, bytes]:
    r = conn.getresponse()
    raw = r.read()
    reason = getattr(r, "reason", "") or ""
    if isinstance(reason, bytes):
        reason = reason.decode("latin-1", errors="replace")
    return r.status, reason, raw


class CarMotorsHttp:
    def __init__(
        self,
        host: str = "192.168.4.1",
        port: int = 80,
        path: str = "/motors",
        request_timeout_s: float = 0.35,
        *,
        verbose_http: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._path = path if path.startswith("/") else f"/{path}"
        self._request_timeout_s = request_timeout_s
        self._verbose_http = verbose_http
        self._q: queue.Queue[Optional[Dict[str, Any]]] = queue.Queue(maxsize=1)
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._probe_ok = False
        self._last_verbose_ok_log_t = 0.0
        self._last_error_log_t = 0.0
        self._last_ok_false_warn_t = 0.0

    @property
    def connected(self) -> bool:
        return self._probe_ok

    def connect(self) -> bool:
        """Prueba GET /; si falla, POST a self._path con parada (firmware sin raíz HTTP)."""
        self._probe_ok = False

        try:
            c = http.client.HTTPConnection(self._host, self._port, timeout=3.0)
            try:
                c.request("GET", "/")
                st, reason, raw = _read_http_response(c)
                if self._verbose_http:
                    self._log_line(f"probe GET / -> HTTP {st} {reason!s} body={self._body_preview(raw)}")
            finally:
                c.close()
            self._probe_ok = True
            return True
        except (OSError, http.client.HTTPException):
            pass

        try:
            c = http.client.HTTPConnection(self._host, self._port, timeout=3.0)
            try:
                h = {
                    "Host": self._host,
                    "Content-Type": "application/json",
                    "Content-Length": str(len(_STOP_PROBE_BODY)),
                    "Connection": "close",
                }
                c.request("POST", self._path, body=_STOP_PROBE_BODY, headers=h)
                st, reason, raw = _read_http_response(c)
                if self._verbose_http or st >= 400:
                    self._log_line(
                        f"probe POST {self._path} (stop) -> HTTP {st} {reason!s} body={self._body_preview(raw)}"
                    )
                self._warn_if_json_ok_false(st, raw)
                if st >= 400:
                    return False
            finally:
                c.close()
            self._probe_ok = True
            return True
        except (OSError, http.client.HTTPException):
            return False

    def _body_preview(self, raw: bytes) -> str:
        t = raw.decode("utf-8", errors="replace")
        if len(t) > _MAX_BODY_LOG_LEN:
            return repr(t[:_MAX_BODY_LOG_LEN] + "…")
        return repr(t)

    def _log_line(self, msg: str) -> None:
        print(f"[motors-http] {msg}", flush=True)

    def _log_post_result(self, status: int, reason: str, raw: bytes) -> None:
        body = self._body_preview(raw)
        line = f"POST {self._path} -> HTTP {status} {reason!s} body={body}"
        if status >= 400:
            self._log_line(line)
            return
        if not self._verbose_http:
            return
        now = time.monotonic()
        if now - self._last_verbose_ok_log_t < _VERBOSE_OK_INTERVAL_S:
            return
        self._last_verbose_ok_log_t = now
        self._log_line(line)

    def _log_post_exception(self, exc: BaseException) -> None:
        now = time.monotonic()
        if now - self._last_error_log_t < _ERROR_LOG_INTERVAL_S and not self._verbose_http:
            return
        self._last_error_log_t = now
        self._log_line(f"POST {self._path} error: {type(exc).__name__}: {exc}")

    def _warn_if_json_ok_false(self, status: int, raw: bytes) -> None:
        if status >= 400 or not raw.strip():
            return
        try:
            j = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if isinstance(j, dict) and j.get("ok") is False:
            now = time.monotonic()
            if now - self._last_ok_false_warn_t < _OK_FALSE_WARN_INTERVAL_S:
                return
            self._last_ok_false_warn_t = now
            self._log_line(f"POST {self._path} cuerpo JSON con ok:false body={self._body_preview(raw)}")

    def start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run, name="car-motors-http", daemon=True)
        self._worker.start()

    def stop_worker(self) -> None:
        self._stop.set()
        try:
            self._q.put_nowait(None)
        except queue.Full:
            pass
        if self._worker:
            self._worker.join(timeout=2.0)
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
            self._post_json(item)

    def _post_json(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Host": self._host,
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "close",
        }
        conn: Optional[http.client.HTTPConnection] = None
        try:
            conn = http.client.HTTPConnection(
                self._host,
                self._port,
                timeout=self._request_timeout_s,
            )
            conn.request("POST", self._path, body=body, headers=headers)
            status, reason, raw = _read_http_response(conn)
            self._log_post_result(status, reason, raw)
            self._warn_if_json_ok_false(status, raw)
        except (OSError, http.client.HTTPException) as e:
            self._log_post_exception(e)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except OSError:
                    pass

    def offer_json(self, payload: Dict[str, Any]) -> None:
        if not self._probe_ok:
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

    def shutdown(self) -> None:
        self.stop_worker()
        self._probe_ok = False
