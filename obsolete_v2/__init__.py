"""
Robot Control Package - Vision-based control for ELEGOO Smart Robot Car.
"""

import sys
from pathlib import Path

# Running `python src/__init__.py` leaves __package__ unset; relative imports fail.
if __package__ is None:
    _repo_root = Path(__file__).resolve().parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from src.camera import Camera
    from src.connection import connection
    from src.vision import Vision
    from src.visionStates import VisionState, VisionDecisionMaker
    from src.output import OutputCommandGenerator
else:
    from .camera import Camera
    from .connection import connection
    from .vision import Vision
    from .visionStates import VisionState, VisionDecisionMaker
    from .output import OutputCommandGenerator

__all__ = [
    "Camera",
    "connection",
    "Vision",
    "VisionState",
    "VisionDecisionMaker",
    "OutputCommandGenerator",
]
