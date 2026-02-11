"""
Módulo de Output - Generación de comandos JSON para ESP32
"""
import json
from typing import Dict, Optional
from .visionStates import VisionState


class OutputCommandGenerator:
    """
    Genera comandos JSON para enviar al ESP32 Access Point.
    Convierte estados de decisión en comandos específicos del robot.
    """
    
    def __init__(self):
        """Inicializa el generador de comandos"""
        self.cmd_no = 0
        
        # Mapeo de estados a comandos
        self.state_to_command = {
            VisionState.FORWARD: {'action': 'move', 'direction': 'forward', 'speed': 100},
            VisionState.TURN_LEFT: {'action': 'move', 'direction': 'left', 'speed': 100},
            VisionState.TURN_RIGHT: {'action': 'move', 'direction': 'right', 'speed': 100},
            VisionState.BACKWARD: {'action': 'move', 'direction': 'backward', 'speed': 80},
            VisionState.STOP: {'action': 'stop'},
            VisionState.SCANNING: {'action': 'stop'},  # Detener para escanear
        }
        
        # Mapeo de direcciones a códigos numéricos
        self.direction_map = {
            'forward': '3',
            'backward': '4',
            'left': '1',
            'right': '2',
        }
    
    def generate_command(self, state: VisionState, 
                        additional_params: Optional[Dict] = None) -> str:
        """
        Genera un comando JSON basado en el estado de visión.
        
        Args:
            state: Estado de visión actual
            additional_params: Parámetros adicionales opcionales
                Ejemplo: {'speed': 150, 'servo_angle': 90}
        
        Returns:
            str: Comando JSON formateado para enviar al ESP32
        """
        self.cmd_no += 1
        
        # Obtener configuración base del estado
        state_config = self.state_to_command.get(state, {'action': 'stop'})
        
        # Crear mensaje base
        msg = {"H": str(self.cmd_no)}
        
        # Generar comando según la acción
        if state_config['action'] == 'move':
            msg = self._create_move_command(msg, state_config, additional_params)
        
        elif state_config['action'] == 'stop':
            msg = self._create_stop_command(msg)
        
        elif state_config['action'] == 'rotate':
            msg = self._create_rotate_command(msg, additional_params)
        
        elif state_config['action'] == 'servo':
            msg = self._create_servo_command(msg, additional_params)
        
        elif state_config['action'] == 'measure':
            msg = self._create_measure_command(msg, additional_params)
        
        return json.dumps(msg)
    
    def _create_move_command(self, msg: Dict, state_config: Dict,
                            additional_params: Optional[Dict]) -> Dict:
        """Crea comando de movimiento"""
        direction = state_config.get('direction', 'forward')
        speed = additional_params.get('speed', None) if additional_params else None
        speed = speed or state_config.get('speed', 100)
        
        msg['N'] = '3'  # Comando de movimiento
        msg['D1'] = self.direction_map.get(direction, '3')
        msg['D2'] = str(speed)
        
        return msg
    
    def _create_stop_command(self, msg: Dict) -> Dict:
        """Crea comando de detención"""
        msg['N'] = '1'
        msg['D1'] = '0'
        msg['D2'] = '0'
        msg['D3'] = '1'
        
        return msg
    
    def _create_rotate_command(self, msg: Dict,
                              additional_params: Optional[Dict]) -> Dict:
        """Crea comando de rotación del servo"""
        angle = additional_params.get('angle', 90) if additional_params else 90
        
        msg['N'] = '5'
        msg['D1'] = '1'  # Tipo de servo (1 = left/right)
        msg['D2'] = str(angle)
        
        return msg
    
    def _create_servo_command(self, msg: Dict,
                             additional_params: Optional[Dict]) -> Dict:
        """Crea comando para rotar servo específico"""
        servo_type = additional_params.get('servo_type', 1) if additional_params else 1
        angle = additional_params.get('angle', 90) if additional_params else 90
        
        msg['N'] = '5'
        msg['D1'] = str(servo_type)
        msg['D2'] = str(angle)
        
        return msg
    
    def _create_measure_command(self, msg: Dict,
                               additional_params: Optional[Dict]) -> Dict:
        """Crea comando de medición"""
        measure_type = additional_params.get('type', 'distance') if additional_params else 'distance'
        
        if measure_type == 'distance':
            msg['N'] = '21'
            msg['D1'] = '2'  # Medir distancia directamente
        elif measure_type == 'obstacle':
            msg['N'] = '21'
            msg['D1'] = '1'  # Solo detectar obstáculo
        elif measure_type == 'motion':
            msg['N'] = '6'  # Medir movimiento MPU6050
        
        return msg
    
    def generate_custom_command(self, command_type: str,
                               params: Dict) -> str:
        """
        Genera un comando personalizado.
        
        Args:
            command_type: Tipo de comando ('move', 'stop', 'rotate', 'servo', 'measure')
            params: Parámetros del comando
        
        Returns:
            str: Comando JSON formateado
        """
        self.cmd_no += 1
        msg = {"H": str(self.cmd_no)}
        
        if command_type == 'move':
            msg = self._create_move_command(msg, params, None)
        elif command_type == 'stop':
            msg = self._create_stop_command(msg)
        elif command_type == 'rotate':
            msg = self._create_rotate_command(msg, params)
        elif command_type == 'servo':
            msg = self._create_servo_command(msg, params)
        elif command_type == 'measure':
            msg = self._create_measure_command(msg, params)
        
        return json.dumps(msg)
    
    def reset_command_counter(self):
        """Reinicia el contador de comandos"""
        self.cmd_no = 0
