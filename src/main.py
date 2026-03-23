"""Video MJPEG + detección verde + trayectoria visual + comandos diferenciales (JSON al coche)."""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2

if __package__ is None:
    _repo_root = Path(__file__).resolve().parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from src.car_motors import CarMotorsHttp
from src import control as diff_ctrl
from src.stream_reader import STREAM_URL
from src.vision import green_detect

WIN_BGR = "BGR"
WIN_MASK = "mask"

# Calibración: d_y ≈ a + C/(y - y0)
_DY_A = -10.35
_DY_C = 7285.24
_DY_Y0 = 87.30
_DX_K = -0.0025

_MIN_ABS_SIN_BETA = 0.02

# No inundar Wi‑Fi ni la consola
_MIN_SEND_INTERVAL_S = 0.07
_PRINT_INTERVAL_S = 0.35


def estimate_dy_cm(y: float) -> float | None:
    if y <= _DY_Y0:
        return None
    return _DY_A + _DY_C / (y - _DY_Y0)


def estimate_dx_cm(x_prime: float, dy_cm: float) -> float:
    return _DX_K * dy_cm * x_prime


def turn_radius_display_cm(d_cm: float, beta_rad: float) -> float | None:
    s = math.sin(beta_rad)
    if abs(s) < _MIN_ABS_SIN_BETA:
        return None
    return d_cm / (2.0 * s)


def _robot_anchor(w: int, h: int) -> tuple[int, int]:
    return w // 2, h - 28


