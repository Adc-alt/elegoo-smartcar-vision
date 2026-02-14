import re
import json
from .connection import connection
from .robotCommands import robotCommands


class myCar:
    def __init__(self, ip="192.168.4.1", port=100):
        self.connection = connection(ip, port)
        # self.camera = Camera(ip)  # Camera commented out
        self.commands = robotCommands()
        # MPU calibration offsets
        self.mpu_offset = [0.007, 0.022, -0.085, 0.012, -0.011, -0.05]  # Adjusted az offset

    def connect(self):
        """Establish connection with the car and wait for initial heartbeat"""
        if not self.connection.connect():
            return False
        data = self.connection.receive()
        return data is not None

    def communicate(self, command_json):
        """Send a command to the car and process its response"""
        # Get the command number from the JSON
        try:
            command = json.loads(command_json)
            is_motion_command = command.get('N') == '6'
        except:
            is_motion_command = False
            
        if not self.connection.send(command_json):
            return None
        
        while True:
            response = self.connection.receive()
            if response is None:
                continue
            
            # Keep receiving until we get a response with '_'
            if '_' not in response:
                continue
            
            # Extract response data using the same regex as the original script
            match = re.search('_(.*)}', response)
            if not match:
                continue
                
            response_data = match.group(1)
            
            # For motion command, process MPU data
            if is_motion_command and ',' in response_data:
                res = response_data.split(",")
                res = [int(x)/16384 for x in res]  # convert to units of g
                res = [round(res[i] - self.mpu_offset[i], 4) for i in range(6)]  # apply calibration offsets
                res[2] = res[2]-1
                return res
            
            # For non-motion commands
            if response_data == 'ok' or response_data == 'true':
                return 1
            elif response_data == 'false':
                return 0
            else:
                try:
                    return int(response_data)
                except ValueError:
                    return response_data
                except Exception:
                    return None

    def move(self, direction, speed):
        """Move the car in specified direction at given speed"""
        command = self.commands.move(direction, speed)
        return self.communicate(command)

    def stop(self):
        """Stop the car"""
        command = self.commands.stop()
        return self.communicate(command)

    def rotate(self, angle):
        """Rotate the car by specified angle"""
        command = self.commands.rotate(angle)
        return self.communicate(command)

    def servo_rotate(self, servo_type, angle):
        """Rotate a servo motor to a specific angle
        Args:
            servo_type (int): 1 for left/right servo, 2 for up/down servo
            angle (int): Rotation angle (0-180 degrees)
        """
        command = self.commands.servo_rotate(servo_type, angle)
        return self.communicate(command)

    def measure_distance(self):
        """
        Measure the distance to the nearest obstacle.

        Returns:
            float: Distance in centimeters, or None if measurement fails.
        """
        command = self.commands.measure_distance()
        result = self.communicate(command)
        if isinstance(result, (int, float)):
            return int(result)
        return 0

    def check_obstacle(self):
        """Check for obstacles"""
        command = self.commands.check_obstacle()
        return self.communicate(command)

    def measure_motion(self):
        """Measure motion using accelerometer"""
        command = self.commands.measure_motion()
        return self.communicate(command)

    def check_ground(self):
        """Check if car is on ground"""
        command = self.commands.check_ground()
        return self.communicate(command)

    def disconnect(self):
        """Close the connection with the car"""
        self.connection.close()