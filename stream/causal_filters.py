
import numpy as np
from scipy.signal import butter, lfilter_zi, lfilter
from colorama import Fore, Style
from datetime import datetime
import logging
from ahrs.common import Quaternion
from ahrs.filters import Madgwick
from collections import deque

import numpy as np



def get_signed_rotation_angle(q1, q2):
    # Normalize quaternions
    q1 = q1 / np.linalg.norm(q1)
    q2 = q2 / np.linalg.norm(q2)
    
    # Calculate relative rotation
    q1_inv = np.array([q1[0], -q1[1], -q1[2], -q1[3]])
    q_rel = quaternion_multiply(q2, q1_inv)
    
    # Get the angle
    angle = 2 * np.arccos(np.clip(q_rel[0], -1.0, 1.0))  # Remove abs()
    angle_deg = np.degrees(angle)
    
    # Determine the sign based on the imaginary components
    # If the dot product of the rotation axis with a reference axis (e.g., up vector)
    # is negative, we're rotating in the negative direction
    rotation_axis = q_rel[1:4]  # imaginary components represent rotation axis
    if np.linalg.norm(rotation_axis) > 0:
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
        # You might need to adjust this reference axis based on your coordinate system
        reference_axis = np.array([0, 1, 0])  # Using Y-axis as reference
        sign = 1 if np.dot(rotation_axis, reference_axis) >= 0 else -1
        angle_deg *= sign
    
    return -angle_deg


def get_rotation_angle(q1, q2):
    # Ensure quaternions are normalized
    q1 = q1 / np.linalg.norm(q1)
    q2 = q2 / np.linalg.norm(q2)
    
    # Calculate the relative rotation quaternion
    # q_rel = q2 * q1^(-1)
    q1_inv = np.array([q1[0], -q1[1], -q1[2], -q1[3]])  # Conjugate of unit quaternion is its inverse
    q_rel = quaternion_multiply(q2, q1_inv)
    
    # Extract the angle from the relative quaternion
    # angle = 2 * arccos(q_w)  where q_w is the real part of the quaternion
    angle = 2 * np.arccos(np.clip(abs(q_rel[0]), -1.0, 1.0))
    
    # Convert to degrees
    angle_deg = np.degrees(angle)
    
    return angle_deg

def quaternion_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    
    return np.array([w, x, y, z])

class FirstOrderHighPassFilter:
    def __init__(self, cutoff_frequency, sampling_rate, num_channels=1):
        """
        Initialize a first-order high-pass filter for multi-channel data.

        Args:
            cutoff_frequency (float): Cutoff frequency in Hz.
            sampling_rate (float): Sampling rate in Hz.
            num_channels (int): Number of channels (default is 1).
        """
        self.cutoff_frequency = cutoff_frequency
        self.sampling_rate = sampling_rate
        self.num_channels = num_channels

        # Compute the RC constant
        self.rc = 1 / (2 * np.pi * self.cutoff_frequency)
        self.dt = 1 / self.sampling_rate
        self.alpha = self.dt / (self.rc + self.dt)

        # Initialize previous values for each channel
        self.prev_x = [0.0] * self.num_channels
        self.prev_y = [0.0] * self.num_channels

    def apply(self, x):
        """
        Apply the first-order high-pass filter to a single multi-channel sample.

        Args:
            x (list of float): Input sample for all channels.

        Returns:
            list of float: Filtered output sample for all channels.
        """
        filtered_output = []
        for channel in range(self.num_channels):
            y = self.alpha * (self.prev_y[channel] + x[channel] - self.prev_x[channel])
            self.prev_x[channel] = x[channel]
            self.prev_y[channel] = y
            filtered_output.append(y)
        return filtered_output

    def apply_batch(self, batch):
        """
        Apply the first-order high-pass filter to a batch of multi-channel samples.

        Args:
            batch (list of list of float): List of samples for each channel (shape: [num_samples, num_channels]).

        Returns:
            list of list of float: Filtered output samples for each channel (same shape as input).
        """
        batch = np.array(batch)
        result = []
        for i in range(batch.shape[0]):
            result.append(self.apply(batch[i]))
        return result

