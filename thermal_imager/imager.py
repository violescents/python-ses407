# import helper modules
import os
import time
import csv
import logging
from datetime import datetime

#import processing modules
import numpy as np
import matplotlib.pyplot as plt
import serial 
import serial.tools.list_ports

#logging config --> error handling
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

#itsyBitsy USB\VID_239A&PID_802B&MI_00

# helper fxn: creates heatmap figure based on raw data array, adds avg temp overlay, preview
def generateHeatMap(raw, avg_temp, path_name, preview_seconds):
    fig, ax = plt.subplots(figsize=(8,6))

    im = ax.imshow(raw, interpolation='bicubic', cmap='magma')
    fig.colorbar(im, ax=ax, label='Temperature (°C)')
    ax.set_title("MLX90640 Thermal Image")
    ax.axis("off")

    overlay_text = f"Avg Temp: {avg_temp:.2f} °C"
    ax.text(0.02, 0.98, overlay_text, transform=ax.transAxes, fontsize=12, color="white", verticalalignment="top", bbox=dict(facecolor="black", alpha=0.6, pad=4))
    plt.show(block = False)
    plt.pause(preview_seconds)
    fig.savefig(path_name, bbox_inches="tight", dpi=300)
    plt.close(fig)

#main class for handling serial connection and data processing
class masterController:
    def __init__(
            self,
            baud_rate=115200,
            timeout=5,
            output_folder="thermal_captures",
            images_per_set=15,
            total_sets=3,
            image_delay=1.0):
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.images_per_set = images_per_set
        self.total_sets = total_sets
        self.image_delay = image_delay

# everytime script runs folder gets created with timestamp of script run
        run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_stamp = run_stamp
        self.output_folder = os.path.join(output_folder, f"run_{run_stamp}")
        os.makedirs(self.output_folder, exist_ok=True)

#metadata created for each image captured, can be taken out if deemed unnecessary
        self.metadata_csv = os.path.join(self.output_folder, "capture_metadata.csv")
        self._init_metadata_csv()

        self.current_set = 1 #1 set = 15 images
        self.counter = 1 #image counter
        
        self.port = None
        self.serial_connection = None
        self.is_connected = False

#metadata csv creation functions:
    def _init_metadata_csv(self):
        with open(self.metadata_csv, "w", newline="")as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "run_stamp",
                "set_number",
                "image_in_set",
                "global_image_number",
                "avg_temp_C",
                "filename"
            ])

    def _append_metadata_row(self, set_number, image_in_set, global_image_number, avg_temp, filename):
        with open(self.metadata_csv, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                self.run_stamp,
                set_number,
                image_in_set,
                global_image_number,
                f"{avg_temp:.2f}",
                filename
            ])


#finds/stores comport itsybitsy plugged into, (1st w/hardware nd validated with handshake)
    def findPort(self, vid=0x239A, pid=0x802B):
        ports = serial.tools.list_ports.comports()
        potential_ports = []

        for port in ports:
            if port.vid == vid and port.pid == pid:
                potential_ports.append(port.device)
                logging.info("VID/PID match found on %s", port.device)

        if not potential_ports:
            logging.error("No device found with VID=0x%04X PID=0x%04X", vid, pid)
            return None

        self.port = potential_ports[0]
        logging.info("Selected port: %s", self.port)
        return self.port
    
    #est serial connection
    def handshake(self):
        if self.port is None:
            logging.error("no port")
            return False
        try:
            self.serial_connection = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)

            time.sleep(2)
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            self.serial_connection.write(b"ping\n")
            self.serial_connection.flush()

            response = self.serial_connection.readline().decode("utf-8", errors="replace").strip()

            if response == "pong":
                self.is_connected = True
                logging.info("handshake established on %s", self.port)
                print(f"itsyBitsy connected on {self.port}")
                return True
            
            logging.warning("handshake failed on %s, got: %s", self.port, response)
            self.serial_connection.close()
            self.serial_connection = None
            self.is_connected=False
            return False
        except serial.SerialException as e:
            logging.exception("couldnt connect to %s: %s", self.port, e)
            self.is_connected = False
            return False
        
    #exit serial for cleanup
    def serialDisconnect(self):
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
        except serial.SerialException:
            pass
        finally: 
            self.serial_connection = None
            self.is_connected = False
            logging.info("serial connection closed")

