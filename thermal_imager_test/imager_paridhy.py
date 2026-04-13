import serial
import time
import numpy as np
import matplotlib.pyplot as plt
import os
import logging
import serial.tools.list_ports
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#ItsyBitsy USB\VID_239A&PID_802B&MI_00

"""
def findPort(vid=0x239A, pid=0x802B
             #handshake_msg
             #baudrate 115200
             ):
    
#find arduino port by vendor id(vid) and product id (pid)
    candidate_ports = [
        port.device
        for port in list_ports.comports()
        if (port.vid == vid) and (port.pid == pid)
    ]

    #verify candidate via handshake:
    for port in candidate_ports:
        print(f"Testing port: {port}")
        if handshake_arduino(port, baudrate = baudrate):
            print(f"(handshake verified) port: {port}" )
            return port



# just hardware check:
    
    arduino_ports = [
        port.device
        for port in list_ports.comports()
        if (port.vid == vid) and (port.pid == pid)
    ]

    if not arduino_ports:
        return None
    if len(arduino_ports)>1:
        print(f"Warning: multiple arduionos found on ports {arduino_ports}. Using the first.")
    return arduino_ports[0]
    """



class ThermalCamera:
    def __init__(self, port = "COM4", baud_rate = 115200, output_folder = "thermal_images"):
        self.port = port
        self.baud_rate = baud_rate
        self.output_folder = output_folder
        self.counter = 1
        os.makedirs(self.output_folder, exist_ok = True) #creates output folder if it doesnt already exist

    def read_IR_data(self, ser):
            try: 
                ser.write(b'snap\n') #send snap command to arduino
                time.sleep(1) #wait for arduino to process command and send data back
                data = []
                for i in range(24):
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        values = [float(v) for v in line.split(',') if v]
                        data.extend(values)
                        if len(data) != 768: #24*32
                            raise ValueError("incomplete")
                        return np.array(data).reshape((24,32)) #reshape to 24x32 array
            except (serial.SerialException, ValueError) as e:
                logging.error(f"expected 768 values but got {len(data)}. Data incomplete. Error: {e}")
                return None
            
    def thermal_image_generate(self, raw_data): #generates thermal image from 2d numpy array and saves as image
            plt.figure(figsize=(8,6))
            img = plt.imshow(raw_data, interpolation='bicubic', cmap='magma')
            plt.colorbar(img, label = 'Temperature (°C)')
            plt.title('MLX90640 Thermal Image')
            plt.axis('off')
            filename = f"{self.counter:03d}_thermal_capture.png"
            path = os.path.join(self.output_folder, filename)
            plt.savefig(path)
            plt.close()
            self.counter +=1
    
    def image_capture(self, num_captures = 15, delay=0):
        try: 
            with serial.Serial(self.port, self.baud_rate, timeout=1) as ser:
                for _ in range(num_captures):
                    data_array = self.read_IR_data(ser)
                    if data_array is not None:
                        self.thermal_image_generate(data_array)
                    if delay > 0:
                        time.sleep(delay) #delay between captures
        except serial.SerialException as e:
            logging.error(f"Serial connection error: {e}")

#usage 
imager = ThermalCamera(port="COM4", baud_rate=115200, output_folder="thermal_images")
imager.image_capture(num_captures=15, delay=1) #capture 15 images with 1 second delay between captures



