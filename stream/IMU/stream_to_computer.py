import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import csv
import numpy as np
import os

SAMPLES_PER_PACKAGE = 8
data_path = r"C:\Users\lhauptmann\Code\WristPPG2\data"

class BluetoothIMUReader:
    def __init__(self, port, baud_rate, save_file="data.csv", save_interval=1000):
        self.port = port
        self.baud_rate = baud_rate
        self.save_file = save_file
        self.save_interval = save_interval
        self.ser = None  # Serial object will be initialized in the `init_connection()` method
        self.received_data = []
        self.saving_time = 0
        self.init_connection()
        self.packages = [-1]
        self.data_losses = []
        self.current_package = -1

    def init_connection(self):
        """Initialize the Bluetooth serial connection."""
        self.ser = serial.Serial(self.port, self.baud_rate)
        time.sleep(2)  # Allow some time for the connection to establish
        print(f"Connected to {self.port} at {self.baud_rate} baud rate")


    def read_data(self):
        if self.ser.in_waiting:
            data = self.ser.readline().decode('utf-8').strip()
            if data.startswith("Package count: "):
                package_count = int(data[len("Package count: "):])
                return package_count
            if data == "" or len(data.split("\t")) != 7:
                if data != "":
                    print(data)
                return None
            data_splits = data.split("\t")
            acc_x = int(data_splits[0])
            acc_y = int(data_splits[1])
            acc_z = int(data_splits[2])
            gyro_x = int(data_splits[3])
            gyro_y = int(data_splits[4])
            gyro_z = int(data_splits[5])
            timestamp = float(data_splits[6])
            timestamp_computer = int(time.time() * 1000)
            return acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer
        return None

    def process_acc(self, acc):
        # Assuming the maximum value is 2g (units: mg)
        acc_lsb_div = 2**14
        return acc / acc_lsb_div * 1000

    def process_gyro(self, gyro):
        # Assuming the maximum value is 250 deg/s (units: deg/s)
        gyro_lsb_div = 64
        return gyro / gyro_lsb_div

    def save_data(self):
        if len(self.received_data) > 0:
            with open(self.save_file, mode='a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.received_data[0].keys())
                if file.tell() == 0:
                    writer.writeheader()
                for data in self.received_data:
                    writer.writerow(data)
            self.received_data = []  # Clear the buffer after saving

            

    def update(self):
        try:
            data = self.read_data()
        except Exception as e:
            print(f"Error reading data: {e}")
            return
        
        if isinstance(data, int):
            package = data
            print(f"Package count: {package}")
            if package != self.packages[-1]:
                self.packages.append(package)
            if self.current_package != package:
                self.current_package = package
        
        elif data is not None:
            acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer = data
            acc_x = self.process_acc(acc_x)
            acc_y = self.process_acc(acc_y)
            acc_z = self.process_acc(acc_z)
            gyro_x = self.process_gyro(gyro_x)
            gyro_y = self.process_gyro(gyro_y)
            gyro_z = self.process_gyro(gyro_z)

            data_dict = {
                "acc_x": acc_x, "acc_y": acc_y, "acc_z": acc_z,
                "gyro_x": gyro_x, "gyro_y": gyro_y, "gyro_z": gyro_z,
                "timestamp": timestamp, "timestamp_computer": timestamp_computer, "package": self.packages[-1]
            }
            self.received_data.append(data_dict)
        
        # Save the data periodically based on the save interval
        current_time = time.time() * 1000
        if current_time - self.saving_time >= self.save_interval and len(self.received_data) > 0:
            self.data_losses.append(self.get_data_loss_package())
            
            self.save_data()
            self.saving_time = current_time
            
    def get_package_loss(self):
        package_count = np.array(self.packages[1:])
        package_count = np.unique(package_count)
        package_count.sort()
        package_diff = np.diff(package_count)
        package_loss = package_diff[package_diff > 1]
        #print(package_loss)
        package_loss = np.sum(package_loss - 1)
        return package_loss / (len(package_count) + package_loss)
        
    def get_data_loss_package(self):
        # explude first and last package
        sample_packages = np.array([data["package"] for data in self.received_data if data["package"] != self.received_data[0]["package"]])
        if len(sample_packages) == 0:
            return np.nan
        unique_packages = np.unique(sample_packages)
        data_loss = (len(unique_packages)*SAMPLES_PER_PACKAGE - len(sample_packages)) / (len(unique_packages)*SAMPLES_PER_PACKAGE)
        return data_loss

    def get_data_loss(self):
        self.data_losses = np.array(self.data_losses)
        self.data_losses = self.data_losses[~np.isnan(self.data_losses)]
        return np.nanmean(self.data_losses)

    def run(self):
        try:
            while True:
                self.update()
        except KeyboardInterrupt:
            print("Program stopped")
        finally:
            print(f"Package loss: {self.get_package_loss()}")
            print(f"Data loss: {self.get_data_loss()}")
            print(f"Data saved to {self.save_file}")
            self.ser.close()  # Close the serial port

# Example usage
if __name__ == "__main__":
    # Set the correct port (e.g., COM3 on Windows or /dev/rfcomm0 on Linux)
    bluetooth_port = 'COM6'  # Change this to the actual port
    baud_rate = 115200  # The same baud rate as in Arduino code

    # Initialize the Bluetooth IMU reader
    filename = "imu_", time.strftime("%m_%d-%H_%M") + ".csv"
    imu_reader = BluetoothIMUReader(bluetooth_port, baud_rate, save_file=os.path.join(data_path, filename))

    # Run the reader (press Ctrl+C to stop)
    imu_reader.run()
