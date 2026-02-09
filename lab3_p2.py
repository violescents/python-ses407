import serial
ser = serial.Serial('COM3', 9600)

while True:
    command = input("Enter input command: ")
    command = command + "\r"

    ser.write(command.encode())