class RotationFilter:
    def __init__(self, track_rotation_index = 8, start_rotation_index=5, end_rotation_index = 6, probability_threshold = 0.95, inference_interval = 0.01, max_rotation_time = 2, sampling_frequency = 112.2):
        self.track_rotation_index = track_rotation_index
        self.start_rotation_index = start_rotation_index
        self.end_rotation_index = end_rotation_index
        self.rotation_threshold = probability_threshold
        self.max_rotation_time = max_rotation_time
        self.last_orientation = None
        self.currently_rotating_counter = 0
        self.inference_interval = inference_interval
        self.sampling_frequency = sampling_frequency
        self.running_average_prob = None
        
    def update(self, probabilities, current_orientation):
    
        
        if self.running_average_prob is None:
            self.running_average_prob = probabilities
        else:
            self.running_average_prob = 0.7 * self.running_average_prob + 0.3 * probabilities
        
        start_rotation_prob = self.running_average_prob[self.start_rotation_index]
        end_rotation_prob = self.running_average_prob[self.end_rotation_index]
        rotation_prob = self.running_average_prob[self.track_rotation_index]
        
        if self.currently_rotating_counter == 0 and self.rotation_threshold < start_rotation_prob:
            #print("Started rotation")
            self.currently_rotating_counter += 1
            self.last_orientation = Quaternion(current_orientation)
            
            
        elif self.currently_rotating_counter > 0:
            # While in rotation mode
            #delta_rotation = Quaternion(current_orientation).product(self.last_orientation.conjugate)
            #delta_rotation = Quaternion(delta_rotation).to_angles()[0] * 180/np.pi
            #delta_rotation = Quaternion(current_orientation - self.last_orientation).normalize().to_axang()[1] * 180/np.pi
            delta_rotation = get_signed_rotation_angle(self.last_orientation, current_orientation)
            delta_rotation = (self.last_orientation.to_angles() - Quaternion(current_orientation).to_angles())[0] *180 / np.pi
            delta_rotation = (delta_rotation + 180) % 360 - 180
            #delta_rotation = Quaternion(delta_rotation).to_angles()[2] * 180/np.pi
            #print(f"Delta Rotation: {delta_rotation}")
            
            if self.rotation_threshold < end_rotation_prob or self.currently_rotating_counter > self.max_rotation_time/self.inference_interval:
                # stop rotation
                #print("Stopped rotation")
                self.currently_rotating_counter = 0
                self.last_orientation = None
            else:
                # continue rotation
                self.currently_rotating_counter += 1
                self.last_orientation = Quaternion(current_orientation)
                
            
            return -delta_rotation
    
       


                


    def _print_rotation(self, rotation):
        print(f"Rotation: {rotation}")
        
        


class HighPassFilter:
    def __init__(self, cutoff_frequency, sampling_rate, order=2, num_channels=3):
        """
        Initialize the high-pass filter with Butterworth coefficients for multi-channel data.
        
        Args:
            cutoff_frequency (float): Cutoff frequency in Hz.
            sampling_rate (float): Sampling rate in Hz.
            order (int): Filter order (default is 2).
            num_channels (int): Number of channels (default is 1).
        """
        self.cutoff_frequency = cutoff_frequency
        self.sampling_rate = sampling_rate
        self.order = order
        self.num_channels = num_channels

        # Compute filter coefficients
        self.b, self.a = butter(
            self.order, 
            self.cutoff_frequency, 
            btype='highpass', 
            analog=False,
            fs=self.sampling_rate
        )

        # Initialize filter states for each channel
        self.z = lfilter_zi(self.b, self.a).reshape(-1,1).repeat(self.num_channels, axis=1)

    def apply(self, x):
        """
        Apply the high-pass filter to a single multi-channel sample.

        Args:
            x (list of float): Input sample for all channels.

        Returns:
            list of float: Filtered output sample for all channels.
        """
        #print(x.shape, self.z.shape)
        y, self.z = lfilter(self.b, self.a,np.atleast_2d(x), zi=self.z, axis=0)
        return y

   

