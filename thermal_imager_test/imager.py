#imager.py (official code)

import numpy as np
import matplotlib.pyplot as plt
import serial
import time
import os
import logging
import serial.tools.list_ports

logging.basicConfig(level=logging.INFO, format ='%(asctime)s - %(levelname)s - %(message)s')

#itsyBitsy USB\VID_239A&PID_802B&MI_00

#naming convention: functions/classes with uppercase next letter
#                   variables with underlines 

# helper fxn: 

def generateHeatMap(raw, path_name):
    plt.figure(figsize = (8,6))
    img = plt.imshow(raw, interpolation='bicubic', cmap = 'magma')
    plt.colorbar(img, label = 'Temperature (°C)')
    plt.title('MLX90640 Thermal Image')
    plt.axis('off')

    plt.show(block = False)
    plt.pause(0.5)

    img.savefig(path_name, bbox_inches = 'tight', dpi = 300)

    plt.close(img)
    

class masterController:
    def __init__(self, baud_rate = 115200, timeout = 5, counter = 1, output_folder = "thermal_captures", set = 1):
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.counter = counter
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok = True)
        self.set = set

        self.port = None
        self.serial_connection = None
        self.is_connected = False
    

    def findPort(self, vid = 0x239A, pid = 0x802B):
        ports = serial.tools.list_ports.comports()
        # --- hardware (pid/vid) check ---

        for port in ports:
            if port.vid == vid and port.pid == pid:
                logging.info(f"port: {port.device}")

        try: 
            test_ser = serial.Serial(port.device, self.baud_rate, timeout = self.timeout)

            time.sleep(2)

            test_ser.reset_input_buffer()
            test_ser.reset_output_buffer()

            # -- handshake -- 
            test_ser.write(b"ping\n")
            response = test_ser.readline().decode("utf-8", errors="replace").strip()

            test_ser.close()

            if response == "pong":
                logging.info(f"shook hands with itsybitsy on {port.device}")
                self.port = port.device
                return port.device
            else:
                logging.warning(f"could not establish handshake on {port.device} : {response}")

        except serial.SerialException as e:
            logging.warning(f"could not open {port.device}: {e}")

        logging.error("no valid device found")
        return None



    def connection(self):
        if self.port is None:
            return False
        try: 
            serial.Serial(
                self.port,
                self.baud_rate,
                timeout = self.timeout
            )

            self.is_connected = True
            time.sleep(2)
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            print(f"ItsyBitsy connected on {self.port}\n ready !")
            return True

        except serial.SerialException as e:
            logging.error(f"arduino could not connect")
            self.serial_connection = None
            self.is_connected = False
            return False


    def sendCommand(self, cmd): 
        if self.serial_connection is None or not self.is_connected:
            raise RuntimeError(f"serial not open/connected")
        
        try: 
            command = cmd.strip() + "\n"
            self.serial_connection.write(command.encode('utf-8'))
            self.serial_connection.flush()
            logging.info(f"sent command: {cmd}")
            return True

        except (serial.SerialException) as e:
            logging.exception(f"cmd wrong {e}")
            self.is_connected = False
            return None
        
    def rawFrameRead(self):
        if self.serial_connection is None or not self.is_connected:
            raise RuntimeError(f"serial not open/connected")
            
        try:    
            data = []

            for _ in range(24):
                line = self.serial_connection.readline().decode('utf-8', errors = 'replace').strip()
                if not line:
                    raise ValueError("incomplete frame")
                
                row_values = [float(v) for v in line.split(',') if v.strip()]
                if len(row_values) != 32:
                    raise ValueError(f"expected 32 values, instead got {len(row_values)}")
                
                data.extend(row_values)

            if len(data) != 768:
                raise ValueError(f"Expected 768 values, got {len(data)}")
            
            return np.array(data, dtype=np.float32).reshape((24, 32))

        except (serial.SerialException, RuntimeError, ValueError) as e:
            logging.error(f"failed: {e}")
            return None
        
        
    def imgCapture(self):
        try: 
            sent = self.sendCommand("snap")
            if not sent:
                return None
            
            time.sleep(1)

            frame = self.rawFrameRead()
            if frame is None:
                logging.error("no frame from arduino")
                return None
            return frame

        except (serial.SerialException) as e:
            logging.exception(f"bruh image capture failed: {e}")
            return None
        
    def captureSequence(self, delay):

        set_folder = os.path.join(self.output_folder, f"capture_set{self.set}")
        os.makedirs(set_folder, exist_ok = True)

        for i in range(15):
            frame = self.imgCapture()
            filename = f"{(i + 1):02d}_thermalCapture.png"
            save_path = os.path.join(set_folder, filename)
            generateHeatMap(frame, save_path)
            counter +=1
            time.sleep(1)
        
        self.set+=1
    
    