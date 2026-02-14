import time

# State definitions
class States:
    FORWARD = 'Forward'
    SCANNING = 'Scanning'
    TURNING_LEFT = 'Turning Left'
    TURNING_RIGHT = 'Turning Right'
    BACKWARD = 'Backward'
    STOP = 'Stop'

class obstacleAvoidance:
    def __init__(self, *, car=None):        
        if car is None:
            raise ValueError("A myCar instance is required")
        self.car = car
        self.setState = States.FORWARD  # Initial state
        self.leftDistance = 0
        self.rightDistance = 0
        
        # Map states to methods
        self.state_handlers = {
            States.FORWARD: self.forward,
            States.SCANNING: self.scanning,
            States.TURNING_LEFT: self.turn_left,
            States.TURNING_RIGHT: self.turn_right,
            States.BACKWARD: self.backward,
            States.STOP: self.stop
        }
        
    def run(self):
        """Main method that handles states"""
        handler = self.state_handlers.get(self.setState)
        if handler:
            handler()
        else:
            print(f"⚠️  Unknown state: {self.setState}")
            self.setState = States.STOP
        
    def forward(self):
        """State: Forward movement"""
        print("🚗  Moving forward")
        self.car.rotate('90')
        self.car.move('3', '100')
        
        # Check for obstacles
        if self.car.check_obstacle():
            print("🚨  Obstacle detected - Starting scan")
            self.car.stop()  # Stop the car when obstacle is detected
            self.setState = States.SCANNING
    
    def scanning(self):
        """State: Environment scanning"""
        print("🔍  Scanning environment...")
        self.car.stop()  # Ensure car is stopped during scanning
        
        # Measure left distance
        self.car.rotate('30')
        time.sleep(0.2)  # Wait for servo to position
        self.leftDistance = self.car.measure_distance()
        print(f"Left distance: {self.leftDistance} cm")
        
        # Measure right distance
        self.car.rotate('150')
        time.sleep(0.2)  # Wait for servo to position
        self.rightDistance = self.car.measure_distance()
        print(f"Right distance: {self.rightDistance} cm")
        
        # Return to center position
        self.car.rotate('90')
        time.sleep(0.1)  # Small pause before decision
        
        # Decide next state
        if self.leftDistance < 10 and self.rightDistance < 10:
            print("⚠️  Not enough space - Going backward")
            self.setState = States.BACKWARD
        elif self.leftDistance > self.rightDistance:
            print("↩️  Turning left")
            self.setState = States.TURNING_RIGHT
        else:
            print("↪️  Turning right")
            self.setState = States.TURNING_LEFT
    
    def turn_left(self):
        """State: Left turn"""
        print("↩️  Executing left turn")
        self.car.move('1', '100')  # 1 = Turn left
        time.sleep(0.4)  # Turn for half second
        self.car.stop()
        self.setState = States.FORWARD
    
    def turn_right(self):
        """State: Right turn"""
        print("↪️  Executing right turn")
        self.car.move('2', '100')  # 2 = Turn right
        time.sleep(0.4)  # Turn for half second
        self.car.stop()
        self.setState = States.FORWARD
    
    def backward(self):
        """State: Backward movement"""
        print("⬅️  Going backward")
        self.car.move('4', '100')  # 4 = backward
        time.sleep(0.8)  # Back up for 1 second
        self.car.stop()
        self.setState = States.SCANNING  # Scan again after backing up
    
    def stop(self):
        """State: Stop"""
        print("🛑  Stopping vehicle")
        self.car.stop()