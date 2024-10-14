import tkinter as tk
from tkinter import ttk
import random
import time
from tkinter import simpledialog, messagebox
import csv
import os, sys

SAVE_PATH = r"C:\Users\lhauptmann\Code\WristPPG2\data\labels"
GESTURE_TIME_MAX = 1.0
GESTURE_TIME_MIN = 1.4

LETTER_GESTURES = {
    "a": "Swipe Forward\n⬆️",
    "b": "Swipe Backward\n⬇️",
    "c": "Swipe Left\n⬅️",
    "d": "Swipe Right\n➡️",
    "p": "Pinch Tap\n🤏",
    "prr": "Rotate Right\n🔄 ➡️",
    "prl": "Rotate Left\n🔄 ⬅️",
    "pbd": "Rotate Back\n🔄",
    "pc": "Pinch Hold\n🤏👊",
    "po": "Pinch Open\n🖐️",
    "sp": "Side Pinch\n👌",
    "o": "Nothing\n❌",
    "s": "Knock\n👊"
}



def create_gesture_sequence():
    input_set = [['a']]*15 + [['b']]*15 + [['c']]*15 + [['d']]*15 + [["p"]] * 15 + [["sp"]] * 15 + [["pc", "po"]] * 15  + [["o"]] * 15
    random.shuffle(input_set)
    #expand the list
    input_set = [item for sublist in input_set for item in sublist]
    # adding calibration knocks
    #input_set = ["s"] * 1 + input_set + ["s"] * 1
    return input_set[::-1]

INPUT_SET = create_gesture_sequence()

data_log = []  # To store all letter data for the session

def countdown(seconds):

    if isinstance(seconds, int):
        for i in range(seconds, 0, -1):
            label.config(text=i, font=("Helvetica", 56))
            root.update()
            time.sleep(1)
    elif seconds>1: # seconds is float
        seconds_int = int(seconds)
        
        for i in range(seconds_int, 0, -1):
            label.config(text=i, font=("Helvetica", 56))
            root.update()
            time.sleep(1)
        time.sleep(seconds - seconds_int)
    else: # seconds is samller than 1
        label.config(text="", font=("Helvetica", 56))
        root.update()
        time.sleep(seconds)   
        
        

def show_letter(label, letter):
    gesture = LETTER_GESTURES[letter]
    print(f"Displaying letter: {letter} ({gesture.replace('\n', ' ')})")
    label.config(text=gesture, font=("Helvetica", 96))
    root.update()
    waiting_time = random.uniform(GESTURE_TIME_MIN, GESTURE_TIME_MAX)
    time.sleep(waiting_time)

def init_csv():
    with open(fname, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['start_time', 'end_time', 'label'])    

def write_csv(data_log):
    with open(fname, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data_log)

def start_sequence():
    global data_log
    global letters
    current_time = time.time()
    # Initialize the data log with a start time
    # The start button should be clicked together with knocking
    data_log = [(current_time, current_time, "s")]  
    init_csv()
    total_letters = len(INPUT_SET)
    letters = INPUT_SET.copy() # Reverse the list to pop from the end
    
    progress_bar['maximum'] = total_letters  # Set the progress bar max value
    progress = 0
    countdown(5)
    
    while letters:
        letter = letters.pop()  # Pick a letter from the remaining letters
        start_time = time.time()
        show_letter(label, letter)
        countdown(0.1)
        end_time = time.time()
        data_log.append((start_time, end_time, letter))  # Store in-memory log
        write_csv([data_log[-1]])  # Only write the last recorded data to the CSV

        # Update progress bar
        progress += 1
        progress_bar['value'] = progress
        root.update()


def delete_last(event=None):  # Add event=None to make it compatible with key binding
    global data_log
    if data_log:
        # Remove the last letter from the log
        last_entry = data_log.pop()
        
        # Rewrite the CSV without the last entry
        with open(fname, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['start_time', 'end_time', 'label'])  # Re-write header
            writer.writerows(data_log)  # Re-write all but the last entry
        
        # Update progress bar
        progress_bar['value'] -= 1
        # Add letter back to the list
        letters.append(last_entry[2])
        root.update()
        print("Info", f"Last entry '{last_entry[2]}': {LETTER_GESTURES[last_entry[2]]} deleted.")
    else:
        print("Info", "No more entries to delete.")

try:
    FILEINDEX = int(sys.argv[1])
except:
    print("Please provide a file index")
    sys.exit(1)
fname = os.path.join(SAVE_PATH, f'label_{FILEINDEX:03d}.csv')

# Set up the Tkinter window
root = tk.Tk()
root.title("Countdown & Letter Display")
root.geometry("800x600")

label = tk.Label(root, text="", font=("Helvetica", 48))
label.pack(expand=True)

# Add the progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=10)

# Add the Start button
start_button = tk.Button(root, text="Start", command=start_sequence, font=("Helvetica", 24))
start_button.pack(pady=20)

# Bind the 'Backspace' key to delete the last entry
root.bind("<BackSpace>", delete_last)

# Run the Tkinter event loop
root.mainloop()