import os
from pathlib import Path
import numpy as np
from mutagen import File  # You'll need to install mutagen: pip install mutagen
def get_songs_metadata():
    songs = []
    audio_directory = r"C:\Users\lhauptmann\Code\WristPPG2\stream\inference_visualizer\public\song_files"
    
    for file in os.listdir(audio_directory):
        if file.endswith(('.mp3', '.wav', '.m4a')):
            file_path = os.path.join(audio_directory, file)
            try:
                audio = File(file_path)
                
                # Default values from filename
                title = Path(file).stem
                artist = 'Unknown Artist'
                
                # Try to get metadata if available
                if audio is not None:  # Check if audio file was loaded
                    if hasattr(audio, 'tags') and audio.tags:  # Check if tags exist
                        tags = audio.tags
                        # Try different tag formats (ID3, etc)
                        if hasattr(tags, 'get'):  # ID3 tags
                            title = str(tags.get('TIT2', [title])[0])
                            artist = str(tags.get('TPE1', [artist])[0])
                        elif hasattr(tags, 'title'):  # Some other formats
                            title = tags.title[0] if tags.title else title
                            artist = tags.artist[0] if hasattr(tags, 'artist') and tags.artist else artist
                
                # Look for album art
                artwork_path = None
                artwork_files = [f for f in os.listdir(audio_directory) 
                               if f.startswith('AlbumArt_') and 
                               f.endswith(('.jpg', '.png'))]
                if artwork_files:
                    artwork_path = artwork_files[0]

                songs.append({
                    'id': len(songs) + 1,
                    'title': title,
                    'artist': artist,
                    'filename': file,
                    'artwork': artwork_path
                })
                
            except Exception as e:
                print(f"Error processing {file}: {e}")
                # Add file with basic info even if metadata extraction fails
                songs.append({
                    'id': len(songs) + 1,
                    'title': Path(file).stem,
                    'artist': 'Unknown Artist',
                    'filename': file,
                    'artwork': None
                })
    
    return songs



import keyboard  # You'll need to pip install keyboard

# Add at the beginning of the script, with other global variables
keyboard_mode = False  # Global flag to switch between keyboard and model modes

def handle_keyboard_input():
    """Handle keyboard input and return corresponding gesture data"""
    # Map keys to gestures
    key_to_gesture = {
        'w': ('Swipe Forward', 1),      # a
        's': ('Swipe Backward', 2),     # b
        'a': ('Swipe Left', 3),         # c
        'd': ('Swipe Right', 4),        # d
        'q': ('Pinch Close', 5),        # pc
        'e': ('Pinch Open', 6),         # po
        'r': ('Side Tap', 7),           # sp
        't': ('Rotate', 8),             # pr
        'space': ('Nothing', 0),        # o
    }
    
    # Check each key and return the first pressed key's gesture
    for key, (gesture_name, gesture_id) in key_to_gesture.items():
        if keyboard.is_pressed(key):
            # Create a probability array with 1.0 for the pressed gesture
            probability = np.zeros(9)
            probability[gesture_id] = 1.0
            return gesture_name, 1.0, probability, gesture_name
            
    # If no key is pressed, return "Nothing"
    probability = np.zeros(9)
    probability[0] = 1.0
    return "Nothing", 1.0, probability, "Nothing"