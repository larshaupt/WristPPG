import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # Import PIL for image handling
import random
import time
import csv
import os
import sys

SAVE_PATH = r"C:\Users\lhauptmann\Code\WristPPG2\data\labels"
GESTURE_TIME_MAX = 1.0
GESTURE_TIME_MIN = 1.4

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
    "sp": "Side Pinch",
    "o": "Nothing",
    "s": "Knock"
}

LETTER_ICONS = {
    "a": "image",
    "b": "image",
    "c": "image",
    "d": "image",
    "p": "image",
    "prr": "image",
    "prl": "image",
    "pbd": "image",
    "pc": "image",
    "po": "image",
    "sp": "image",
    "o": "❌",
    "s": "👊"
}

# Path to images
IMAGE_PATH = r"C:\Users\lhauptmann\Code\WristPPG2\scripts\images"  # Adjust to your image directory

def create_gesture_sequence():
    input_set = [['a']]*15 + [['b']]*15 + [['c']]*15 + [['d']]*15 + [["p"]] * 15 + [["sp"]] * 15 + [["pc", "po"]] * 5 + [["o"]] * 15 + [["pc", "prr", "po", "o"]] * 5 + [["pc", "prl", "po", "pbd"]] * 5
    test_input = [['a', 'a']] * 8 + [['b', 'b']] * 8 + [['c', 'c']] * 8 + [['d', 'd']] * 8 + [['p', 'p']] * 8 + [['sp', 'sp']] * 8 + [['p','pc', 'po']] * 5 + [['o']] * 16 + [['pc', 'pc', 'prr', 'po']] * 5 + [['pc', 'pc', 'prr', 'po']] * 5
    random.shuffle(input_set)
    return input_set[::-1]

INPUT_SET = create_gesture_sequence()
data_log = []

def countdown(seconds):
    image_label.config(image='', text='')  # Clear image during countdown
    if isinstance(seconds, int):
        for i in range(seconds, 0, -1):
            label.config(text=i, font=("Helvetica", 96))
            root.update()
            time.sleep(1)
    elif seconds > 1:
        seconds_int = int(seconds)
        for i in range(seconds_int, 0, -1):
            label.config(text=i, font=("Helvetica", 96))
            root.update()
            time.sleep(1)
        time.sleep(seconds - seconds_int)
    else:
        label.config(text="", image='')
        root.update()
        time.sleep(seconds)

def show_letter(label, letter):
    gesture = LETTER_GESTURES[letter]
    print(f"Displaying letter: {letter} (",gesture.replace('\n', ' '),")")
    label.config(text=gesture, font=("Helvetica", 96))
    
    icon = LETTER_ICONS[letter]
    
    if isinstance(icon, str) and icon == "image":
        try:
            img_path = os.path.join(IMAGE_PATH, f"{letter}.png")  # Adjust according to your naming convention
            img = Image.open(img_path)
            img = img.resize((200, 200))
            img_tk = ImageTk.PhotoImage(img)
            image_label.config(image=img_tk)
            image_label.image = img_tk  # Keep a reference to avoid garbage collection
        except Exception as e:
            image_label.config(image='')  # Clear image if loading fails
    elif isinstance(icon, list):
        pass
    else:
        image_label.config(text=icon, image='', font=("Helvetica", 96))
    
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
    global data_log, letters, key_pressed
    current_time = time.time()
    data_log = [(current_time, current_time, "s")]  
    init_csv()
    total_letters = len(INPUT_SET)
    letters = INPUT_SET.copy()  
    progress_bar['maximum'] = total_letters  
    progress = 0
    countdown(5)

    temp_log = []  
    gesture_count = 0

    while letters:
        letter = letters.pop()  
        if not isinstance(letter, list):
            letter = [letter]
        for subletter in letter:
            show_letter(label, subletter)
            countdown(0.1)
            entry = (time.time(), time.time(), subletter)
            data_log.append(entry)  
            temp_log.append(entry)  
            write_csv([data_log[-1]])

        gesture_count += 1
        progress += 1
        progress_bar['value'] = progress
        root.update()

        if gesture_count == 10:
            show_break_message()
            root.wait_variable(key_pressed)  
            if key_pressed.get() == 'r':
                repeat_last_n(temp_log, n=10)
            temp_log = []  
            gesture_count = 0
            countdown(0.1)
        
        gesture_count

def show_break_message():
    label.config(text="Break", font=("Helvetica", 96))
    image_label.config(image='')  # Clear image during break
    root.update()

def on_key_press(event):
    global key_pressed
    if event.char == 's':  # Start sequence with 'k'
        key_pressed.set(event.char)
        start_sequence()  # Call start_sequence directly
    elif event.char == 'r' or event.char == 'k':  # To repeat the last n gestures
        key_pressed.set(event.char)

def repeat_last_n(temp_log, n=10):
    global letters, data_log
    data_log = data_log[:-n]  
    with open(fname, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['start_time', 'end_time', 'label'])
        writer.writerows(data_log)
    progress_bar['value'] -= n
    letters = letters + [entry[2] for entry in temp_log][::-1]  

def delete_last(event=None):
    global data_log
    if data_log:
        last_entry = data_log.pop()
        with open(fname, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['start_time', 'end_time', 'label'])
            writer.writerows(data_log)
        progress_bar['value'] -= 1
        letters.append(last_entry[2])
        root.update()
        print(f"Last entry '{last_entry[2]}': {LETTER_GESTURES[last_entry[2]]} deleted.")
    else:
        print("No more entries to delete.")

def on_closing():
    root.destroy()  # This will close the application

try:
    FILEINDEX = int(sys.argv[1])
except:
    print("Please provide a file index")
    sys.exit(1)
fname = os.path.join(SAVE_PATH, f'label_{FILEINDEX:03d}.csv')

root = tk.Tk()
root.title("Countdown & Letter Display")
root.state('zoomed')  # This will maximize the window

image_label = tk.Label(root)
image_label.place(relx=0.5, rely=0.5, anchor='center')  # Center the image label

label = tk.Label(root, text="", font=("Helvetica", 48))
label.place(relx=0.5, rely=0.2, anchor='center')  # Position above the image

progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.place(relx=0.5, rely=0.8, anchor='center')  # Position below the image

start_button = tk.Button(root, text="Start", command=start_sequence, font=("Helvetica", 24), padx=5, pady=5)
start_button.place(relx=0.5, rely=0.9, anchor='center')

# Create a variable to hold the key pressed
key_pressed = tk.StringVar()
root.bind('<KeyPress>', on_key_press)
root.bind('<Delete>', delete_last)

# Set the close protocol to call the on_closing function
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
