import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import csv
import numpy as np
import os
import threading
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from collections import deque

running = True
SAMPLES_PER_PACKAGE = 8
save_path = r"C:\Users\lhauptmann\Code\WristPPG2\data"

""" class DataBuffer:
    def __init__(self):
        self.data = []
        self.is_recording = False

    def add_data(self, data):
        if self.is_recording:
            self.data.append(data)

    def set_recording(self, on):
        #Enable or disable data recording.
        self.is_recording = on

    def plotting_queues(self):
        #Return data for plotting. This assumes that each data point has a similar structure.
        acc_x = [d['acc_x'] for d in self.data]
        acc_y = [d['acc_y'] for d in self.data]
        acc_z = [d['acc_z'] for d in self.data]
        gyro_x = [d['gyro_x'] for d in self.data]
        gyro_y = [d['gyro_y'] for d in self.data]
        gyro_z = [d['gyro_z'] for d in self.data]
        timestamps = [d['timestamp'] for d in self.data]
        
        return acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamps """
        
        
class DataBuffer:
    def __init__(self, n_channels=8, frame_rate=128, plotting_window=5, csv_window=2, fileindex=0):
        
        # timestamp = time.strftime("%Y%m%d-%H%M%S")
        # self.filename = f"..//recordings//ppg_data_{timestamp}"
        self.filename = f'C://Users//lhauptmann//Code//WristPPG2//data//imu_{fileindex:03d}'

        self.plotting_winoow = plotting_window
        self.csv_window = csv_window
        self.frame_rate = frame_rate

        self.buffers = [deque(maxlen=plotting_window*frame_rate) for _ in range(n_channels)]
        self.csv_buffers = [deque(maxlen=csv_window*frame_rate) for _ in range(n_channels)]

        self.recording = True
        self.n_channels = n_channels

    def add_data(self, qidx, val):

            
        self.buffers[qidx].append(val)
        self.csv_buffers[qidx].append(val)

    def dump_to_txt(self):
        # with open(self.filename, mode='a', newline='') as file:
        #     writer = csv.writer(file)
        #     for i in range(self.n_channels):
        #         row = f'{i}' + np.array(self.csv_buffers[i]).astype(str)
        #         writer.writerow(row)
        while True:
            if self.recording:
                f = open(f"{self.filename}.txt", "a")
                for i in range(self.n_channels):
                    f.write(f"{i} ")
                    while self.csv_buffers[i]:
                        f.write(f"{self.csv_buffers[i].popleft()} ")
                    f.write(" \n")
                f.close()
            time.sleep(self.csv_window)

    def set_recording(self, value):
        if value and not self.recording:
            self.start_recording()
        if self.recording and not value:
            self.stop_recording()
        # self.recording = value

    # def start_data_dump(self):
    #     dump_thread = threading.Thread(target=self.data_dump)
    #     dump_thread.daemon = True
    #     dump_thread.start()
    #     return dump_thread

    # def data_dump(self):
    #     while True:
    #         if self.recording:
    #             self.dump_to_txt()
    #         time.sleep(self.csv_window)

    def start_recording(self):
        self.recording = True
        ti = time.time()
        with open(f"{self.filename}.txt", 'a') as f:
            f.write(f'start time: {ti} \n')
        f.close()
        print("[IMU]: recording started")

    def stop_recording(self):
        self.recording = False
        tf = time.time()

        with open(f"{self.filename}.txt", 'a') as f:
            f.write(f'end time: {tf} \n')
        f.close()

        print("[IMU]: recording stopped")
        print(f"[IMU]: data saved to {self.filename}.txt")

    def plotting_queues(self):
        return [np.array(self.buffers[i]) for i in range(self.n_channels)]