class MadgwickRotationFilter:

    def __init__(self, sampling_frequency=112.2, history_size=600, filter_gyro = False, gain_imu=0.033):
        self.sampling_frequency = sampling_frequency
        self.gain_imu = gain_imu
        self.rotation_history = deque(maxlen=history_size)  # Fixed-size queue for rotation history
        self.current_rotation = None
        if filter_gyro:
            self.filter_gyro = HighPassFilter(cutoff_frequency=0.5, sampling_rate=sampling_frequency, order=2)
        
        

    def update_imu_values(self, imu_values):
        if self.current_rotation is None:
            acc, gyro = imu_values[:,:3], imu_values[:,3:]
            self.filter = Madgwick(gyr=gyro, acc=acc, frequency=self.sampling_frequency, gain_imu=self.gain_imu)
            self.rotation_history.extend(self.filter.Q)
            self.current_rotation = self.filter.Q[-1]
        for sample in imu_values:
            if len(sample) == 6:
                
                acc, gyro = sample[:3], sample[3:]
                
                if hasattr(self, "filter_gyro"):
                    gyro = self.filter_gyro.apply(gyro).squeeze()
                
                rotation = self.filter.updateIMU(q = self.current_rotation, acc = acc, gyr = gyro/180*np.pi)
                self.rotation_history.append(rotation.copy())  # Save current orientation
                self.current_rotation = rotation
                #print(f"Updated Rotation: {np.round(Quaternion(self.current_rotation).to_angles()/np.pi*180,0)}")
                #print(f"Updated Rotation: {self.current_rotation}")
            else:
                print(f"Invalid IMU sample length", len(sample), imu_values.shape)
                
        #print(f"Rotation: {self.current_rotation}")

    def get_current_rotation(self):
        return self.current_rotation

    def get_rotation_history(self):
        #print(np.array(self.rotation_history).shape)
        #print(f"Rotation history: {len(self.rotation_history)}")
        
        return list(self.rotation_history)  # Return history as a list for easier manipulation


class PredictionFilter:
    def __init__(self, n_classes=7, log_to_file=False, gesture_prediction_len_threshold = 1, label_to_gesture = None):
        self.current_gesture = 0
        self.current_gesture_length = 0
        self.current_certainty = 0
        self.current_max_certainty = 0
        self.gesture_prediction_len_threshold = gesture_prediction_len_threshold
        self.current_probabilities = np.zeros(n_classes)
        self.log_to_file = log_to_file  # Option to log to a file
        if label_to_gesture is None:
            self.label_to_gesture = lambda x: x
        else:
            self.label_to_gesture = label_to_gesture

    
    def update(self, probabilities):
        gesture = np.argmax(probabilities)
        certainty = probabilities[gesture]

        if gesture == self.current_gesture and certainty > self.current_certainty:
            self.current_max_certainty = certainty
        
        if gesture != self.current_gesture:
            if self.current_gesture_length >= self.gesture_prediction_len_threshold:
                self.print_prediction(self.current_gesture, self.current_max_certainty)
                self.current_gesture_length = 0
                return gesture
            else:
                self.current_gesture_length = 0
        else:
            self.current_gesture_length += 1

        self.current_gesture = gesture
        self.current_certainty = certainty
        self.current_probabilities = probabilities
        
        return 0
    
    def print_prediction(self, gesture, certainty, threshold = 0.5):
        if certainty > threshold and gesture != 0:
            # Prepare the message
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = (
                f"{Fore.CYAN}[{time}]{Style.RESET_ALL} "
                f"{Fore.GREEN}Gesture: {self.label_to_gesture[gesture]}{Style.RESET_ALL}, "
                f"Certainty: {Fore.YELLOW}{certainty * 100:.1f}%{Style.RESET_ALL}"
            )
            # Print to console
            print("=" * 40)
            print(message)
            print("=" * 40)

            # Log to file if enabled
            if self.log_to_file:
                logging.info(f"Gesture: {self.label_to_gesture[gesture]}, Certainty: {certainty * 100:.1f}%")
    
