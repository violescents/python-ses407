import serial
import time
import numpy as np
import matplotlib.pyplot as plt
import os
import logging


logging.basicConfig(level=logging.Info)

PORT = "COM4"
BAUD_RATE = 115200
print("Starting IR data reader...")
ser = serial.Serial(PORT, BAUD_RATE,timeout=1)
print("great success, we have connection!!")

output_folder = "thermal_captures"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

counter = 1  # Initialize

def increment_counter():
    global counter
    counter += 1
    print(counter)

#reads the data from the IR sensor and returns it as a numpy array
def read_IR_data():
   

        #send snap command to itsybitsy
        ser.write(b'snap\n')
        time.sleep(1)
        data = []
        for i in range(24):  # Loop 24 times for 24 rows
            line = ser.readline().decode('utf-8').strip()
            if line:  # Only process non-empty lines
                values = line.split(',')
                # Convert each value to float and add to data list
                data.extend([float(v) for v in values if v])
        
        # Convert the collected data list into a 2D numpy array with 24 rows
        # The reshape automatically calculates columns based on total data points
        data_array = np.array(data).reshape(24, -1)
        
        # Print a label to the terminal
        print("Camera data:")
        
        # # Display the 2D numpy array to the terminal so you can see the camera output
        # print(data_array)
        
        
        
        # Return the numpy array so it can be used elsewhere in the program
        return data_array
        


def generate_thermal_image(raw_data):

    data_array = np.array(raw_data).reshape((24, 32))

    plt.figure(figsize=(8, 6))
    img = plt.imshow(data_array, interpolation='bicubic', cmap='magma')

    plt.colorbar(img, label='Temperature (°C)')

    plt.title("MLX90640 Thermal Capture")
    plt.axis('off') # Hide the pixel coordinate axes


    filename = f"{counter:03d}_thermal_capture.png"  # e.g. 001_thermal_capture.png
    path = os.path.join(output_folder, filename)
    plt.savefig(path)
    #plt.savefig(str(counter) + 'thermal_capture.png')
    #ply.savefig()
    plt.close() # Close the figure to free up memory


    increment_counter()  # Increment the counter after saving the image


# Call the function to execute it
for counter in range(1, 16):  # Capture and save 15 thermal images
    data_array = read_IR_data()
    generate_thermal_image(data_array)
    data_array = np.zeros((24, 32))  # same shape as your frame
   # Time to wait between captures in seconds
   # time.sleep(1)



# Close the serial connection to free up the COM port
ser.close()



    
