#%%

import os
# to prevent forrtl: error (200): program aborting due to control-C event
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
import matplotlib
matplotlib.use('Agg')
from PPG.wristband_listener import *
from causal_filters import *
from IMU.BluetoothIMU import BluetoothIMUReader
from flask import Flask, jsonify
from flask_cors import CORS
import threading

import numpy as np
import argparse
import signal
import time
from scipy.signal import correlate, correlation_lags

from GestureFiltering import GestureFilteringHMM

import torch
from pathlib import Path
import yaml
import sys
import glob
import os
sys.path.append(r"C:\Users\lhauptmann\Code\GestureDetection")
import matplotlib.pyplot as plt
from ahrs.common import Quaternion


    
LETTER_GESTURES = {
"a": "Swipe Forward",
"b": "Swipe Backward",
"c": "Swipe Left",
"d": "Swipe Right",
"p": "Fast Pinch",
"prr": "Rotate Right",
"prl": "Rotate Left",
"pbd": "Back to Default",
"pc": "Pinch Close",
"po": "Pinch Open",
"sp": "Side Tap",
"o": "Nothing",
"s": "Knock",
"pr": "Rotate",
}
global GESTURE_TO_LABEL, LABEL_TO_GESTURE, LABEL_TO_LETTER
LABEL_TO_LETTER = {
                        1: "a",
                        2: "b",
                        3: "c",
                        4: "d",
                        5: "pc",
                        6: "po",
                        7: "sp",
                        8: "pr",
                        0: "o",
                        9: "prr",
                        10: "prl",
                        11: "pbd",
                        12: "s"
                    }

LABEL_TO_GESTURE = {key: LETTER_GESTURES[val] for key, val in LABEL_TO_LETTER.items()}

GESTURE_TO_LABEL = {
    "a":1,
    "b":2,
    "c":3,
    "d":4,
    "p":8,
    "prr":0,
    "prl":0,
    "pbd":0,
    "pc":5,
    "po":6,
    "sp":7,
    "o":0,
    "s":0
}

n_classes = 9

def probability_mapping(probability:np.array, n_classes = n_classes, mapping = {8: [5,6]}):
    new_prob = np.zeros(n_classes - len(mapping))

    for i in range(probability.shape[0]):
        if i in mapping:
            for j in mapping[i]:
                new_prob[j] += probability[i] / len(mapping[i])
        else:
            new_prob[i] = probability[i]
    
    new_prob = new_prob / new_prob.sum()
    #print(new_prob.sum())
    
    return new_prob
    
    
def pretty_print_matrix(m:np.array):
    for i in range(m.shape[0]):
        print(" ".join([f"{el:.2f}" for el in m[i]]))
    

#%%

parser = argparse.ArgumentParser(description='Record Wristband Signal')
parser.add_argument('--file_index', type=int, default=0, help='recording index')
parser.add_argument('--sensor_size', type=str, default='M', help='size of the sensor footprint')
args = parser.parse_args()

FRAME_RATE_PPG = 112.22
FRAME_RATE_IMU = 112.1
WLEN = 3
N_PPG_CHANNELS = 16
recording_status = False
calibration_status = False

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
stop_event = threading.Event()

def get_correlation_lag(x,y):
    correlation = correlate(x, y, mode="full")
    lags = correlation_lags(x.size, y.size, mode="full")
    lag = lags[np.argmax(correlation)]
    return lag

def load_model(model_path):
    load_config=Path(os.path.join(model_path,"config.yml"))
    config = yaml.load(load_config.read_text(), Loader=yaml.Loader)
    #print(config)
    #del(config.model.nsensors["accel"])
    #del(config.model.nhidden_units["accel"])
    #del(config.model.nsensors["gyro"])
    #del(config.model.nhidden_units["gyro"])
    #del(config.model.nsensors["ppg"])
    #del(config.model.nhidden_units["ppg"])
    #config.model.nsensors["ppg"] = 16
    del config.model.nsensors["ppg"]
    del config.model.nhidden_units["ppg"]
    del config.model.kernel_multiplier["ppg"]
    del config.model.nsensors["ppg_accel"]
    del config.model.nhidden_units["ppg_accel"]
    del config.model.kernel_multiplier["ppg_accel"]

    device = "cpu"
    config.device = device
    config.data_config.max_shift = 0



    model = config.model.setup(prediction_heads={"gesture":n_classes}).to(device)
    weights_path = glob.glob(os.path.join(model_path , "best_model__*.pt"))[0]
    weights_path = glob.glob(os.path.join(model_path , "checkpoint_*.pt"))[0]
    load_state_dict = torch.load(weights_path, map_location=device)["model_state_dict"]
    print(f"Loading model from {weights_path}")
    
    #print(model)

    # remove all weights that correspond to pred_head
    #load_state_dict = {k: v for k, v in load_state_dict.items() if not k.startswith("pred_heads")}
    model.load_state_dict(load_state_dict, strict=False)
    model.eval()
    return model


    

