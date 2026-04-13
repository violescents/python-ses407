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

#logging config
logging.basicConfig(
    level=logging.info,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#pep8 naming convention
#itsyBitsy USB\VID_239A&PID_802B&MI_00

def generateHeatMap(raw, avg_temp, path_name, preview_seconds):
    fig, ax = plt.subplot(figsize=(8,6))

    im = ax.imshow(raw, interpolation='bicubic', cmap='magma')
    fig.colorbar(im, ax=ax, label='Temperature (°C)')
    ax.set_title("MLX90640 Thermal Image")
    ax.axis("off")

    overlay_text = f"Avg Temp: {avg_temp:.2f} °C"
    ax.text(0.02, 0.98, overlay_text, transform=ax.transAxes, fontsize=12, color="white", verticalalignment="top", bbox=dict(facecolor="black", alpha=0.6, pad =4))
    plt.show(block = False)
    plt.pause(preview_seconds)
    fig.savefig(path_name, bbox_inches="tight", dpi=300)
    plt.close(fig)

class masterController:
    def __init__(
            self,
            baud_rate=115200,
            timeout=5,
            output_folder="thermal_captures",
            images_per_set=15,
            total_sets=3,
            delay_between_images=1.0):
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.images_per_set = images_per_set
        self.total_sets = total_sets
        self.delay_between_images = delay_between_images

        run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_stamp = run_stamp
        self.output_folder = os.path.join(output_folder, f"run_{run_stamp}")
        os.makedirs(self.output_folder, exist_ok=True)

        self.metadata_csv = os.path.join(self.output_folder, "capture_metadat.csv")
        self._init_metadata_csv()

        self.current_set = 1
        self.counter = 1
        
        self.port = None
        self.serial_connection = None
        self.is_connected = False

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

    def findPort(self, vid=0x239A, pid=0x802B): 
        #laterproblem
        return None
    
    def connection(self):
        if self.port is None:
            logging.error("no port, run findPort first.")
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
            
            logging.warning("Handshake failed on %s, response was: %s", self.port, response)
            self.serial_connection.close()
            self.serial_connection = None
            self.is_connected=False
            return False
        except serial.SerialException as e:
            logging.exception("couldnt connect to %s: %s", self.port, e)
            self.is_connected = False
            return False
        
    def disconnect(self):
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
        except serial.SerialException:
            pass
        finally: 
            self.serial_connection = None
            self.is_connected = False
            logging.info("serial connection closed")

    def sendCommand(self, cmd):
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
        
    def rawFrameRead(self):
        if self.serial_connection is None or not self.is_connected:
            raise RuntimeError("Serial unreachable")
        
        try:
            data = []
            expected_rows =24
            expected_cols = 32

            for _ in range(expected_rows):
                line = self.serial_connection.readline().decode("utf-8", errors = "replace").strip()
                if not line:
                    raise ValueError("incomplete frame: empty line recieved")
                
                row_values = [float(v) for v in line.split(",") if v.strip()]
                if len(row_values) != expected_cols:
                    raise ValueError(f"Expected {expected_cols} values, got {len(row_values)}")
                data.extend(row_values)
            if len(data) != expected_rows * expected_cols:
                raise ValueError(f"Expected {expected_rows * expected_cols} values, got {len(data)}")
            
            return np.array(data, dtype=np.float32).reshape((expected_rows, expected_cols))
        
        except (serial.SerialException, ValueError) as e:
            logging.error("failed to read frame: %s", e)
            return None
        
    def capture(self):
        try:
            sent = self.sendCommand("snap")
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
    
    def captureSequence(self, delay=None):
        if delay is None:
            delay = self.delay_between_images
        if self.current_set > self.total_sets:
            print("all sets captured")
            return
        set_folder = os.path.join(self.output_folder, f"capture_set{self.current_set:02d}")
        os.makedirs(set_folder, exist_ok=True)

        print(f"starting set {self.current_set}/{self.total_sets}")

        for i in range(self.images_per_set):
            frame = self.imgCapture()
            if frame is None:
                logging.error("stopping set %d due to capture failure", self.current_set)
                return
            avg_temp = float(np.mean(frame))
            image_num_in_set = i + 1

            filename = f"{self.counter:02d}_avg_{avg_temp:.2f}C.png"
            save_path = os.path.join(set_folder, filename)

            generateHeatMap(frame, avg_temp, save_path)

            self._append_metadata_row(set_number=self.current_set, image_in_set=image_num_in_set, global_image_number=self.counter, avg_temp=avg_temp, filename=filename)

            print(f"Image {self.counter:02d}   "
                  f"{image_num_in_set}/{self.images_per_set} captured   "
                  f"avg temp: {avg_temp:.2f} °C")
            self.counter += 1
            time.sleep(delay)

        print(f"set {self.current_set} complete")
        self.current_set +=1
    
    def cleanup(self):
        try:
            if self.is_connected:
                self.sendCommand("close")
                time.sleep(0.5)
        except Exception as e:
            logging.warning("cleanup close command failed: %s", e)
        finally:
            self.disconnect()
    