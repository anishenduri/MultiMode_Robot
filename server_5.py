#!/usr/bin/env python3
import socket
import time
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_B, OUTPUT_C, OUTPUT_A, SpeedPercent
from ev3dev2.sensor.lego import ColorSensor, TouchSensor, GyroSensor, UltrasonicSensor

HOST = ''
PORT = 9999

# Motors
motor_left = LargeMotor(OUTPUT_B)
motor_right = LargeMotor(OUTPUT_C)
medium_motor = MediumMotor(OUTPUT_A)

# Sensors
color_sensor = ColorSensor('in3')
touch_sensor = TouchSensor('in1')
gyro_sensor = GyroSensor('in2')
ultra_sensor = UltrasonicSensor('in4')

# Command history
command_history = []

COLOR_NAMES = {
    0: "No color",
    1: "Black",
    2: "Blue",
    3: "Green",
    4: "Yellow",
    5: "Red",
    6: "White",
    7: "Brown"
}

def execute_command(cmd):
    cmd = cmd.strip().lower()

    # Movement
    if cmd == "forward":
        motor_left.on(SpeedPercent(50))
        motor_right.on(SpeedPercent(50))
        time.sleep(2)
        motor_left.off()
        motor_right.off()
        return "Moved forward"

    elif cmd == "backward":
        motor_left.on(SpeedPercent(-50))
        motor_right.on(SpeedPercent(-50))
        time.sleep(2)
        motor_left.off()
        motor_right.off()
        return "Moved backward"

    elif cmd == "left":
        motor_left.on(SpeedPercent(-50))
        motor_right.on(SpeedPercent(50))
        time.sleep(1)
        motor_left.off()
        motor_right.off()
        return "Turned left"

    elif cmd == "right":
        motor_left.on(SpeedPercent(50))
        motor_right.on(SpeedPercent(-50))
        time.sleep(1)
        motor_left.off()
        motor_right.off()
        return "Turned right"

    # Claw
    elif cmd == "open":
        medium_motor.on(SpeedPercent(50))
        time.sleep(2.5)
        medium_motor.off()
        return "Claw opened"

    elif cmd == "close":
        medium_motor.on(SpeedPercent(-50))
        time.sleep(2.5)
        medium_motor.off()
        return "Claw closed"

    # Stop all motors
    elif cmd == "stop":
        try:
            motor_left.off(brake=False)
            motor_right.off(brake=False)
            medium_motor.off(brake=False)
        except:
            pass
        return "All motors stopped"

    # Sensors
    elif cmd == "distance":
        dist_cm = ultra_sensor.distance_centimeters
        return "Distance is " + str(int(dist_cm)) + " centimeters"

    elif cmd == "color":
        col_code = color_sensor.color
        col_name = COLOR_NAMES.get(col_code, "Unknown")
        return "Color detected: " + col_name

    elif cmd == "angle":
        ang = gyro_sensor.angle
        return "Angle is " + str(ang) + " degrees"

    elif cmd == "history":
        return "\n".join(command_history) if command_history else "No commands yet."

    elif cmd == "exit":
        return "exit"

    return ""  # No "Unknown command" to avoid TTS issues

# TCP Server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print("EV3 Server running... waiting for connection.")

    conn, addr = s.accept()
    with conn:
        print("Connected by", addr)
        while True:
            data = conn.recv(1024)
            if not data:
                break
            command = data.decode().strip()
            command_history.append(command)
            response = execute_command(command)
            conn.sendall(response.encode())
            if response == "exit":
                print("Shutting down server.")
                break
