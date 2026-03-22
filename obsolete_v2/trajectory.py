"""
Hito 4: Follow the trajectory — bucle de control + máquina de estados (ball tracking).

Estados:
- SEARCH: no hay bola → gira sobre sí mismo lento hasta verla.
- TRACK: hay bola → aplica control diferencial continuo (beta, dist).
- APPROACH_STOP: dist < umbral → frena y fin.

Opcional (extensión PDF): OBSTACLE_AVOID con ultrasonidos — reservado para integración futura.
"""
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from .control import motors_command_from_beta_dist

# Distancia (cm) por debajo de la cual se considera "llegado" y se para.
DIST_STOP_CM = 18.0

# Velocidad de giro en sitio en SEARCH (0–100). Sentido: clockwise = True → derecha atrás, izquierda adelante.
SEARCH_SPEED = 18
SEARCH_CLOCKWISE = True


class TrajectoryState(Enum):
    SEARCH = "search"           # No ball → rotate in place
    TRACK = "track"             # Ball visible → differential control
    APPROACH_STOP = "approach_stop"  # dist < threshold → stop
    OBSTACLE_AVOID = "obstacle_avoid"  # Optional: ultrasonics (reserved)


def _motors_command_stop() -> Dict[str, Any]:
    """Comando: ambas ruedas paradas."""
    return {
        "motors": {
            "left": {"action": "stop", "speed": 0},
            "right": {"action": "stop", "speed": 0},
        }
    }


def _motors_command_rotate_in_place(
    speed: int = SEARCH_SPEED,
    clockwise: bool = SEARCH_CLOCKWISE,
) -> Dict[str, Any]:
    """Comando: giro en sitio (una rueda adelante, otra atrás)."""
    if clockwise:
        left_action, right_action = "forward", "backward"
    else:
        left_action, right_action = "backward", "forward"
    return {
        "motors": {
            "left": {"action": left_action, "speed": speed},
            "right": {"action": right_action, "speed": speed},
        }
    }


class TrajectoryStateMachine:
    """
    Máquina de estados para seguir la trayectoria hacia la bola.

    - Sin bola → SEARCH (giro lento en sitio).
    - Con bola y dist >= dist_stop_cm → TRACK (control diferencial).
    - Con bola y dist < dist_stop_cm → APPROACH_STOP (parar).
    """

    def __init__(
        self,
        dist_stop_cm: float = DIST_STOP_CM,
        search_speed: int = SEARCH_SPEED,
        search_clockwise: bool = SEARCH_CLOCKWISE,
    ):
        self.dist_stop_cm = dist_stop_cm
        self.search_speed = search_speed
        self.search_clockwise = search_clockwise
        self._state = TrajectoryState.SEARCH

    @property
    def state(self) -> TrajectoryState:
        return self._state

    def update(
        self,
        ball_detected: bool,
        dist_cm: Optional[float],
        beta_deg: float = 0.0,
    ) -> Tuple[TrajectoryState, Dict[str, Any]]:
        """
        Actualiza estado y devuelve el comando de motores para este frame.

        Args:
            ball_detected: True si se detectó bola verde.
            dist_cm: Distancia a la bola en cm (None si no hay bola).
            beta_deg: Ángulo hacia la bola en grados (solo usado en TRACK).

        Returns:
            (state, motors_command) con motors_command listo para JSON.
        """
        if not ball_detected:
            self._state = TrajectoryState.SEARCH
            cmd = _motors_command_rotate_in_place(
                speed=self.search_speed,
                clockwise=self.search_clockwise,
            )
            return self._state, cmd

        # Hay bola
        if dist_cm is not None and dist_cm < self.dist_stop_cm:
            self._state = TrajectoryState.APPROACH_STOP
            return self._state, _motors_command_stop()

        self._state = TrajectoryState.TRACK
        d = dist_cm if dist_cm is not None else self.dist_stop_cm
        d = max(d, 1.0)  # evitar dist 0 en control
        cmd = motors_command_from_beta_dist(beta_deg, d)
        return self._state, cmd
