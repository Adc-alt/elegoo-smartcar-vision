import socket
import time

CONNECT_WAIT = 1


class connection:
    def __init__(self, ip="192.168.4.1", port=100):
        self.ip = ip
        self.port = port
        self.socket = None

    def connect(self):
        try:
            if self.socket:
                self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            self.socket.settimeout(None)  # Sin timeout: conexión bloqueante
            time.sleep(CONNECT_WAIT)
            return True
        except Exception:
            return False

    def send(self, message):
        if not self.socket:
            return False
        try:
            self.socket.send(message.encode())
            return True
        except Exception:
            return False

    def receive(self):
        if not self.socket:
            return None
        try:
            return self.socket.recv(1024).decode()
        except (socket.timeout, Exception):
            return None

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
