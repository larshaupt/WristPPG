from PPG.wristband_listener import *
from IMU.BluetoothIMU import BluetoothIMUReader

import multiprocessing
import threading
import asyncio
import numpy as np
import sys
import dash
from dash import Dash, dcc, html, Input, Output, callback
import dash_daq as daq
import plotly
import plotly.graph_objs as go
import os
import plotly.subplots
import argparse

from scipy.signal import butter, lfilter, lfilter_zi

parser = argparse.ArgumentParser(description='record webcam video')
parser.add_argument('--file_index', type=int, default=0, help='recording index')
parser.add_argument('--sensor_size', type=str, default='M', help='size of the sensor footprint')
args = parser.parse_args()

FRAME_RATE = 128
WLEN = 5
N_PPG_CHANNELS = 16
recording_status = False
calibration_status = False

ppg_max = [1600, 1200, 400, 1400, 8000, 4000, 6000, 2000,
            8000, 4000, 6000, 2000, 4000, 2000, 3000, 800]

ppg_min = [-2000, -1400, -500, -1400, -6000, -4000, -8000, -3000,
            -6000, -4000, -8000, -3000, -3000, -2000, -4000, -1400]

class LiveFigure:
    def __init__(self, height=800, width=1600, wlen=128, n_ppg_channels=16):
        self.wlen = wlen

        # channel offsets
        self.green_offsets = [0 for _ in range(8)]
        self.ir_offsets = [0 for _ in range(8)]

        self.fig = plotly.subplots.make_subplots(
            rows=8, cols=6,
            specs= [[{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None , None],
                ],
            print_grid=True, 
            column_titles=["green", "IR"],
        )
    
        # update figure size
        self.fig.update_layout(height=height, width=width)

        # ppgs
        for ch in range(8): # green
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], name=f"channel_{ch+1}", line=dict(color='black'), showlegend=False), 
                            row=ch+1, col=1, secondary_y=False)
            self.fig.update_yaxes(title_text=f"ch {ch+1}", row=ch+1, col=1, title_standoff=0)

        for ch in range(8): # IR
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], name=f"channel_{ch+1}", line=dict(color='black'), showlegend=False), 
                                row=ch+1, col=3, secondary_y=False)
            self.fig.update_yaxes(title_text=f"ch {ch+1}", row=ch+1, col=3, title_standoff=0)

        self.fig.update_layout(yaxis=dict(autorangeoptions=dict(clipmax=1e6)))

        self.mins = [0 for _ in range(16)]
        self.maxs = [1e5 for _ in range(16)]
        self.alpha = 0.9

        ## accelerometer
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Example: blue, orange, green for x,y,z
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i],showlegend=True, line=dict(color=colors[i])), row=3, col=5)
        self.fig.update_yaxes(title_text=f"PPG Accelerometer", row=3, col=5, range=([-20, 20]))
        
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i], showlegend=False,line=dict(color=colors[i])), row=5, col=5)
        self.fig.update_yaxes(title_text=f"IMU Accelerometer", row=5, col=5, range=([-20, 20]))
        
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i], showlegend=False,line=dict(color=colors[i])), row=7, col=5)
        self.fig.update_yaxes(title_text=f"IMU Gyroscope", row=7, col=5, range = [-512, 512])

    def _update_ppg_plots(self, input_data):
        # update the y axes maxs and mins
        for ch in range(16):
            min = np.percentile(input_data[ch], 5) * 0.9
            max = np.percentile(input_data[ch], 95) * 1.1
            self.mins[ch] = self.mins[ch] * self.alpha + min * (1 - self.alpha)
            self.maxs[ch] = self.maxs[ch] * self.alpha + max * (1 - self.alpha)

        for ch in range(8):
            self.fig['data'][ch]['y'] = np.array(input_data[ch])
            self.fig['data'][ch+8]['y'] = np.array(input_data[ch+8])
    
            self.fig.update_yaxes(row=ch+1, col=1, range=[self.mins[ch], self.maxs[ch]])
            self.fig.update_yaxes(row=ch+1, col=3, range=[self.mins[ch+8], self.maxs[ch+8]])

    def _update_ppg_imu_plots(self, input_data):
        # Ensure input_data has data for accelerometer and gyroscope
        if input_data is not None:
            for ch in range(3):  # Assuming input_data[16:19] are accelerometer values
                self.fig['data'][ch + 16]['y'] = np.array(input_data[16+ch])  # Accelerometer
            #self.fig.update_yaxes(row=3, col=5, range=[-20, 20])

    def update_imu_plots(self, input_data):
        #print(len(input_data[0]))
        # Ensure input_data has data for accelerometer and gyroscope
        if input_data is not None:
            
            # Update IMU accelerometer plots
            for ch in range(3):  # x, y, z axes
                self.fig['data'][ch+19]['y'] = np.array(input_data[ch]) 
            #self.fig.update_yaxes(row=5, col=5, range=[-20, 20])
            
            # Update PPG gyroscope plots
            for ch in range(3):  # x, y, z axes
                self.fig['data'][ch+22]['y'] = np.array(input_data[3+ch])  
            #self.fig.update_yaxes(row=7, col=5, range=[-512, 512])
            
            # You can similarly add more plots if needed, e.g., for IMU gyroscope data


    def _scale_ppg(self, input_data):
        # min max scale
        ppg_scale = [ppg_max[i] - ppg_min[i] for i in range(16)]
        scaled_data = [(input_data[i] - ppg_min[i]) / ppg_scale[i] for i in range(8)]
        scaled_data += [(input_data[i] - ppg_min[i]) / ppg_scale[i] for i in range(8, 16)]
        return scaled_data

    def update_ppg_plots(self, input_data_ppg, input_data_imu = None):
        filtered_ppg = [filter_ppg(input_data_ppg[i]) for i in range(16)] 
        filtered_ppg = self._scale_ppg(filtered_ppg)
        self._update_ppg_plots(filtered_ppg)
        self._update_ppg_imu_plots(input_data_ppg)


