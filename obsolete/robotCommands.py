# import json

# class robotCommands:
#     def __init__(self):
#         self.cmd_no = 0

#     def _create_base_message(self):
#         self.cmd_no += 1
#         return {"H": str(self.cmd_no)}

#     def move(self, direction, speed):
#         # Accept both numeric codes and text
#         direction_map = {
#             'forward': '3',
#             'backward': '4',
#             'left': '1',
#             'right': '2',
#             '1': '1',  # Direct numeric codes
#             '2': '2',
#             '3': '3',
#             '4': '4'
#         }

#         msg = self._create_base_message()
#         msg['N'] = str(3)
#         msg['D1'] = direction_map[direction]
#         msg['D2'] = str(speed)
#         return json.dumps(msg)

#     def stop(self):
#         msg = self._create_base_message()
#         msg['N'] = str(1)
#         msg['D1'] = str(0)
#         msg['D2'] = str(0)
#         msg['D3'] = str(1)
#         return json.dumps(msg)

#     def rotate(self, angle):
#         msg = self._create_base_message()
#         msg['N'] = str(5)
#         msg['D1'] = str(1)
#         msg['D2'] = str(angle)
#         return json.dumps(msg)

#     def servo_rotate(self, servo_type, angle):
#         """Rotate a servo motor to a specific angle
#         Args:
#             servo_type (int): 1 for left/right servo, 2 for up/down servo
#             angle (int): Rotation angle (0-180 degrees)
#         """
#         msg = self._create_base_message()
#         msg['N'] = str(5)
#         msg['D1'] = str(servo_type)  # 1 = left/right servo, 2 = up/down servo
#         msg['D2'] = str(angle)       # 0-180 degrees
#         return json.dumps(msg)

#     def measure_distance(self):
#         msg = self._create_base_message()
#         msg['N'] = str(21)
#         msg['D1'] = str(2)  # Measure distance directly
#         return json.dumps(msg)

#     def check_obstacle(self):
#         msg = self._create_base_message()
#         msg['N'] = str(21)
#         msg['D1'] = str(1)  # Only detect obstacle
#         return json.dumps(msg)

#     def measure_motion(self):
#         """Measure motion using MPU6050
#         Returns accelerometer (ax,ay,az) and gyroscope (gx,gy,gz) data
#         """
#         msg = self._create_base_message()
#         msg['N'] = '6'  # Note: using string '6' to match exactly the original
#         return json.dumps(msg)

#     def check_ground(self):
#         msg = self._create_base_message()
#         msg['N'] = str(23)
#         return json.dumps(msg) 