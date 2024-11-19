import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import numpy as np
import threading
from collections import deque
from collections import defaultdict
from PPG.wristband_listener import DataBuffer

SAMPLES_PER_PACKAGE = 8
save_path = r"C:\Users\lhauptmann\Code\WristPPG2\data"

class DataBuffer:
    def __init__(self, n_channels=8, frame_rate=128, plotting_window=5, csv_window=2, fileindex=0):
        
        # timestamp = time.strftime("%Y%m%d-%H%M%S")
        # self.filename = f"..//recordings//ppg_data_{timestamp}"
        self.filename = f'C://Users//lhauptmann//Code//WristPPG2//data//imu_{fileindex:03d}'

        self.plotting_winoow = plotting_window
        self.csv_window = csv_window
        self.frame_rate = frame_rate

        self.buffers = [deque(maxlen=int((plotting_window+1)*frame_rate + 1)) for _ in range(n_channels)]
        self.csv_buffers = [deque(maxlen=int((csv_window+1)*frame_rate+1)) for _ in range(n_channels)]

        self.recording = False
        self.n_channels = n_channels
        
        self.dump_thread = None
        self.dump_thread_running = threading.Event()

    def add_data(self, qidx, val):
        self.buffers[qidx].append(val)
        self.csv_buffers[qidx].append(val)

    def dump_to_txt(self):
        # with open(self.filename, mode='a', newline='') as file:
        #     writer = csv.writer(file)
        #     for i in range(self.n_channels):
        #         row = f'{i}' + np.array(self.csv_buffers[i]).astype(str)
        #         writer.writerow(row)
        while self.dump_thread_running.is_set():
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


    def start_dump_thread(self):
        self.dump_thread_running.set()  # Start the thread
        self.dump_thread = threading.Thread(target=self.dump_to_txt, daemon=True)
        self.dump_thread.start()


    def stop_dump_thread(self):
        self.dump_thread_running.clear()  # Signal the thread to stop
        if self.dump_thread:
            self.dump_thread.join()  # Wait for the thread to finish

import asyncio
import serial_asyncio
from collections import defaultdict
import time
import threading

