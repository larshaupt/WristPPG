import os
from pathlib import Path
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