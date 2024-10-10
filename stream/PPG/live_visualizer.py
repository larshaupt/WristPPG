from wristband_listener import *

import multiprocessing
import threading
import asyncio
import numpy as np
import sys
import dash
from dash import Dash, dcc, html, Input, Output, callback
from dash.dependencies import Output, Input
import dash_daq as daq
import plotly
import plotly.graph_objs as go
import os
import plotly.subplots
import argparse

from globalspline import GlobalSpline2D

import scipy.interpolate as si
from scipy import stats

import nest_asyncio
nest_asyncio.apply()

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
    def __init__(self, height=800, width=1600, wlen=128, n_ppg_channels=16, 
                 heatmap_size=64, draw_hand=False):
        
        # headmap range
        self.green_max = 1.5
        self.ir_max = 1.5
        self.heatmap_size = heatmap_size

        self.wlen = wlen

        # channel offsets
        self.green_offsets = [0 for _ in range(8)]
        self.ir_offsets = [0 for _ in range(8)]

        self.fig = plotly.subplots.make_subplots(
            rows=8, cols=6,
            # shared_xaxes=True,
            specs= [[{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan":4, "colspan":2, "type":"surface"}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2}, {"rowspan": 2}],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, {"rowspan": 2, "colspan":2}, None],
                    [{"secondary_y": True, "colspan":2}, None, {"secondary_y": True, "colspan":2}, None, None, None],
                ],
            print_grid=True, 
            column_titles=["green", "IR"],
            )
    
        # update figure size
        self.fig.update_layout(height=height, width=width)

        # ppgs
        for ch in range(8): # green
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], name=f"channel_{ch+1}", line=dict(color='black')), 
                            row=ch+1, col=1, secondary_y=False)
            self.fig.update_yaxes(title_text=f"ch {ch+1}", row=ch+1, col=1, title_standoff=0)
            # self.fig.update_layout(yaxis_range=[0,4], row=ch+1, col=1)

        for ch in range(8): # IR
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], name=f"channel_{ch+1}", line=dict(color='black')), 
                                row=ch+1, col=3, secondary_y=False)
                # fig.update_yaxes(title_text=f"ch {ch+1}", row=ch+1, col=2, title_standoff=0)
            self.fig.update_yaxes(title_text=f"ch {ch+1}", row=ch+1, col=3, title_standoff=0)

        self.fig.update_layout(showlegend=False, yaxis=dict(autorangeoptions=dict(clipmax=1e6)))

        self.mins = [0 for _ in range(16)]
        self.maxs = [1e5 for _ in range(16)]
        self.alpha = 0.9

        ## heatmaps
        self._init_heatmaps()

        ## accelerometer
        acc_axes = ['x', 'y', 'z']
        for i in range(3):
            self.fig.add_trace(go.Scatter(x=np.arange(self.wlen), y=[0], mode='lines', name=acc_axes[i]), row=7, col=5)
        self.fig.update_yaxes(title_text=f"accelerometer", row=7, col=5)

        ## hand

    def _init_heatmaps(self):   
        z_zero = np.zeros((self.heatmap_size, self.heatmap_size))

        theta = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        circle_grid_coords = ((np.array([np.cos(theta), np.sin(theta)]).T + 1) 
                                      * (self.heatmap_size-1) / 2).astype(int)
        # self.pd_pos_dict = {
        #     0: [2, 5],
        #     1: [3, 3],
        #     2: [5, 2],
        #     3: [7, 3],
        #     4: [8, 5],
        #     5: [7, 7],
        #     6: [5, 8],
        #     7: [3, 7]
        # }

        # spatial label of each channel
        text = [['' for _ in range(self.heatmap_size)] for _ in range(self.heatmap_size)]
        for i, pos in enumerate(circle_grid_coords):
            text[pos[0]][pos[1]] = str(i+1)

        # for the green
        self.fig.add_trace(go.Heatmap(
                            z=z_zero,
                            text=text,
                            texttemplate="%{text}",
                            textfont={"size":16},
                            colorscale='Viridis',
                            coloraxis='coloraxis1',
                            ), 
                            row=5, col=5)
        # for the IR
        self.fig.add_trace(go.Heatmap(
                            z=z_zero,
                            text=text,
                            texttemplate="%{text}",
                            textfont={"size":16},
                            colorscale='Viridis',
                            coloraxis='coloraxis2'
                            ), 
                            row=5, col=6)

        # colorbar scale
        self.fig.update_layout(coloraxis1=dict(colorscale='Viridis', cmin=0, cmax=self.green_max, 
                                        colorbar=dict(len=1./4.2, y=0.365, x=0.78, thickness=16, 
                                                        # ticklabelposition='inside',
                                                        ticksuffix='     ',
                                                        ticklabeloverflow='allow',
                                                        tickfont_color='darkslategrey',)),
                        coloraxis2=dict(colorscale='Viridis', cmin=0, cmax=self.ir_max, 
                                        colorbar=dict(len=1./4.2, y=0.365, x=0.945, thickness=16)),
                        showlegend=False, 
        )

    def _interpolate_heatmap_bicubic(self, input_list):
        '''
        input_list: list of n_channel (8) values
        '''
        x_y = list(self.pd_pos_dict.values())
        x_y = list(zip(*x_y))

        # sort both x and y in ascending order of x
        # x, y, v = zip(*sorted(zip(x_y[0], x_y[1], input_list)))

        # interp = si.RegularGridInterpolator((x, y), v, 
        #                                     method='linear', bounds_error=False, fill_value=None)
        
        interp = GlobalSpline2D(x_y[0], x_y[1], input_list, degree=3)
        z = interp(np.arange(self.heatmap_size), np.arange(self.heatmap_size))
        z = z.T

        return z
    
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
            

    def _update_heatmaps_old(self, input_data):
        heatmap_data = [np.abs(np.array(input_data[i])).mean() for i in range(16)]

        # heatmap for green led
        z_g = self._interpolate_heatmap_bicubic(heatmap_data[:8])
        self.fig['data'][16]['z'] = z_g

        # heatmap for IR led
        z_ir = self._interpolate_heatmap_bicubic(heatmap_data[8:])
        self.fig['data'][17]['z'] = z_ir

    def _update_heatmaps(self, input_data):
        heatmap_data = [np.abs(input_data[i][-1]) for i in range(16)]
        # heatmap_data = [stats.zscore(np.array(input_data[i]), nan_policy='omit')[-1] for i in range(16)]

        z_g = self._update_a_heatmap(heatmap_data[:8])
        z_ir = self._update_a_heatmap(heatmap_data[8:])
        self.fig['data'][16]['z'] = z_g
        self.fig['data'][17]['z'] = z_ir

    def _update_a_heatmap(self, values):

        theta = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        circle_points = np.array([np.cos(theta), np.sin(theta)]).T

        # Grid for interpolation
        grid_x, grid_y = np.meshgrid(np.linspace(-1, 1, self.heatmap_size), np.linspace(-1, 1, self.heatmap_size))
        grid_points = np.vstack([grid_x.ravel(), grid_y.ravel()]).T

        # Interpolate values
        interpolated_values = si.griddata(circle_points, values, grid_points, method='cubic')

        # # Mask out points outside the circle
        # mask = np.sqrt(grid_x**2 + grid_y**2) > 1
        # interpolated_values[mask.ravel()] = np.nan

        interpolated_values = interpolated_values.reshape((self.heatmap_size, self.heatmap_size))

        return interpolated_values
    
    def _update_a_heatmap_rbf(self, values):

        theta = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        circle_points = np.array([np.cos(theta), np.sin(theta)])

        grid_x, grid_y = np.meshgrid(np.linspace(-1, 1, self.heatmap_size), np.linspace(-1, 1, self.heatmap_size))

        rbf = si.Rbf(circle_points[0], circle_points[1], values, function='cubic')
        interpolated_values = rbf(grid_x, grid_y)

        interpolated_values = interpolated_values.reshape((self.heatmap_size, self.heatmap_size))

        return interpolated_values
    
    def _update_imu_plots(self, input_data):
        for ch in range(3):
            self.fig['data'][ch+18]['y'] = np.array(input_data[ch])

    def _scale_ppg(self, input_data):
           
        # min max scale
        ppg_scale = [ppg_max[i] - ppg_min[i] for i in range(16)]
        
        scaled_data = [(input_data[i] - ppg_min[i]) / ppg_scale[i] for i in range(8)]
        scaled_data += [(input_data[i] - ppg_min[i]) / ppg_scale[i] for i in range(8, 16)]

        return scaled_data

    def update_plots(self, input_data):
        filtered_ppg = [filter_ppg(input_data[i]) for i in range(16)] 
        filtered_ppg = self._scale_ppg(filtered_ppg)
        self._update_ppg_plots(input_data)
        self._update_heatmaps(filtered_ppg)
        self._update_imu_plots(input_data[16:])

