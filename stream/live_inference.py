import os
# to prevent forrtl: error (200): program aborting due to control-C event
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

from PPG.wristband_listener import *
from IMU.BluetoothIMU import BluetoothIMUReader

import numpy as np
import argparse
import signal
import time
import pickle

parser = argparse.ArgumentParser(description='Record Wristband Signal')
parser.add_argument('--file_index', type=int, default=0, help='recording index')
parser.add_argument('--sensor_size', type=str, default='M', help='size of the sensor footprint')
args = parser.parse_args()

FRAME_RATE_PPG = 112.22
FRAME_RATE_IMU = 112.1
WLEN = 5
N_PPG_CHANNELS = 16
recording_status = False
calibration_status = False



#%% main
if __name__ == '__main__':

    # Define a handler function
    def signal_handler(sig, frame):
        print("Keyboard interrupt received. Stopping threads...")
        imu_listener.stop_threads()
        wristband_listner.stop_threads()
        print("Threads stopped.")
        exit(0)
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)


    wristband_listner = WristbandListener(n_ppg_channels=N_PPG_CHANNELS, window_size=WLEN, csv_window=2,
                                     frame_rate=FRAME_RATE_PPG, fileindex=args.file_index, bracelet=args.sensor_size)
    imu_listener = BluetoothIMUReader(port = 'COM13', baud_rate=115200, file_index=args.file_index, frame_rate=FRAME_RATE_IMU)

    
    wristband_listner.start_threads()
    imu_listener.start_threads()


    while True:

        try:
            ppg_data = wristband_listner.data_buffer.plotting_queues()
            imu_data = imu_listener.data_buffer.plotting_queues()
            #print(ppg_data)
            #print(np.array(ppg_data).shape, np.array(imu_data).shape)
            ppg_data_length = min([len(el) for el in ppg_data[:-1]])
            ppg_timestamps = np.array(ppg_data[-1])[:ppg_data_length].T
            ppg_data = np.array([el[:ppg_data_length] for el in ppg_data[:-1]]).T
            imu_timestamp = np.array(imu_data[-2:]).T
            imu_data = np.array(imu_data[:-2]).T
            figure, axes = plt.subplots(2, 1, figsize=(10, 10))
            axes[0].plot(ppg_data[:,-3:])
            axes[0].set_title("PPG Data")   
            axes[1].plot(np.array(imu_data)[:,:-2])
            axes[1].set_title("IMU Data")
            #save the figure
            plt.savefig('live_data.png')
            plt.close()

            # save data to pickle file
            with open('live_data.pkl', 'wb') as f:
                pickle.dump({'ppg_data': ppg_data, 'ppg_timestamps': ppg_timestamps, 'imu_data': imu_data, 'imu_timestamp': imu_timestamp}, f)

            time.sleep(0.1)




        except KeyboardInterrupt:
            print("Keyboard interrupt received. Stopping threads...")
            imu_listener.stop_threads()
            wristband_listner.stop_threads()
            print("Threads stopped.")
            break




        