class BluetoothIMUReader:
    def __init__(self, port, baud_rate, save_file="data.csv", file_index=0, frame_rate=112.2):
        self.port = port
        self.baud_rate = baud_rate
        self.save_file = save_file
        self.ser = serial.Serial(self.port, self.baud_rate)
        self.received_data = []
        self.packages = [-1]
        self.data_losses = []
        self.current_package = -1
        self.sample_per_package = defaultdict(int)
        self.running = False
        self.file_index = file_index
        self.frame_rate = frame_rate
        self.last_package_time = 0
        self.new_package_flag = False

        # Initialize the data buffer
        self.data_buffer = DataBuffer(n_channels=8, frame_rate=self.frame_rate, plotting_window=5, csv_window=2, fileindex=self.file_index)
        print(f"Connected to {self.port} at {self.baud_rate} baud rate")

    async def send_signal(self, signal):
        """Asynchronously send a signal to start/stop."""
        try:
            await asyncio.get_running_loop().run_in_executor(None, self.ser.write, signal.encode())
            print(f"[IMU] Signal '{signal}' sent.")
        except Exception as e:
            print(f"[IMU] Failed to send signal: {e}")

    async def init_connection(self):
        """Initialize the Bluetooth serial connection asynchronously."""
        await self.send_signal('S')
        while True:
            data = await self.read_data_async()
            if data is not None:
                if isinstance(data, str) and "Connected to target device" in data:
                    print("[IMU]: Connection established.")
                    break
                if isinstance(data, int):  # Package count
                    print("[IMU]: Connection established.")
                    break

    async def read_data_async(self):
        """Asynchronously read data from the serial port."""
        if self.ser.in_waiting:
            data = await asyncio.get_running_loop().run_in_executor(None, self.ser.readline)
            data = data.decode('utf-8').strip()

            if data.startswith("Package count: "):
                return int(data[len("Package count: "):])
            if data == "" or len(data.split("\t")) != 7:
                return data

            # Parse accelerometer and gyroscope data
            data_splits = data.split("\t")
            acc_x, acc_y, acc_z = map(int, data_splits[:3])
            gyro_x, gyro_y, gyro_z = map(int, data_splits[3:6])
            timestamp = float(data_splits[6])
            timestamp_computer = int(time.time() * 1000)

            return acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer
        return None

    async def run(self):
        """Main asynchronous loop for reading IMU data."""
        await self.init_connection()
        self.running = True
        while self.running:
            await self.update()

    async def update(self):
        """Fetch and process data asynchronously."""
        
        try:
            data = await self.read_data_async()
        except Exception as e:
            print(f"[IMU]: Error reading data: {e}")
            return

        if data:
            if isinstance(data, int):  # Package count
                package = data
                if package != self.packages[-1]:
                    self.packages.append(package)
                self.current_package = package
                return None
            elif isinstance(data, str):
                print("[IMU]:", data)
                return None

            # Process sensor data
            acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer = data
            acc_x = self.process_acc(acc_x)
            acc_y = self.process_acc(acc_y)
            acc_z = self.process_acc(acc_z)
            acc_x, acc_y, acc_z = self.map_geometry_to_ppg(acc_x, acc_y, acc_z)
            gyro_x = self.process_gyro(gyro_x)
            gyro_y = self.process_gyro(gyro_y)
            gyro_z = self.process_gyro(gyro_z)
            gyro_x, gyro_y, gyro_z = self.map_geometry_to_ppg(gyro_x, gyro_y, gyro_z)

            # Add data to buffer
            for i, val in enumerate([acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, timestamp, timestamp_computer]):
                self.data_buffer.add_data(i, val)
            self.sample_per_package[self.current_package] += 1

    def start_threads(self):
        """Start async tasks to read IMU data in a separate thread."""
        def async_task():
            """Run the asyncio event loop in a separate thread."""
            asyncio.run(self.run())  # Start the event loop

        # Start the async task in a new thread
        
        async_thread = threading.Thread(target=async_task, daemon=True)
        async_thread.start()
        self.threads = [async_thread]
        
        # Start the data dump thread
        self.data_buffer.start_dump_thread()
        

        print("[IMU]: Async IMU reading thread started.")

    def stop_threads(self):
        self.running = False
        """Stop the IMU data reading asynchronously."""
        print("[IMU]: Stopping data reading thread...")
        for thread in self.threads:
            #print(thread)
            thread.join()
            self.data_buffer.stop_dump_thread()
        
        print("[IMU]: Data reading stopped.")
        self.end_run()

    def map_geometry_to_ppg(self, x, y, z):
        #z = -z
        #y = -x
        #x = -y
        return -y, -x, -z

    def process_acc(self, acc):
        acc_lsb_div = 2**14 
        return acc / acc_lsb_div * 9.81

    def process_gyro(self, gyro):
        gyro_lsb_div = 32 # since gyro range is 1024 deg/s now
        return gyro / gyro_lsb_div

         
    def get_package_loss(self):
        package_count = np.array(self.packages[1:])
        package_count = np.unique(package_count)
        package_count.sort()
        package_diff = np.diff(package_count)
        package_loss = package_diff[package_diff > 1]
        #print(package_loss)
        package_loss = np.sum(package_loss - 1)
        return package_loss / (len(package_count) + package_loss)
        
        

    def get_data_loss(self):
        if not self.packages:
            return np.nan
        
        start_package, end_package = self.packages[1], self.packages[-1]
        total_amount = np.sum([self.sample_per_package[key] for key in range(start_package, end_package)])
        desired_amount = (end_package - start_package) * SAMPLES_PER_PACKAGE
        if desired_amount == 0:
            return np.nan
        return 1 - total_amount / desired_amount
    
    def end_run(self):
        """Stops the run loop, saves the data, and closes the serial connection."""
        self.send_signal('E')
        self.running = False  # Stop the reading loop
        self.ser.close()  # Close the serial port
        print(f"[IMU]: Package loss: {self.get_package_loss()*100:.2f} %")
        print(f"[IMU]: Data loss: {self.get_data_loss()*100:.2f} %")
        print(f"[IMU]: Data saved to {self.data_buffer.filename}.txt")
        #print("[IMU] Sample ",[np.mean([el for el in self.sample_per_package.values()])])



if __name__ == "__main__":
    bluetooth_port = 'COM6'  # Change this to the actual port
    baud_rate = 115200
    imu_reader = BluetoothIMUReader('COM6', 115200, save_file='imu_data.csv')
    try:
        
        imu_reader.start_threads()  # Start the data reading thread
        while imu_reader.running:
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Stopping the IMU reader")
        imu_reader.stop()

    