def prepare_data(imu_data = None, ppg_data = None, window_size = 150):
    if ppg_data is not None:
        ppg_acc = ppg_data[:,-3:]
        ppg_mag = np.linalg.norm(ppg_acc, axis=1)
        
    imu_acc = imu_data[:,:3]
    imu_mag = np.linalg.norm(imu_acc, axis=1)

    if ppg_data is None:
        lag = 0
    else:
        lag_prior = -40
        lag = get_correlation_lag(ppg_mag, imu_mag)
        #print(lag)
        lag = int(1*lag + 0.0*lag_prior)
        lag = min(max(lag, -100), 0)

    if ppg_data is not None:
        latest_window_ppg = ppg_data[-window_size:,:]
    #latest_window_imu = imu_data[-lag:-lag+window_size,:]
    if lag < 0:
        latest_window_imu = imu_data[-window_size-lag:-lag,:]
    else:
        latest_window_imu = imu_data[-window_size:,:]

    
    if ppg_data is not None and not (latest_window_ppg.shape[0] == latest_window_imu.shape[0] == window_size):
        print(f"Shapes do not match: {latest_window_ppg.shape[0]} {latest_window_imu.shape[0]}")
        print(f"PPG: {ppg_acc.shape}, IMU: {imu_acc.shape}")
        return None

    if ppg_data is not None:
        latest_window_ppg = (latest_window_ppg - latest_window_ppg.mean(axis=0)) / latest_window_ppg.std(axis=0)
    else:
        latest_window_ppg = np.zeros((window_size, 16))
    latest_window_imu = (latest_window_imu - latest_window_imu.mean(axis=0)) / latest_window_imu.std(axis=0)

    sample = {
    "ppg": torch.Tensor(latest_window_ppg[:,:-3]).T.unsqueeze(0),
    "accel": torch.Tensor(latest_window_imu[:,:3]).T.unsqueeze(0),
    "gyro": torch.Tensor(latest_window_imu[:,3:6]).T.unsqueeze(0),
    "ppg_accel": torch.Tensor(latest_window_ppg[:,-3:]).T.unsqueeze(0),
    }

    return sample