def filter_ppg(input_signal):
    input_signal = np.array(input_signal)
    nans, x = np.isnan(input_signal), lambda z: z.nonzero()[0]
    input_signal[nans] = np.interp(x(nans), x(~nans), input_signal[~nans])

    b, a = butter(5, [0.1, 63.5], fs=128, btype='band')
    zi = lfilter_zi(b, a) * input_signal[0]
    filtered_signal = lfilter(b, a, input_signal, zi=zi)[0]
    return filtered_signal

live_figure = LiveFigure(wlen=WLEN*FRAME_RATE, n_ppg_channels=N_PPG_CHANNELS)
wristband_listner = WristbandListener(n_ppg_channels=N_PPG_CHANNELS, window_size=WLEN, csv_window=2,
                                      frame_rate=FRAME_RATE, fileindex=args.file_index, bracelet=args.sensor_size)
imu_listener = BluetoothIMUReader(port = 'COM6', baud_rate=115200, file_index=args.file_index)

def calibrate_min_max():
    live_figure.green_min = 0
    live_figure.green_max = 1e5
    live_figure.ir_min = 0
    live_figure.ir_max = 1.5e5

#%% DASH APP
app = Dash(__name__)
app.assets_ignore = '.*'

app.layout = html.Div(
    [    
        daq.BooleanSwitch(
                id='record-switch',
                on=False,
                label="record",
                style={'display': 'inline-block', 'margin-left': '5px'},
        ),
        html.Div(id='recording-switch-output'),

        dcc.Graph(id='live-graph', figure=live_figure.fig),
        dcc.Interval(
            id='graph-update',
            interval = 125, # in milliseconds
            n_intervals = 0
        ),
    ]
)

@app.callback(
    Output('recording-switch-output', 'children'),
    Input('record-switch', 'on')
)
def update_switch1(on):
    global recording_status
    recording_status = on
    wristband_listner.data_buffer.set_recording(on)
    imu_listener.data_buffer.set_recording(on)
    return ''

@app.callback(
    Output('live-graph', 'figure'),
    [ Input('graph-update', 'n_intervals') ],
    [dash.dependencies.State('live-graph', 'figure')]
)
def update_graph_live(n_intervals, existing_fig):
    global live_figure, wristband_listner
    
    if len(wristband_listner.data_buffer.plotting_queues()[0]) != 0:
        live_figure.update_ppg_plots(wristband_listner.data_buffer.plotting_queues())
    if len(imu_listener.data_buffer.plotting_queues()[0]) != 0:
        live_figure.update_imu_plots(imu_listener.data_buffer.plotting_queues())
    return live_figure.fig

def start_background_process():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(wristband_listner.connect_and_stream())

#%% main
if __name__ == '__main__':

    try:
        wristband_listner.start_threads()
        imu_listener.start_threads()
        app.run(debug=True, port=8048, use_reloader=False)
    
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Stopping threads...")

        wristband_listner.stop_threads()
        imu_listener.stop_threads()
        app.stop()
    
        print("Threads stopped.")
        
