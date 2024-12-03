import os
# to prevent forrtl: error (200): program aborting due to control-C event
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

from PPG.wristband_listener import *
from IMU.BluetoothIMU import BluetoothIMUReader

import asyncio
import numpy as np
import dash
from dash import Dash, dcc, html, Input, Output, callback
import dash_daq as daq
import plotly
import plotly.graph_objs as go
import plotly.subplots
import argparse
import signal
from scipy.signal import butter, lfilter, lfilter_zi

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

# no idea where these numbers come from
ppg_max = [1600, 1200, 400, 1400, 8000, 4000, 6000, 2000,
            8000, 4000, 6000, 2000, 4000, 2000, 3000, 800,
            8000, 4000, 6000, 2000, 4000, 2000, 3000, 800,
            8000, 4000, 6000, 2000, 4000, 2000, 3000, 800,]

ppg_min = [-2000, -1400, -500, -1400, -6000, -4000, -8000, -3000,
            -6000, -4000, -8000, -3000, -3000, -2000, -4000, -1400,
            -6000, -4000, -8000, -3000, -3000, -2000, -4000, -1400,
            -6000, -4000, -8000, -3000, -3000, -2000, -4000, -1400]

class LiveFigure:
    def __init__(self, height=800, width=1900, wlen=128, n_ppg_channels=16):
        self.wlen = wlen
        self.n_ppg_channels = n_ppg_channels

        # channel offsets
        self.green_offsets = [0 for _ in range(8)]
        self.ir_offsets = [0 for _ in range(8)]

        self.fig = plotly.subplots.make_subplots(
            rows=8, cols=8,
            specs= [[{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None , None],
                ],
            print_grid=True, 
            column_titles=["green", "IR", "Red"],
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
            
        for ch in range(8): # RED
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], name=f"channel_{ch+1}", line=dict(color='black'), showlegend=False), 
                                row=ch+1, col=5, secondary_y=False)
            self.fig.update_yaxes(title_text=f"ch {ch+1}", row=ch+1, col=5, title_standoff=0)

        self.fig.update_layout(yaxis=dict(autorangeoptions=dict(clipmax=1e6)))

        self.mins = [0 for _ in range(24)]
        self.maxs = [1e5 for _ in range(24)]
        self.alpha = 0.9

        ## accelerometer
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Example: blue, orange, green for x,y,z
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i],showlegend=True, line=dict(color=colors[i])), row=3, col=7)
        self.fig.update_yaxes(title_text=f"PPG Accelerometer", row=3, col=7, range=([-20, 20]))
        
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i], showlegend=False,line=dict(color=colors[i])), row=5, col=7)
        self.fig.update_yaxes(title_text=f"IMU Accelerometer", row=5, col=7, range=([-20, 20]))
        
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i], showlegend=False,line=dict(color=colors[i])), row=7, col=7)
        self.fig.update_yaxes(title_text=f"IMU Gyroscope", row=7, col=7, range = [-512, 512])

    def _update_ppg_plots(self, input_data):
        # update the y axes maxs and mins
        for ch in range(self.n_ppg_channels):
            if len(input_data[ch]) == 0:
                continue
            min = np.percentile(input_data[ch], 5) * 0.9
            max = np.percentile(input_data[ch], 95) * 1.1
            self.mins[ch] = self.mins[ch] * self.alpha + min * (1 - self.alpha)
            self.maxs[ch] = self.maxs[ch] * self.alpha + max * (1 - self.alpha)

        for i in range(self.n_ppg_channels//8):
            for ch in range(8):
                self.fig['data'][ch + i*8]['y'] = np.array(input_data[ch + i*8])
                self.fig.update_yaxes(row=ch+1, col=1 + i*2, range=[self.mins[ch + i*8], self.maxs[ch + i*8]])


    def _update_ppg_imu_plots(self, input_data):
        # Ensure input_data has data for accelerometer and gyroscope
        #print(input_data[self.n_ppg_channels:self.n_ppg_channels+3])
        if input_data is not None:
            for ch in range(3):  # Assuming input_data[16:19] are accelerometer values
                self.fig['data'][16 + 8 + ch]['y'] = np.array(input_data[self.n_ppg_channels+ch])  # Accelerometer
            #self.fig.update_yaxes(row=3, col=5, range=[-20, 20])

    def update_imu_plots(self, input_data):
        #print(len(input_data[0]))
        # Ensure input_data has data for accelerometer and gyroscope
        if input_data is not None:
            
            # Update IMU accelerometer plots
            for ch in range(3):  # x, y, z axes
                self.fig['data'][ch+19+ 8]['y'] = np.array(input_data[ch]) 
            #self.fig.update_yaxes(row=5, col=5, range=[-20, 20])
            
            # Update PPG gyroscope plots
            for ch in range(3):  # x, y, z axes
                self.fig['data'][ch+22+ 8]['y'] = np.array(input_data[3+ch])  
            #self.fig.update_yaxes(row=7, col=5, range=[-512, 512])
            
            # You can similarly add more plots if needed, e.g., for IMU gyroscope data


    def _scale_ppg(self, input_data):
        # min max scale
        assert len(input_data) <= len(ppg_max) == len(ppg_min), f"input_data: {len(input_data)}, ppg_max: {len(ppg_max)}, ppg_min: {len(ppg_min)}"
        scaled_data = [(input_data[i] - ppg_min[i]) / (ppg_max[i] - ppg_min[i]) for i in range(self.n_ppg_channels)]
        return scaled_data

    def update_ppg_plots(self, input_data_ppg):
        #print([len(input_data_ppg[i]) for i in range(len(input_data_ppg))])
        #filtered_ppg = [filter_ppg(input_data_ppg[i]) for i in range(self.n_ppg_channels)] 
        #filtered_ppg = self._scale_ppg(filtered_ppg)
        #print([len(filtered_ppg[i]) for i in range(len(filtered_ppg))])
        #self._update_ppg_plots(filtered_ppg)
        self._update_ppg_imu_plots(input_data_ppg)


def filter_ppg(input_signal):
    
    if len(input_signal) == 0:
        return input_signal
    
    input_signal = np.array(input_signal)
    nans, x = np.isnan(input_signal), lambda z: z.nonzero()[0]
    input_signal[nans] = np.interp(x(nans), x(~nans), input_signal[~nans])

    b, a = butter(5, [0.1, 63.5], fs=128, btype='band')
    zi = lfilter_zi(b, a) * input_signal[0]
    filtered_signal = lfilter(b, a, input_signal, zi=zi)[0]
    return filtered_signal

live_figure = LiveFigure(wlen=WLEN*max(FRAME_RATE_PPG, FRAME_RATE_IMU), n_ppg_channels=N_PPG_CHANNELS)
wristband_listner = WristbandListener(n_ppg_channels=N_PPG_CHANNELS, window_size=WLEN, csv_window=2,
                                     frame_rate=FRAME_RATE_PPG, fileindex=args.file_index, bracelet=args.sensor_size)
imu_listener = BluetoothIMUReader(port = 'COM13', baud_rate=115200, file_index=args.file_index, frame_rate=FRAME_RATE_IMU)


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

    # Define a handler function
    def signal_handler(sig, frame):
        print("Keyboard interrupt received. Stopping threads...")
        imu_listener.stop_threads()
        wristband_listner.stop_threads()
        print("Threads stopped.")
        exit(0)
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)


    
    wristband_listner.start_threads()
    imu_listener.start_threads()
    app.run(debug=True, port=8048, use_reloader=False)
        

    
    #except KeyboardInterrupt:
    #    print("Keyboard interrupt received. Stopping threads...")
    #
    #    wristband_listner.stop_threads()
    #    imu_listener.stop_threads()
    #    app.stop()
    #    
    #
    #    print("Threads stopped.")
        
