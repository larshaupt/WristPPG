from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import random
import time
from threading import Thread
import dash_bootstrap_components as dbc

# Create the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Global variables to store the latest PPG and IMU values
ppg_value = 0
imu_value = 0

# Mock function to read PPG data
def read_ppg():
    return random.uniform(50, 100)

# Mock function to read IMU data
def read_imu():
    return random.uniform(0, 360)  # Simulate IMU data (e.g., orientation in degrees)

# Function to continuously update the PPG value
def update_ppg():
    global ppg_value
    while True:
        ppg_value = read_ppg()
        time.sleep(1)  # Simulate delay between reads

# Function to continuously update the IMU value
def update_imu():
    global imu_value
    while True:
        imu_value = read_imu()
        time.sleep(1)  # Simulate delay between reads

# Layout of the Dash app
app.layout = html.Div([
    html.H1("Real-time PPG and IMU Plot"),
    dcc.Graph(id='live-graph', animate=True),
    dcc.Interval(
        id='graph-update',
        interval=2000,  # Update every 2 seconds for better performance
        n_intervals=0  # Number of interval events that have triggered
    ),
])

# Initialize time and data lists
time_vals = []
ppg_vals = []
imu_vals = []

# Callback to update the graph with the latest PPG and IMU values
@app.callback(
    Output('live-graph', 'figure'),
    [Input('graph-update', 'n_intervals')]
)
def update_graph_live(n):
    global ppg_value, imu_value

    # Update time and values
    current_time = len(time_vals)  # Use current length as time
    time_vals.append(current_time)
    ppg_vals.append(ppg_value)
    imu_vals.append(imu_value)

    # Keep only the last 100 data points to avoid performance issues
    if len(time_vals) > 100:
        time_vals.pop(0)
        ppg_vals.pop(0)
        imu_vals.pop(0)

    # Create traces for PPG and IMU
    ppg_data = go.Scatter(
        x=list(time_vals),
        y=list(ppg_vals),
        mode='lines',
        name='PPG Value'
    )

    imu_data = go.Scatter(
        x=list(time_vals),
        y=list(imu_vals),
        mode='lines',
        name='IMU Value',
        yaxis='y2'  # Use a secondary y-axis for IMU
    )

    layout = go.Layout(
        xaxis=dict(title='Time (s)'),
        yaxis=dict(title='PPG Value'),
        yaxis2=dict(title='IMU Value', overlaying='y', side='right'),
        margin={'l': 40, 'r': 40, 't': 50, 'b': 40},
        hovermode='closest'
    )

    return {'data': [ppg_data, imu_data], 'layout': layout}

# Start the PPG and IMU update threads
ppg_thread = Thread(target=update_ppg)
imu_thread = Thread(target=update_imu)
ppg_thread.daemon = True
imu_thread.daemon = True
ppg_thread.start()
imu_thread.start()

if __name__ == '__main__':
    app.run_server(debug=True)
