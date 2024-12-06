#%%

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
from scipy.signal import correlate, correlation_lags
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

import matplotlib.pyplot as plt
import torch
from pathlib import Path
import yaml
import sys
import glob
import os
sys.path.append(r"C:\Users\lhauptmann\Code\GestureDetection")


    
LETTER_GESTURES = {
"a": "Swipe Forward",
"b": "Swipe Backward",
"c": "Swipe Left",
"d": "Swipe Right",
"p": "Fast Pinch",
"prr": "Rotate Right",
"prl": "Rotate Left",
"pbd": "Back to Default",
"pc": "Pinch Hold",
"po": "Pinch Open",
"sp": "Side Tap",
"o": "Nothing",
"s": "Knock"
}
LABEL_TO_LETTER = {
    0: "a",
    1: "b",
    2: "c",
    3: "d",
    4: "p",
    5: "po",
    6: "sp",
    7: "o",
    8: "prr",
    9: "prl",
    10: "pbd",
    8: "pc",
    12: "s"
}

LABEL_TO_GESTURE = {key: LETTER_GESTURES[val] for key, val in LABEL_TO_LETTER.items()}

GESTURE_TO_LABEL = {
    "a":0,
    "b":1,
    "c":2,
    "d":3,
    "p":4,
    "prr":7,
    "prl":7,
    "pbd":7,
    "pc":8,
    "po":5,
    "sp":6,
    "o":7,
    "s":7
}

#%%

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


def get_correlation_lag(x,y):
    correlation = correlate(x, y, mode="full")
    lags = correlation_lags(x.size, y.size, mode="full")
    lag = lags[np.argmax(correlation)]
    return lag

def load_model(model_path):
    load_config=Path(os.path.join(model_path,"config.yml"))
    config = yaml.load(load_config.read_text(), Loader=yaml.Loader)
    #del(config.model.nsensors["accel"])
    #del(config.model.nhidden_units["accel"])
    #del(config.model.nsensors["gyro"])
    #del(config.model.nhidden_units["gyro"])
    #del(config.model.nsensors["ppg"])
    #del(config.model.nhidden_units["ppg"])
    config.model.nsensors["ppg"] = 16
    device = "cpu"
    config.device = device
    config.data_config.max_shift = 0



    model = config.model.setup(prediction_heads={"gesture":9}).to(device)
    weights_path = glob.glob(os.path.join(model_path , "best_model__*.pt"))[0]
    weights_path = glob.glob(os.path.join(model_path , "checkpoint_*.pt"))[0]
    load_state_dict = torch.load(weights_path, map_location=device)["model_state_dict"]
    print(f"Loading model from {weights_path}")

    # remove all weights that correspond to pred_head
    #load_state_dict = {k: v for k, v in load_state_dict.items() if not k.startswith("pred_heads")}
    model.load_state_dict(load_state_dict, strict=False)
    model.eval()
    return model

def prepare_data(ppg_data, imu_data):

    ppg_acc = ppg_data[:,-3:]
    imu_acc = imu_data[:,:3]

    ppg_mag = np.linalg.norm(ppg_acc, axis=1)
    imu_mag = np.linalg.norm(imu_acc, axis=1)

    lag_prior = -40
    lag = get_correlation_lag(ppg_mag, imu_mag)
    lag = int(0.2*lag + 0.8*lag_prior)

    window_size = 150
    latest_window_ppg = ppg_data[:window_size,:]
    latest_window_imu = imu_data[-lag:-lag+window_size,:]

    latest_window_ppg = (latest_window_ppg - latest_window_ppg.mean(axis=0)) / latest_window_ppg.std(axis=0)
    latest_window_imu = (latest_window_imu - latest_window_imu.mean(axis=0)) / latest_window_imu.std(axis=0)

    sample = {
    "ppg": torch.Tensor(latest_window_ppg[:,:-3]).T.unsqueeze(0),
    "accel": torch.Tensor(latest_window_imu[:,:3]).T.unsqueeze(0),
    "gyro": torch.Tensor(latest_window_imu[:,3:6]).T.unsqueeze(0),
    "ppg_accel": torch.Tensor(latest_window_ppg[:,-3:]).T.unsqueeze(0),
    }

    return sample






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

    model_path = r"C:\Users\lhauptmann\Code\GestureDetection\experiments\2024-12-03_180833"
    model = load_model(model_path)


    while True:



        try:
            ppg_data = wristband_listner.data_buffer.plotting_queues()
            imu_data = imu_listener.data_buffer.plotting_queues()
            #print(ppg_data)
            #print(np.array(ppg_data).shape, np.array(imu_data).shape)
            ppg_data_length = min([len(el) for el in ppg_data[:-1]])
            #ppg_timestamps = np.array(ppg_data[-1])[:ppg_data_length].T
            ppg_data = np.array([el[:ppg_data_length] for el in ppg_data[:-1]]).T
            #imu_timestamp = np.array(imu_data[-2:]).T
            imu_data = np.array(imu_data[:-2]).T
            #figure, axes = plt.subplots(2, 1, figsize=(10, 10))
            #axes[0].plot(ppg_data[:,-3:])
            #axes[0].set_title("PPG Data")   
            #axes[1].plot(np.array(imu_data)[:,:-2])
            #axes[1].set_title("IMU Data")
            #save the figure
            #plt.savefig('live_data.png')
            #plt.close()

            # save data to pickle file
            #with open('live_data.pkl', 'wb') as f:
            #    pickle.dump({'ppg_data': ppg_data, 'ppg_timestamps': ppg_timestamps, 'imu_data': imu_data, 'imu_timestamp': imu_timestamp}, f)

            if imu_data.shape[0] > 200 and ppg_data.shape[0] > 200:
                sample = prepare_data(ppg_data, imu_data)
                with torch.no_grad():
                    output,_,_,xf = model(sample)
                    gesture = torch.argmax(output).item()
                    print(LABEL_TO_GESTURE[gesture])
                figure, ax = plt.subplots(1, figsize=(10, 10))
                ax.plot(sample["ppg_accel"].squeeze().T, label="PPG Accel")
                ax.plot(sample["accel"].squeeze().T, label="IMU Accel")
                ax.set_title(LABEL_TO_GESTURE[gesture])
                ax.legend()
                plt.savefig('live_data.png')
                plt.close()





        except KeyboardInterrupt:
            print("Keyboard interrupt received. Stopping threads...")
            imu_listener.stop_threads()
            wristband_listner.stop_threads()
            print("Threads stopped.")
            break






        