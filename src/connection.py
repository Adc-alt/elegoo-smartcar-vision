import socket
import time

class connection:
    def __init__(self, ip="192.168.4.1", port=100, timeout=30):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.socket = None

    def connect(self):
        try:
            print(f"Intentando conectar a {self.ip}:{self.port}...")
            if self.socket:
                self.socket.close()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Reducir timeout para pruebas
            print(f"Socket creado, conectando...")
            self.socket.connect((self.ip, self.port))
            print(f"Conexión establecida, esperando 1 segundo...")
            time.sleep(1)  # Wait after connection
            return True
        except socket.timeout:
            print(f"Timeout: El servidor no respondió en {self.timeout} segundos")
            print(f"Verifica que el ESP32 esté encendido y en la IP {self.ip}")
            return False
        except socket.gaierror as e:
            print(f"Error de DNS/resolución: {str(e)}")
            print(f"No se pudo resolver la IP {self.ip}")
            return False
        except ConnectionRefusedError:
            print(f"Conexión rechazada: El puerto {self.port} puede estar cerrado o incorrecto")
            return False
        except Exception as e:
            print(f"Error al conectar: {str(e)}")
            print(f"Tipo de error: {type(e).__name__}")
            return False

    def send(self, message):
        if not self.socket:
            return False
        try:
            self.socket.send(message.encode())
            return True
        except Exception as e:
            return False

    def receive(self):
        if not self.socket:
            return None
        try:
            data = self.socket.recv(1024).decode()
            return data
        except socket.timeout:
            return None
        except Exception as e:
            return None

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                pass
            finally:
                self.socket = None