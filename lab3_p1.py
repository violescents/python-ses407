import serial
import time
import matplotlib.pyplot as plt
from drawnow import*

voltage = []
plt.ion()

def create_plot():
    plt.title('Voltage over Time')
    plt.grid(True)
    plt.ylabel('Voltage (V)')
    plt.xlabel('counts')
    plt.plot(voltage, 'o-', label='Volts')
    plt.legend(loc='upper left')

dataRaw = serial.Serial('COM3', 9600)
while True:
    while dataRaw.in_waiting == 0:
        pass
    data = dataRaw.readline().decode('utf-8').strip('\r\n')
    volts = ((5 - 0) / (1023 - 0)) * int(data)
    print(volts)
    voltage.append(volts)
    drawnow(create_plot)
    plt.pause(0.0001)
    print(data)
    
