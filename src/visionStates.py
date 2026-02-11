"""
Módulo de Estados y Decisiones basadas en Visión
"""
from enum import Enum
from typing import Dict, Optional
from .vision import Vision


class VisionState(Enum):
    """Estados posibles del sistema basado en visión"""
    FORWARD = "forward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    BACKWARD = "backward"
    STOP = "stop"
    SCANNING = "scanning"


class VisionDecisionMaker:
    """
    Toma decisiones basadas en el análisis de visión.
    Implementa una máquina de estados que decide qué acción tomar.
    """
    
    def __init__(self, vision: Vision):
        """
        Args:
            vision: Instancia del módulo Vision
        """
        self.vision = vision
        self.current_state = VisionState.SCANNING  # Empezar escaneando
        self.previous_state = None
        self.state_history = []
        
        # Parámetros configurables
        self.min_green_area = 100.0  # Área mínima para considerar verde detectado
        
    def decide(self, vision_analysis: Dict) -> VisionState:
        """
        Toma una decisión basada en el análisis de visión (tracking de verde).
        
        Args:
            vision_analysis: Resultados del análisis de visión
            
        Returns:
            VisionState: Estado/acción decidida
        """
        self.previous_state = self.current_state
        
        # Extraer información del tracking de verde
        green_detected = vision_analysis.get('green_detected', False)
        green_position = vision_analysis.get('green_position', 'none')
        green_area = vision_analysis.get('green_area', 0.0)
        
        # Lógica simple basada en posición del verde
        if green_detected and green_area > self.min_green_area:
            # Verde detectado - decidir según posición
            if green_position == 'center':
                self.current_state = VisionState.FORWARD
            elif green_position == 'left':
                self.current_state = VisionState.TURN_LEFT
            elif green_position == 'right':
                self.current_state = VisionState.TURN_RIGHT
        else:
            # No se detecta verde - buscar/escaneo
            if self.current_state == VisionState.FORWARD:
                # Si estaba avanzando y perdió el verde, buscar
                self.current_state = VisionState.SCANNING
            elif self.current_state in [VisionState.TURN_LEFT, VisionState.TURN_RIGHT]:
                # Si está girando y no encuentra verde, continuar girando un poco más
                # (mantener estado actual)
                pass
            else:
                # En otros estados, buscar
                self.current_state = VisionState.SCANNING
        
        # Guardar en historial
        self.state_history.append({
            'state': self.current_state.value,
            'analysis': vision_analysis
        })
        
        # Limitar tamaño del historial
        if len(self.state_history) > 100:
            self.state_history.pop(0)
        
        return self.current_state
    
    def get_current_state(self) -> VisionState:
        """Retorna el estado actual"""
        return self.current_state
    
    def get_state_info(self) -> Dict:
        """Retorna información sobre el estado actual"""
        return {
            'current_state': self.current_state.value,
            'previous_state': self.previous_state.value if self.previous_state else None,
            'history_length': len(self.state_history)
        }
    
    def reset(self):
        """Reinicia el estado a FORWARD"""
        self.current_state = VisionState.FORWARD
        self.previous_state = None
        self.state_history = []
