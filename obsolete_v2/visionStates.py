"""Estados y decisiones basadas en visión (tracking verde)."""
from enum import Enum
from typing import Dict


class VisionState(Enum):
    FORWARD = "forward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    BACKWARD = "backward"
    STOP = "stop"
    SCANNING = "scanning"


class VisionDecisionMaker:
    def __init__(self, min_green_area: float = 100.0):
        self.current_state = VisionState.SCANNING
        self.min_green_area = min_green_area

    def decide(self, vision_analysis: Dict) -> VisionState:
        green_detected = vision_analysis.get("green_detected", False)
        green_position = vision_analysis.get("green_position", "none")
        green_area = vision_analysis.get("green_area", 0.0)
        if green_detected and green_area > self.min_green_area:
            if green_position == "center":
                self.current_state = VisionState.FORWARD
            elif green_position == "left":
                self.current_state = VisionState.TURN_LEFT
            elif green_position == "right":
                self.current_state = VisionState.TURN_RIGHT
        else:
            if self.current_state == VisionState.FORWARD:
                self.current_state = VisionState.SCANNING
            elif self.current_state not in (VisionState.TURN_LEFT, VisionState.TURN_RIGHT):
                self.current_state = VisionState.SCANNING
        return self.current_state

    def get_current_state(self) -> VisionState:
        return self.current_state
