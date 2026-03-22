"""Generación de comandos JSON para ESP32 (solo move/stop usados por el pipeline)."""
import json
from typing import Dict, Optional
from .visionStates import VisionState

_DIR = {"forward": "3", "backward": "4", "left": "1", "right": "2"}

_STATE_CMD = {
    VisionState.FORWARD: ("move", "forward", 100),
    VisionState.TURN_LEFT: ("move", "left", 100),
    VisionState.TURN_RIGHT: ("move", "right", 100),
    VisionState.BACKWARD: ("move", "backward", 80),
    VisionState.STOP: ("stop", None, None),
    VisionState.SCANNING: ("stop", None, None),
}


class OutputCommandGenerator:
    def __init__(self):
        self.cmd_no = 0

    def generate_command(self, state: VisionState, additional_params: Optional[Dict] = None) -> str:
        self.cmd_no += 1
        msg = {"H": str(self.cmd_no)}
        action, direction, speed = _STATE_CMD.get(state, ("stop", None, None))
        if action == "move":
            msg["N"] = "3"
            msg["D1"] = _DIR.get(direction, "3")
            msg["D2"] = str(additional_params.get("speed", speed) if additional_params else speed)
        else:
            msg["N"] = "1"
            msg["D1"] = "0"
            msg["D2"] = "0"
            msg["D3"] = "1"
        return json.dumps(msg)