class BluetoothIMUReader:
    def __init__(self, port, baud_rate, save_file="data.csv", file_index=0):
        self.port = port
        self.baud_rate = baud_rate
        self.save_file = save_file
        self.ser = None  # Serial object will be initialized in the `init_connection()` method
        self.received_data = []
        self.packages = [-1]
        self.data_losses = []
        self.current_package = -1
        self.running = False
        self.file_index = file_index

        # Initialize the data buffer
        self.data_buffer = DataBuffer(n_channels=8, frame_rate=128, plotting_window=5, csv_window=2, fileindex=self.file_index)
        self.ser = serial.Serial(self.port, self.baud_rate)
        print(f"Connected to {self.port} at {self.baud_rate} baud rate")

    def send_signal(self,signal):
        try:
            # Wait a bit to make sure the connection is ready
            time.sleep(2)

            # Send the start/stop signal
            self.ser.write(signal.encode())  # Sending the signal as bytes
            print(f"Signal '{signal}' sent.")
        except Exception as e:
            print(f"Failed to send signal: {e}")
        finally:
            self.ser.close()

    def init_connection(self):
        """Initialize the Bluetooth serial connection."""
        self.send_signal('S')
        
        while True:
            data = self.read_data()
            if data is not None:
                if isinstance(data, str) and "Connected to target device" in data:
                    print("[IMU]: Connection established.")
                    self.data_buffer.set_recording(True)
                    break
                if isinstance(data, int): # package count
                    print("[IMU]: Connection established.")
                    self.data_buffer.set_recording(True)
                    break
                print(data)
        
    def read_data(self):
        if self.ser.in_waiting:
            data = self.ser.readline().decode('utf-8').strip()
            if data.startswith("Package count: "):
                package_count = int(data[len("Package count: "):])
                return package_count
            if data == "" or len(data.split("\t")) != 7:
                return data
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

    def map_geometry_to_ppg(self, x,y,z):
        #z = -z
        #y = -x
        #x = -y
        
        return -y, -x, -z

    def process_acc(self, acc):
        # Assuming the maximum value is 2g (units: N)
        acc_lsb_div = 2**14 
        return acc / acc_lsb_div * 9.81

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
            print(f"[IMU]: Error reading data: {e}")
            return
        
        if data:
            if isinstance(data, int):
                package = data
                #print(f"[IMU] Package count: {package}")
                if package != self.packages[-1]:
                    self.packages.append(package)
                if self.current_package != package:
                    self.current_package = package
                return None
            elif isinstance(data, str):
                print("[IMU]: ",data)
                return None
            
            (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer) = data
            acc_x = self.process_acc(acc_x)
            acc_y = self.process_acc(acc_y)
            acc_z = self.process_acc(acc_z)
            acc_x, acc_y, acc_z = self.map_geometry_to_ppg(acc_x, acc_y, acc_z)
            gyro_x = self.process_gyro(gyro_x)
            gyro_y = self.process_gyro(gyro_y)
            gyro_z = self.process_gyro(gyro_z)
            gryo_x, gyro_y, gyro_z = self.map_geometry_to_ppg(gyro_x, gyro_y, gyro_z)

            # Add data to buffer
            
            for i, val in enumerate([acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer]):
                self.data_buffer.add_data(i, val)

            return acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer
        return None
    
    def run(self):
        """Main loop for the IMU reading thread."""
        self.init_connection()  # Initialize connection when starting the thread
        while self.running:
            self.update()
    
    def start_threads(self):
        """Start the IMU data reading thread."""
        if not self.running:
            self.running = True
            
            self.threads = []
            self.threads.append(threading.Thread(target=self.run, daemon=True))  # Start in a daemon thread
            self.threads.append(threading.Thread(target=self.data_buffer.dump_to_txt, daemon=True))
            
        for thread in self.threads:
            thread.start()    
        print("[IMU]: Data reading thread started.")

    def stop_threads(self):
        """Stop the IMU data reading thread."""
        if self.running:
            print("Stopping data reading thread...")
            self.running = False
            if self.thread is not None:
                self.thread.join()  # Wait for the thread to finish
                print("[IMU]: Data reading thread stopped.")
            
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
    
    def end_run(self):
        """Stops the run loop, saves the data, and closes the serial connection."""
        self.running = False  # Stop the reading loop
        self.save_data()  # Save any remaining data
        self.ser.close()  # Close the serial port
        print(f"[IMU]: Package loss: {self.get_package_loss()*100:.2f} %")
        print(f"[IMU]: Data loss: {self.get_data_loss()*100:.2f} %")
        print(f"[IMU]: Data saved to {self.save_file}")
    
    def stop_threads(self):
        self.save_data()  # Save any remaining data
        self.ser.close()  # Close the serial port
        print(f"[IMU]: Package loss: {self.get_package_loss()*100:.2f} %")
        print(f"[IMU]: Data loss: {self.get_data_loss()*100:.2f} %")
        print(f"[IMU]: Data saved to {self.save_file}")




if __name__ == "__main__":
    bluetooth_port = 'COM6'  # Change this to the actual port
    baud_rate = 115200
    imu_reader = BluetoothIMUReader('COM6', 115200, save_file='imu_data.csv')
    imu_reader.start_threads()  # Start the data reading thread
    # Later on, you can stop the thread with
    # wait for 10s
    time.sleep(100)
    imu_reader.end_run()

    