def init_react_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.logger.disabled = True
    global latest_data            
    latest_data = {
        "imu_data": [],
        "gesture": "No Gesture",
        "confidence": 0,
        "probability": [0] * (n_classes),
        "filtered_gesture": "No Gesture",
    }

    @app.route('/data')
    def get_data():
        return jsonify(latest_data)

    
    def update_latest_data(imu_data, gesture, confidence, probability=None, filtered_gesture=None, orientation:np.array=None, rotation=None):
        # Convert numpy arrays to JSON-serializable data
        if isinstance(imu_data, np.ndarray):
            imu_data_list = []
            for i, row in enumerate(imu_data):
                data_point = {
                    "accelX": row[0], 
                    "accelY": row[1], 
                    "accelZ": row[2],
                    "gyroX": row[3], 
                    "gyroY": row[4], 
                    "gyroZ": row[5],
                    "orientation": {} # Default empty orientation
                }
                
                # Add orientation data if available
                if orientation is not None and len(orientation) > i:
                    orientation_angles = Quaternion(orientation[i]).to_angles()
                    data_point["orientation"] = {
                        "yaw": orientation_angles[0] / np.pi * 180,
                        "pitch": orientation_angles[1]/ np.pi * 180,
                        "roll": orientation_angles[2]/ np.pi * 180
                    }
                    
                imu_data_list.append(data_point)
                
            latest_data["imu_data"] = imu_data_list
            
        latest_data["gesture"] = gesture
        latest_data["confidence"] = float(confidence) * 100
        
        if rotation is not None:
            
            latest_data["rotation"] = rotation
            
        if filtered_gesture is not None:
            if filtered_gesture != "Nothing":
                print(filtered_gesture)
            latest_data["filtered_gesture"] = filtered_gesture
        
        if probability is not None:
            latest_data["probabilities"] = [
                {"name": LABEL_TO_GESTURE[i], "probability": float(probability[i])*100} 
                for i in range(len(probability))
            ]

        #print(latest_data)

        #print(latest_data)
    threading.Thread(target=lambda: app.run(port=5000, debug=False), daemon=True).start()
    
    return update_latest_data




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
   
    inference_period = 32/112.2
    wristband_listner = WristbandListener(n_ppg_channels=N_PPG_CHANNELS, window_size=WLEN, csv_window=2,
                                     frame_rate=FRAME_RATE_PPG, fileindex=-1, bracelet=args.sensor_size)
    imu_listener = BluetoothIMUReader(port = 'COM6', baud_rate=115200, file_index=-1, frame_rate=FRAME_RATE_IMU)

    
    #wristband_listner.start_threads()
    imu_listener.start_threads()

    model_path = r"C:\Users\lhauptmann\Code\GestureDetection\experiments\2025-01-17_111553"
    model = load_model(model_path)
    
    trans_self_prob = 0.9
    filter = GestureFilteringHMM(n_classes, start_neg_prob=0.5, trans_self_prob=trans_self_prob, emit_self_prob=0.9)
    rotation_filter = RotationFilter(track_rotation_index=8, probability_threshold=0.2, inference_interval=inference_period)

    # 8 is the Rotation state, 5 is the Pinch Close state, 6 is the Pinch Open state
    # It is not possibel to got to 8 from any state but 5 and 8
    filter.trans_prob[8, :6] = 0
    filter.trans_prob[8, 7:] = 0
    # you can only transition to 6 from 5 and 8
    #filter.trans_prob[6, :] = 0
    #filter.trans_prob[6, 6] = trans_self_prob
    # from state 5 you can either go to 5 or 8
    filter.trans_prob[:, 5] = [0, 0, 0, 0, 0, trans_self_prob, 0, 0, 1 -trans_self_prob]
    # from state 8 you can eithet go to 8 or 6
    filter.trans_prob[:, 8] = [0, 0, 0, 0, 0, 0, 0.02, 0, 0.98]

    
    # normalize
    filter.trans_prob = filter.trans_prob / filter.trans_prob.sum(axis=0, keepdims=True)
    

    
    print("Transition matrix:")
    pretty_print_matrix(filter.trans_prob)
    
    # 8 is never emitted, but it's possible to observe 0 when in state 8
    
    filter.emit_prob[0,8] += filter.emit_prob[8,8]
    filter.emit_prob[8,8] = 0
    print("\nEmission matrix:")
    pretty_print_matrix(filter.emit_prob)
    
    
    prediction_filter = PredictionFilter(n_classes=n_classes-1, label_to_gesture=LABEL_TO_GESTURE)
    orientation_filter = MadgwickRotationFilter(sampling_frequency=112.2, history_size=800, filter_gyro=False)
  
    update_latest_data = init_react_app()
    highpassfilter = HighPassFilter(cutoff_frequency=0.5, sampling_rate=112.2, num_channels=3, order=3)
    
    started_inference = False
    
    last_inf_time = time.time()
    
    window_size = 150
    
    imu_queue = deque(maxlen=800)
    
    
    try:
        while not stop_event.is_set():

            start_time = time.time()
           
            
            #ppg_data = wristband_listner.data_buffer.plotting_queues()
            #ppg_data = None
            
            new_imu_data = np.array(imu_listener.data_buffer.get_new_data()[:-2]).T
            if new_imu_data.shape[0] != 0:
                imu_queue.extend(new_imu_data)
                heuristic_gyro_offset = np.array([10.7,-9,2.7])
                new_imu_data[:,3:] = new_imu_data[:,3:] - heuristic_gyro_offset
                orientation_filter.update_imu_values(new_imu_data)
                
            
            imu_data = np.array(imu_queue)
            
            #imu_data = imu_listener.data_buffer.plotting_queues()
            

            #ppg_data_length = min([len(el) for el in ppg_data[:-1]])

            #ppg_data = np.array([el[:ppg_data_length] for el in ppg_data[:-1]]).T

            #imu_data = np.array(imu_data[:-2]).T
            #if imu_data.shape[0] != 0 or ppg_data.shape[0] != 0:
            #    print(imu_data.shape, ppg_data.shape)

            if imu_data.shape[0] > 200: #and ppg_data.shape[0] > 200:
                
                if started_inference == False:
                    print("Started inference")
                    started_inference = True
                
                sample = prepare_data(ppg_data = None, imu_data = imu_data, window_size=window_size)
                if sample is None:
                    continue
            
                with torch.no_grad():
                    output,_,_,xf = model(sample)
                    output = torch.nn.functional.softmax(output, dim=1).squeeze().numpy()
                    output = probability_mapping(output)
                    
                filtered_output = filter.update(np.append(output, [0]))
                #print(filtered_output)
                                    
                pred_gesture = output.argmax()
                pred_gesture_filtered = filtered_output.argmax()
                #print(pred_gesture, filtered_output)
                
                filtered_gesture = prediction_filter.update(filtered_output)
                
                #orientation_history = np.array(orientation_filter.get_rotation_history())
                #if len(orientation_history) > 0:
                #    print(orientation_history)
                delta_rotation = rotation_filter.update(filtered_output, orientation_filter.get_current_rotation())
                update_latest_data(
                    imu_data, 
                    LABEL_TO_GESTURE[pred_gesture_filtered], 
                    filtered_output[pred_gesture_filtered], 
                    probability = filtered_output, 
                    filtered_gesture = LABEL_TO_GESTURE[filtered_gesture], 
                    orientation = np.array(orientation_filter.get_rotation_history()),
                    rotation = delta_rotation
                    )
                #update_latest_data(imu_data, LABEL_TO_GESTURE[pred_gesture], output[pred_gesture], output)
                
                    
                    
            else:
                
                if started_inference == True and time.time() - last_inf_time > 5:
                    print("Stopped inference")
                    started_inference = False
                    last_inf_time = time.time()
                    
            # Control the loop timing
            sleep_time = inference_period - (time.time() - start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
       

    except KeyboardInterrupt:
        signal_handler(None, None)
        
    finally:
        plt.close('all')
        

    
                    






        
# %%