#handles user terminal input to send command to itsybitsy
    def sendCMD(self, cmd):
        if self.serial_connection is None or not self.is_connected:
            raise RuntimeError("serial unreachable")
        try:
            command = cmd.strip() + "\n"
            self.serial_connection.write(command.encode("utf-8"))
            self.serial_connection.flush()
            logging.info("sent command: %s", cmd)
            return True
        except serial.SerialException as e:
            logging.exception("failed to send command '%s': %s", cmd, e)
            self.is_connected = False
            return False
        #creates raw data array from IR camera output
    def rawFrameRead(self):
        if self.serial_connection is None or not self.is_connected:
            raise RuntimeError("serial unreachable")
        
        try:
            data = []
            rows =24
            cols = 32

            for _ in range(rows):
                line = self.serial_connection.readline().decode("utf-8", errors = "replace").strip()
                if not line:
                    raise ValueError("incomplete frame: empty line recieved")
                
                row_values = [float(v) for v in line.split(",") if v.strip()]
                if len(row_values) != cols:
                    raise ValueError(f"expected {cols} values, got {len(row_values)}")
                data.extend(row_values)
            if len(data) != 768:
                raise ValueError(f"Expected {rows * cols} values, got {len(data)}")
            
            return np.array(data, dtype=np.float32).reshape((rows, cols))
        
        except (serial.SerialException, ValueError) as e:
            logging.error("failed to read frame: %s", e)
            return None
        
    #image capture command sent
    def capture(self):
        try:
            sent = self.sendCMD("snap")
            if not sent:
                return None
            time.sleep(1)
            frame = self.rawFrameRead()
            if frame is None:
                logging.error("No frame recieved")
            return frame
        except serial.SerialException as e:
            logging.exception("Image cap failed: %s", e)
            return None
    
    #sends snap command (x images per set) to preform captures nd save capture, metadata nd counter + set variables update
    def capture_Sequence(self, delay=None):
        if delay is None:
            delay = self.image_delay
        if self.current_set > self.total_sets:
            print("all sets captured")
            return
        set_folder = os.path.join(self.output_folder, f"capture_set{self.current_set:02d}")
        os.makedirs(set_folder, exist_ok=True)

        print(f"starting set {self.current_set}/{self.total_sets}")

        for i in range(self.images_per_set):
            frame = self.capture()
            if frame is None:
                logging.error("stopping set %d due to capture failure", self.current_set)
                return
            avg_temp = float(np.mean(frame))
            image_num_in_set = i + 1

            filename = f"{self.counter:02d}_avg_{avg_temp:.2f}C.png"
            save_path = os.path.join(set_folder, filename)

            generateHeatMap(frame, avg_temp, save_path, preview_seconds = 0.1)

            self._append_metadata_row(set_number=self.current_set, image_in_set=image_num_in_set, global_image_number=self.counter, avg_temp=avg_temp, filename=filename)

            print(f"Image {self.counter:02d}   "
                  f"{image_num_in_set}/{self.images_per_set} captured   "
                  f"avg temp: {avg_temp:.2f} °C")
            self.counter += 1
            time.sleep(delay)

        print(f"set {self.current_set} complete")
        self.current_set +=1
    
    #cleanup function (sends shutter close signal, exits serial) --> maybe instead of shutter close signal can run a check to ensure shutter closed then if yes exit if not close nd then exit
    def cleanup(self):
        try:
            if self.is_connected:
                self.sendCMD("close")
                time.sleep(0.5)
        except Exception as e:
            logging.warning("cleanup close command failed: %s", e)
        finally:
            self.serialDisconnect()

#command menu printed in terminal for ease of user use
def show_Menu():
    print("\n=== IR Imager Control Menu ===")
    print("open--> open shutter")
    print("close --> close shutter")
    print("snap  --> capture one full set of images")
    print("exit  --> close shutter nd quit")
    print("=========================================\n")


def main():
    controller = masterController(
        baud_rate=115200,
        timeout=5,
        images_per_set=15,
        total_sets=3,
        image_delay=1.0
    )

    controller.findPort()
    if controller.port is None:
        return
    if not controller.handshake():
        return
    
    show_Menu()
# user input handling loop 
    try: 
        while True:
            userCMD = input("imager> ").strip().lower()
            if userCMD == "open":
                if controller.sendCMD("open"):
                    print("shutter open !")
                continue
            elif userCMD == "close":
                if controller.sendCMD("close"):
                    print("shutter closed !")
                continue
            elif userCMD == "snap":
                controller.capture_Sequence()
                continue
            elif userCMD == "exit":
                print("exiting...")
                break
            else: 
                print("unknown command, try again")
    except KeyboardInterrupt:
        print("\nkeyboard interrupt recieved. exiting...")

    finally:
        controller.cleanup()

#makes program main() auto-run only if this file is called directly not if imported, unnecessary but good practice (i believe)
if __name__=="__main__":
    main()