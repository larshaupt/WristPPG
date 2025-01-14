import cv2
import threading
import time

class WebcamStreamer:
    def __init__(self, output_filename='output.avi', codec='MJPG', fps=30, resolution=(640, 480), start_streaming=True):
        self.output_filename = output_filename
        self.codec = codec
        self.fps = fps
        self.resolution = resolution
        self.cap = cv2.VideoCapture(0)
        self.out = None
        self.recording = False
        self.streaming = False  # Initial state is not streaming
        self.start_time = None
        self.end_time = None
        self.overlay_text = ""
        self.text_position = (10, 30)
        self.text_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_color = (0, 255, 0)
        self.text_thickness = 2

        # Open the webcam
        if not self.cap.isOpened():
            raise Exception("Error: Could not open the webcam.")

        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        print("Webcam initialized. Ready to start streaming.")

        # Start streaming automatically if requested
        if start_streaming:
            self.start_streaming()

    def start_streaming(self):
        """Starts the webcam stream and displays the feed."""
        if self.streaming:
            print("Already streaming.")
            return
        
        self.streaming = True
        self.streaming_thread = threading.Thread(target=self._stream_live_feed, daemon=True)
        self.streaming_thread.start()
        #print("Webcam live feed started.")

    def _stream_live_feed(self):
        """Stream the live webcam feed without recording."""
        while self.streaming:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break
            
            # Overlay text if any
            if self.overlay_text:
                cv2.putText(frame, self.overlay_text, self.text_position, self.text_font,
                            1, self.text_color, self.text_thickness, cv2.LINE_AA)
            
            if self.recording:
                self.out.write(frame)
            
            # Display the frame in a window
            cv2.imshow('Webcam Live Feed', frame)

            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == 27:
                self.stop_recording()
                self.stop_streaming()
                break

        cv2.destroyWindow('Webcam Live Feed')

    def stop_streaming(self):
        """Stops the live streaming and closes the webcam feed window."""
        if self.streaming:
            self.streaming = False
            print("Webcam live feed stopped.")


    def start_recording(self):
        if not self.cap.isOpened():
            raise Exception("Error: Webcam is not initialized.")

        # Stop streaming before recording
        #self.streaming = False
        #self.streaming_thread.join()

        # Define the codec and create a VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.out = cv2.VideoWriter(self.output_filename, fourcc, self.fps, self.resolution)
        self.recording = True

        # Save the start time
        self.start_time = time.time()
        print(f"Recording started at {self.start_time}. Press 'q' to stop.")


    def stop_recording(self):
        if self.recording:
            self.recording = False
            # Save the end time
            self.end_time = time.time()
            print(f"Recording stopped at {self.end_time}. Video saved to {self.output_filename}.")
            #print(f"Duration: {self.end_time - self.start_time}.")

            # Release resources
            if self.out:
                self.out.release()

    def release_camera(self):
        """Releases the webcam when it's no longer needed."""
        self.streaming = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        print("Webcam released.")

    def display_text(self, text, position=(10, 30), color=(0, 255, 0), thickness=2):
        """Updates the text to overlay on the video."""
        self.overlay_text = text
        self.text_position = position
        self.text_color = color
        self.text_thickness = thickness

    def save_timestamps(self, filename=None):
        """Saves the start and end timestamps to a file."""
        if not filename:
            filename_ending = "." + self.output_filename.split('.')[-1]
            filename = self.output_filename.replace(filename_ending, '_timestamps.txt')
        
        if self.start_time and self.end_time:
            with open(filename, 'w') as f:
                f.write(f"Recording Start Time: {self.start_time}\n")
                f.write(f"Recording End Time: {self.end_time}\n")
                f.write(f"Duration: {self.end_time - self.start_time}\n")
            print(f"Timestamps saved to {filename}.")
        else:
            print("Error: Recording timestamps are not available.")

if __name__ == "__main__":
    # Example usage
    streamer = WebcamStreamer(output_filename='my_recording.avi', resolution=(1280, 720), start_streaming=True)
    try:
        streamer.display_text("Live Feed! Press 'q' to stop viewing.", position=(50, 50))
        input("Press Enter to start recording...")
        streamer.start_recording()
        streamer.save_timestamps()
    except Exception as e:
        print(e)
    finally:
        streamer.release_camera()
