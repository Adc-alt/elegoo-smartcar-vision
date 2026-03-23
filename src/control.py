"""Control diferencial hacia la bola: radio R = d/(2*sin β), ratio ruedas, salida 0–100."""
import math
from typing import Any, Dict, Tuple

# Mitad del eje en cm (ELEGOO ~12.5 cm entre ruedas → Δ = 6.25).
DELTA_CM = 6.25

DEADBAND_DEG = 5.0

SPEED_MIN = 0
SPEED_MAX = 100

# Velocidades bajas para pruebas (subir cuando el comportamiento sea estable).
DIST_NEAR_CM = 15.0
DIST_FAR_CM = 80.0
SPEED_BASE_NEAR = 8
SPEED_BASE_FAR = 24

# Refuerzo de giro para que el robot encare con claridad.
# Beta<0 (bola a la izquierda en tu convención) debe hacer: right > left.
K_BETA_SPEED = 30.0  # cuanto más grande, más diferencial
MAX_STEER_DIFF = 16.0  # limita la diferencia máxima añadida por beta (evita saturaciones locas)


def turn_radius_cm(beta_rad: float, dist_cm: float) -> float:
    if abs(math.degrees(beta_rad)) < DEADBAND_DEG:
        return float("inf")
    sin_b = math.sin(beta_rad)
    if abs(sin_b) < 1e-6:
        return float("inf")
    return dist_cm / (2.0 * sin_b)


def wheel_speed_ratio(R_cm: float, delta_cm: float = DELTA_CM) -> float:
    if not math.isfinite(R_cm) or abs(R_cm) > 1e6:
        return 1.0
    return (R_cm - delta_cm) / (R_cm + delta_cm)


def wheel_speeds_from_beta_dist(
    beta_rad: float,
    dist_cm: float,
    delta_cm: float = DELTA_CM,
    speed_min: int = SPEED_MIN,
    speed_max: int = SPEED_MAX,
    dist_near_cm: float = DIST_NEAR_CM,
    dist_far_cm: float = DIST_FAR_CM,
    speed_base_near: int = SPEED_BASE_NEAR,
    speed_base_far: int = SPEED_BASE_FAR,
) -> Tuple[int, int]:
    if dist_cm <= dist_near_cm:
        base = float(speed_base_near)
    elif dist_cm >= dist_far_cm:
        base = float(speed_base_far)
    else:
        t = (dist_cm - dist_near_cm) / (dist_far_cm - dist_near_cm)
        base = speed_base_near + t * (speed_base_far - speed_base_near)

    R = turn_radius_cm(beta_rad, dist_cm)
    ratio = wheel_speed_ratio(R, delta_cm)

    if abs(1.0 + ratio) < 1e-6:
        v_l = base
        v_r = base
    else:
        v_l = 2.0 * base / (1.0 + ratio)
        v_r = ratio * v_l

    # P sobre beta (rad): amplifica el giro cuando el ratio geométrico se aplana (|R| >> Δ).
    # Con beta<0 -> steer<0 -> v_l baja y v_r sube (right_speed > left_speed).
    steer = K_BETA_SPEED * beta_rad
    if abs(steer) > MAX_STEER_DIFF:
        steer = math.copysign(MAX_STEER_DIFF, steer)
    v_l = v_l + steer
    v_r = v_r - steer

    v_l = max(speed_min, min(speed_max, round(v_l)))
    v_r = max(speed_min, min(speed_max, round(v_r)))
    return int(v_l), int(v_r)


def motors_command_from_wheel_speeds(left_speed: int, right_speed: int) -> Dict[str, Any]:
    def action(s: int) -> str:
        return "forward" if s > 0 else "stop"

    return {
        "motors": {
            "left": {"action": action(left_speed), "speed": left_speed},
            "right": {"action": action(right_speed), "speed": right_speed},
        }
    }


def motors_command_from_beta_dist(beta_rad: float, dist_cm: float, **kwargs: Any) -> Dict[str, Any]:
    left_speed, right_speed = wheel_speeds_from_beta_dist(beta_rad, dist_cm, **kwargs)
    return motors_command_from_wheel_speeds(left_speed, right_speed)
