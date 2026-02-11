"""
Módulo de Visión - Tracking de color verde
"""
import cv2
import numpy as np
from typing import Dict, Optional, Tuple


class Vision:
    """
    Clase simple para trackear el color verde en los frames de la cámara.
    """
    
    def __init__(self):
        """Inicializa el módulo de visión"""
        self.last_image = None
        
        # Rangos HSV para el color verde (ajustables)
        # Verde en HSV: H=60 (verde puro), pero puede variar
        self.lower_green = np.array([40, 50, 50])   # Límite inferior
        self.upper_green = np.array([80, 255, 255])  # Límite superior
        
    def analyze(self, image: np.ndarray) -> Dict:
        """
        Analiza una imagen y trackea el color verde.
        
        Args:
            image: Imagen numpy array de OpenCV (BGR)
            
        Returns:
            Dict con los resultados del tracking:
            {
                'green_detected': bool,
                'green_position': str,  # 'left', 'right', 'center', 'none'
                'green_center': tuple,  # (x, y) del centroide, o None
                'green_area': float,    # Área del objeto verde detectado
            }
        """
        if image is None:
            return self._empty_analysis()
            
        self.last_image = image.copy()
        
        # Convertir BGR a HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Crear máscara para el color verde
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # Aplicar operaciones morfológicas para limpiar la máscara
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return {
                'green_detected': False,
                'green_position': 'none',
                'green_center': None,
                'green_area': 0.0,
            }
        
        # Encontrar el contorno más grande (objeto verde principal)
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        # Calcular centroide
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            center = (cx, cy)
        else:
            center = None
        
        # Determinar posición relativa (left, center, right)
        if center:
            height, width = image.shape[:2]
            if cx < width // 3:
                position = 'left'
            elif cx > 2 * width // 3:
                position = 'right'
            else:
                position = 'center'
        else:
            position = 'none'
        
        return {
            'green_detected': True,
            'green_position': position,
            'green_center': center,
            'green_area': float(area),
        }
    
    def _empty_analysis(self) -> Dict:
        """Retorna análisis vacío cuando no hay imagen"""
        return {
            'green_detected': False,
            'green_position': 'none',
            'green_center': None,
            'green_area': 0.0,
        }
    
    def set_green_range(self, lower: np.ndarray, upper: np.ndarray):
        """
        Ajusta el rango de color verde para tracking.
        
        Args:
            lower: Array numpy con valores HSV inferiores [H, S, V]
            upper: Array numpy con valores HSV superiores [H, S, V]
        """
        self.lower_green = lower
        self.upper_green = upper
    
    def visualize_tracking(self, image: np.ndarray, analysis: Dict) -> np.ndarray:
        """
        Dibuja visualizaciones del tracking sobre la imagen.
        Útil para debugging.
        
        Args:
            image: Imagen original
            analysis: Resultados del análisis
            
        Returns:
            Imagen con visualizaciones dibujadas
        """
        if image is None:
            return image
        
        vis_image = image.copy()
        
        if analysis.get('green_detected', False):
            center = analysis.get('green_center')
            position = analysis.get('green_position', 'none')
            area = analysis.get('green_area', 0.0)
            
            if center:
                # Dibujar círculo en el centroide
                cv2.circle(vis_image, center, 10, (0, 255, 0), -1)
                cv2.circle(vis_image, center, 20, (0, 255, 0), 2)
                
                # Mostrar información
                cv2.putText(vis_image, f"Green: {position}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(vis_image, f"Area: {area:.0f}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return vis_image
