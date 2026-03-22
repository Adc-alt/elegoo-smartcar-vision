"""
Control diferencial para ball tracking (Hito 3.1 / 3.2).

- Radio de giro: R = d / (2*sin(β)); si |β| < 5° → recto (R → ∞).
- Ratio de velocidades: v_R/v_L = (R - Δ)/(R + Δ), con Δ = mitad distancia entre ruedas.
- wheel_speeds_from_beta_dist(beta, dist): velocidad base por dist, esterzo por beta.
- motors_command_from_beta_dist(): mismo control pero devuelve dict listo para JSON (motors.left/right.action, speed).
"""
import math
from typing import Any, Dict, Tuple

# Mitad de la distancia entre ruedas (cm). ELEGOO: 12.5 cm entre ruedas → Δ = 6.25 cm.
DELTA_CM = 6.25

# Deadband: |beta| < 5° → recto (evitar div ~0 y oscilaciones).
DEADBAND_DEG = 5.0

# Rango de velocidad para JSON (ESP32: speed 0-100 o el que use processDifferentialMotors).
SPEED_MIN = 0
SPEED_MAX = 100

# Velocidad base: distancias de referencia (cm) para “cerca” (más lento) y “lejos” (más rápido).
DIST_NEAR_CM = 15.0
DIST_FAR_CM = 80.0
# Velocidad base cuando la bola está muy cerca / muy lejos (dentro de SPEED_MIN..SPEED_MAX).
SPEED_BASE_NEAR = 25
SPEED_BASE_FAR = 85


def turn_radius_cm(beta_rad: float, dist_cm: float) -> float:
    """
    Radio de giro hacia la bola: R = d / (2*sin(β)).
    Si |beta| < DEADBAND_DEG → recto → retorna inf.
    """
    if abs(math.degrees(beta_rad)) < DEADBAND_DEG:
        return float("inf")
    sin_b = math.sin(beta_rad)
    if abs(sin_b) < 1e-6:
        return float("inf")
    return dist_cm / (2.0 * sin_b)


def wheel_speed_ratio(R_cm: float, delta_cm: float = DELTA_CM) -> float:
    """
    Ratio de velocidades rueda derecha / rueda izquierda: v_R/v_L = (R - Δ)/(R + Δ).
    R → ∞ (recto) ⇒ ratio = 1. R > 0 (girar derecha) ⇒ ratio < 1. R < 0 (girar izquierda) ⇒ ratio > 1.
    """
    if not math.isfinite(R_cm) or abs(R_cm) > 1e6:
        return 1.0
    return (R_cm - delta_cm) / (R_cm + delta_cm)


def wheel_speeds_from_beta_dist(
    beta_deg: float,
    dist_cm: float,
    delta_cm: float = DELTA_CM,
    speed_min: int = SPEED_MIN,
    speed_max: int = SPEED_MAX,
    dist_near_cm: float = DIST_NEAR_CM,
    dist_far_cm: float = DIST_FAR_CM,
    speed_base_near: int = SPEED_BASE_NEAR,
    speed_base_far: int = SPEED_BASE_FAR,
) -> Tuple[int, int]:
    """
    Calcula velocidades de ruedas para ir hacia la bola (misma lógica, rango configurable).

    - Velocidad base según dist: más lejos → más rápido; más cerca → más lento (saturado).
    - Estereo según beta: ratio diferencial v_R/v_L = (R - Δ)/(R + Δ).
    - Deadband: |beta| < 5° → recto (ruedas iguales).
    - Salida saturada a [speed_min, speed_max].

    Returns:
        (left_speed, right_speed) en el rango indicado (p. ej. 0-100 para JSON).
    """
    beta_rad = math.radians(beta_deg)

    # 1) Velocidad base en función de la distancia (más lejos → más rápido).
    if dist_cm <= dist_near_cm:
        base = float(speed_base_near)
    elif dist_cm >= dist_far_cm:
        base = float(speed_base_far)
    else:
        t = (dist_cm - dist_near_cm) / (dist_far_cm - dist_near_cm)
        base = speed_base_near + t * (speed_base_far - speed_base_near)

    # 2) Radio de giro y ratio (con deadband 5°).
    R = turn_radius_cm(beta_rad, dist_cm)
    ratio = wheel_speed_ratio(R, delta_cm)

    # 3) Repartir base en v_L y v_R con v_R/v_L = ratio y (v_L + v_R)/2 = base.
    if abs(1.0 + ratio) < 1e-6:
        v_l = base
        v_r = base
    else:
        v_l = 2.0 * base / (1.0 + ratio)
        v_r = ratio * v_l

    # 4) Saturar a rango de velocidad.
    v_l = max(speed_min, min(speed_max, round(v_l)))
    v_r = max(speed_min, min(speed_max, round(v_r)))

    return int(v_l), int(v_r)


def motors_command_from_beta_dist(
    beta_deg: float,
    dist_cm: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Misma lógica que wheel_speeds_from_beta_dist pero devuelve un dict listo para JSON
    compatible con el ESP32:

      receiveJson["motors"]["left"]["action"], receiveJson["motors"]["left"]["speed"]
      receiveJson["motors"]["right"]["action"], receiveJson["motors"]["right"]["speed"]

    action: "forward" si speed > 0, "stop" si speed == 0 (para marcha atrás se podría usar "backward").
    speed: entero en [SPEED_MIN, SPEED_MAX] (p. ej. 0-100).

    Returns:
        {"motors": {"left": {"action": "forward"|"stop", "speed": int}, "right": {...}}}
    """
    left_speed, right_speed = wheel_speeds_from_beta_dist(beta_deg, dist_cm, **kwargs)

    def action(s: int) -> str:
        return "forward" if s > 0 else "stop"

    return {
        "motors": {
            "left": {"action": action(left_speed), "speed": left_speed},
            "right": {"action": action(right_speed), "speed": right_speed},
        }
    }