class HandVisualizer:
    def __init__(self) -> None:
        pass
        
def filter_ppg(input_signal):
    # filtered_signal = stats.zscore(input_signal, nan_policy='omit')
    # butterworth filter

    # replace NaNs by interpolation
    input_signal = np.array(input_signal)
    nans, x = np.isnan(input_signal), lambda z: z.nonzero()[0]
    input_signal[nans] = np.interp(x(nans), x(~nans), input_signal[~nans])

    b, a = butter(5, [0.1, 63.5], fs=128, btype='band')
    # b, a = butter(3, 0.05, btype='low')
    zi = lfilter_zi(b, a) * input_signal[0]

    filtered_signal = lfilter(b, a, input_signal, zi=zi)[0]

    return filtered_signal

live_figure = LiveFigure(wlen=WLEN*FRAME_RATE, n_ppg_channels=N_PPG_CHANNELS)
wristband_listner = WristbandListener(n_ppg_channels=N_PPG_CHANNELS, window_size=WLEN, csv_window=2,
                                      frame_rate=FRAME_RATE, fileindex=args.file_index, bracelet=args.sensor_size)

def calibrate_min_max():
    live_figure.green_min = 0
    live_figure.green_max = 1e5
    live_figure.ir_min = 0
    live_figure.ir_max = 1.5e5