def _draw_speed_bars(
    img,
    y_top: int,
    v_left: int,
    v_right: int,
    bar_max_w: int = 90,
) -> None:
    x0 = 10
    for i, (label, v) in enumerate((("L", v_left), ("R", v_right))):
        yb = y_top + i * 24
        cv2.rectangle(img, (x0, yb), (x0 + bar_max_w, yb + 18), (45, 45, 45), -1)
        fill = int(bar_max_w * max(0, min(100, v)) / 100.0)
        cv2.rectangle(img, (x0, yb), (x0 + fill, yb + 18), (0, 180, 255), -1)
        cv2.putText(
            img,
            f"{label} {v:3d}",
            (x0 + bar_max_w + 6, yb + 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (240, 240, 240),
            1,
            cv2.LINE_AA,
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Visión + control diferencial hacia la bola.")
    ap.add_argument(
        "--no-send",
        action="store_true",
        help="Solo muestra trayectoria y comandos; no envía HTTP al coche.",
    )
    ap.add_argument("--car-host", default="192.168.4.1", help="IP del AP del coche.")
    ap.add_argument("--car-port", type=int, default=80, help="Puerto del WebServer (HTTP).")
    ap.add_argument(
        "--car-path",
        default="/motors",
        help='Ruta POST JSON (p. ej. /motors). Debe coincidir con WebServerHost en el firmware.',
    )
    ap.add_argument(
        "--car-http-timeout",
        type=float,
        default=0.35,
        help="Timeout por POST (s). Cada comando abre TCP nuevo; en WiFi conviene ≥0.3.",
    )
    ap.add_argument(
        "--verbose-http",
        action="store_true",
        help="Imprime HTTP 2xx/3xx y cuerpo de cada POST (throttle ~0.4s). Errores HTTP siempre.",
    )
    args = ap.parse_args()

    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("No se abre la URL (WiFi al coche, o prueba /stream en vez de /streaming):", STREAM_URL)
        return
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    car: CarMotorsHttp | None = None
    if not args.no_send:
        car = CarMotorsHttp(
            host=args.car_host,
            port=args.car_port,
            path=args.car_path,
            request_timeout_s=args.car_http_timeout,
            verbose_http=args.verbose_http,
        )
        if car.connect():
            car.start_worker()
            base = f"http://{args.car_host}:{args.car_port}{args.car_path}"
            vh = " + --verbose-http" if args.verbose_http else ""
            print(f"Motores HTTP POST {base} (hilo + cola, TCP nuevo por POST){vh}", flush=True)
            if not args.verbose_http:
                print(
                    '  Tip: --verbose-http para ver HTTP 200 y cuerpo (p. ej. {"ok":true}).',
                    flush=True,
                )
        else:
            print(
                f"No responde HTTP en {args.car_host}:{args.car_port} "
                f"(probe: GET / o POST {args.car_path}) — modo solo visual.",
                flush=True,
            )
            car.shutdown()
            car = None
    else:
        print("Modo --no-send: comandos solo en pantalla / consola.", flush=True)

    print(
        "Geometría: dy, dx, d, beta | Control: R=d/(2*sin beta) deadband 5° | "
        f"vel base {diff_ctrl.SPEED_BASE_NEAR}-{diff_ctrl.SPEED_BASE_FAR} (0-100)",
        flush=True,
    )
    cv2.namedWindow(WIN_BGR, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_MASK, cv2.WINDOW_NORMAL)
    placed = False
    last_send_t = 0.0
    last_print_t = 0.0
    stop_payload = diff_ctrl.motors_command_from_wheel_speeds(0, 0)

    try:
        while True:
            ok, frame = cap.read()
            if not (ok and frame is not None):
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            pt, mask, r_ball = green_detect(frame)
            bgr = frame.copy()
            h, w = bgr.shape[:2]
            rx, ry = _robot_anchor(w, h)

            payload = stop_payload
            overlay = "IDLE: no target"
            v_l = v_r = 0
            beta_deg = 0.0
            d_cm = 0.0
            dy_cm_debug = None
            r_turn_display_s = None

            if pt is not None and r_ball > 0:
                x, y = pt
                x_prime = x - (w / 2.0)
                dy_cm = estimate_dy_cm(float(y))
                cv2.circle(bgr, pt, r_ball, (0, 255, 0), 2)

                if dy_cm is not None:
                    dy_cm_debug = dy_cm
                    dx_cm = estimate_dx_cm(x_prime, dy_cm)
                    d_cm = math.hypot(dx_cm, dy_cm)
                    beta_rad = math.atan2(dx_cm, dy_cm)
                    beta_deg = math.degrees(beta_rad)
                    d_safe = max(d_cm, 1.0)
                    payload = diff_ctrl.motors_command_from_beta_dist(beta_rad, d_safe)
                    v_l = payload["motors"]["left"]["speed"]
                    v_r = payload["motors"]["right"]["speed"]
                    overlay = f"TRACK  L={v_l} R={v_r}  beta={beta_deg:+.1f}deg  d={d_cm:.1f}cm"

                    # Trayectoria deseada: ancla del robot → centro de la bola
                    cv2.line(bgr, (rx, ry), (x, y), (255, 200, 0), 2, cv2.LINE_AA)
                    cv2.circle(bgr, (rx, ry), 8, (200, 200, 255), -1)
                    cv2.putText(
                        bgr,
                        "robot",
                        (rx - 28, ry + 28),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (200, 200, 255),
                        1,
                        cv2.LINE_AA,
                    )

                    r_ctrl = diff_ctrl.turn_radius_cm(beta_rad, d_safe)
                    r_txt = (
                        "straight"
                        if not math.isfinite(r_ctrl) or abs(r_ctrl) > 1e5
                        else f"R={r_ctrl:.0f}cm"
                    )
                    cv2.putText(
                        bgr,
                        r_txt,
                        (x + r_ball + 6, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (180, 255, 200),
                        1,
                        cv2.LINE_AA,
                    )

                    # Para consola: radio de giro usando el modelo de visualización (sin deadband por dist_safe).
                    _r_turn = turn_radius_display_cm(d_cm, beta_rad)
                    r_turn_display_s = f"{_r_turn:.1f}cm" if _r_turn is not None else "n/a"
                else:
                    overlay = f"no dy (y<={_DY_Y0})"

            _draw_speed_bars(bgr, h - 58, v_l, v_r)
            cv2.putText(
                bgr,
                overlay[:80],
                (10, 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                (0, 255, 0) if v_l + v_r > 0 else (120, 120, 255),
                2,
                cv2.LINE_AA,
            )
            j_compact = json.dumps(payload, separators=(",", ":"))
            cv2.putText(
                bgr,
                j_compact[:95] + ("..." if len(j_compact) > 95 else ""),
                (10, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 220, 200),
                1,
                cv2.LINE_AA,
            )

            now = time.monotonic()
            if car is not None:
                if now - last_send_t >= _MIN_SEND_INTERVAL_S:
                    car.offer_json(payload)
                    last_send_t = now

            if now - last_print_t >= _PRINT_INTERVAL_S:
                last_print_t = now
                if pt is not None and r_ball > 0:
                    x, y = pt
                    if dy_cm_debug is not None:
                        print(
                            f"x={x} y={y} d={d_cm:.2f}cm beta={beta_deg:+.1f}deg "
                            f"r_turn~{r_turn_display_s} | cmd L={v_l} R={v_r} | {j_compact}",
                            flush=True,
                        )
                    else:
                        print(f"x={x} y={y} dy=n/a | {j_compact}", flush=True)
                else:
                    print(f"no ball | {j_compact}", flush=True)

            cv2.putText(bgr, "BGR", (w - 72, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
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
        if car is not None:
            car.offer_json(stop_payload)
            time.sleep(0.05)
            car.shutdown()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