#%% DASH APP
app = Dash(__name__)
app.assets_ignore = '.*'
# app.config.suppress_callback_exceptions = True

app.layout = html.Div(
    [    
        daq.BooleanSwitch(
                id='record-switch',
                # color='green',
                on=False,
                label="record",
                style={'display': 'inline-block', 'margin-left': '5px'},
        ),
        html.Div(id='recording-switch-output'),

        # daq.BooleanSwitch(
        #         id='calibrate-switch',
        #         # color='blue',
        #         on=False,
        #         label="calibrate",
        #         style={'display': 'inline-block', 'margin-left': '5px'},
        #         ),
        # html.Div(id='calibrate-switch-output'),

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
    return ''

# @app.callback(
#     Output('calibrate-switch-output', 'children'),
#     Input('calibrate-switch', 'on')
# )
# def update_switch2(on):
#     global calibration_status
#     calibration_status = on
#     return ''

@app.callback(
    Output('live-graph', 'figure'),
    [ Input('graph-update', 'n_intervals') ],
    [dash.dependencies.State('live-graph', 'figure')]
)
def update_graph_live(n_intervals, existing_fig):
    global live_figure, wristband_listner

    if len(wristband_listner.data_buffer.plotting_queues()[0]) == 0:
        return live_figure.fig
    
    live_figure.update_plots(wristband_listner.data_buffer.plotting_queues())

    return live_figure.fig

def start_background_process():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(wristband_listner.connect_and_stream())

#%% main
if __name__ == '__main__':

    try:
        wristband_listner.start_threads()
        app.run(debug=True, port=8048, use_reloader=False)
    
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Stopping threads...")

        wristband_listner.stop_threads()
        app.stop()
    
        print("Threads stopped.")
    
