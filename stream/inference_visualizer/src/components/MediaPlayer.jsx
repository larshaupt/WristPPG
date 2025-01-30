import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipForward, SkipBack, Volume2, Volume1, VolumeX } from 'lucide-react';

const songs = [
  { 
    id: 1, 
    title: "Sultans of Swing", 
    artist: "Dire Straits", 
    url: "/song_files/Dire Straits - Sultans Of Swing.mp3",
    imageUrl: "/song_files/AlbumArt_{DEB01734-C213-4F07-B41F-1179B1FF2231}_Small.jpg" 
  },
  { 
    id: 2, 
    title: "Walk of Life", 
    artist: "Dire Straits", 
    url: "/song_files/Dire Straits - Walk Of Life.mp3",
    imageUrl: "/song_files/AlbumArt_{B5020207-474E-4720-3582-302E205FE300}_Small.jpg" 
  },
  { 
    id: 3, 
    title: "Fire & Thunder", 
    artist: "The Electric Howl", 
    url: "/song_files/energetic-indie-rock-252361.mp3",
    imageUrl: "" 
  },
  { 
    id: 4, 
    title: "Funky Streets", 
    artist: "Groove Masters", 
    url: "/song_files/jazz-funk-groove-instrumental-222618.mp3",
    imageUrl: "" 
  },
  { 
    id: 5, 
    title: "Waves of Serenity", 
    artist: "Luna Keys", 
    url: "/song_files/ocean-song-piano-music-292991.mp3",
    imageUrl: "" 
  },
  { 
    id: 6, 
    title: "Sax in the Moonlight", 
    artist: "Leo Starlight", 
    url: "/song_files/romantic-saxophone-244539.mp3",
    imageUrl: "" 
  },
  { 
    id: 7, 
    title: "Whispering Keys", 
    artist: "Eleanor Ivory", 
    url: "/song_files/soft-background-piano-285589.mp3",
    imageUrl: "" 
  },
  { 
    id: 8, 
    title: "Rock Riot", 
    artist: "The Stone Rebels", 
    url: "/song_files/stomping-rock-four-shots-111444.mp3",
    imageUrl: "" 
  },
  { 
    id: 9, 
    title: "Midnight Jazz Club", 
    artist: "Miles Evergreen", 
    url: "/song_files/the-best-jazz-club-in-new-orleans-164472.mp3",
    imageUrl: "" 
  },
  { 
    id: 10, 
    title: "Sunset Vibes", 
    artist: "Indigo Skies", 
    url: "/song_files/upbeat-indie-pop-141685.mp3",
    imageUrl: "" 
  }
];

const MediaPlayer = ({ currentGesture, rotation }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(70);
  const [isMuted, setIsMuted] = useState(false);
  const [activeButton, setActiveButton] = useState(null);
  const [currentSongIndex, setCurrentSongIndex] = useState(0);
  const lastGesture = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    audioRef.current = new Audio(songs[currentSongIndex].url);
    audioRef.current.addEventListener('loadedmetadata', () => {
      setDuration(audioRef.current.duration);
    });
    audioRef.current.addEventListener('timeupdate', () => {
      setCurrentTime(audioRef.current.currentTime);
    });
    audioRef.current.addEventListener('ended', handleNext);

    return () => {
      if (audioRef.current) {
        audioRef.current.removeEventListener('loadedmetadata', () => {});
        audioRef.current.removeEventListener('timeupdate', () => {});
        audioRef.current.removeEventListener('ended', handleNext);
        audioRef.current.pause();
      }
    };
  }, [currentSongIndex]);

  useEffect(() => {
    if (currentGesture && currentGesture !== lastGesture.current) {
      lastGesture.current = currentGesture;
      
      switch (currentGesture) {
        case 'Swipe Right':
          handleNext();
          break;
        case 'Swipe Left':
          handlePrevious();
          break;
        case 'Side Tap':
          handleMuteToggle();
          break;
        case 'Swipe Backward':
          handlePlayPause();
          break;
      }
    }
  }, [currentGesture]);

  useEffect(() => {
    if (rotation !== undefined && rotation !== 0) {     
      const volumeChange = (rotation / 3.6);
      handleVolumeAdjust(Math.min(Math.max(volume + volumeChange, 0), 100));
    }
  }, [rotation]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume / 100;
    }
  }, [volume, isMuted]);

  const handlePlayPause = () => {
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
    setActiveButton('play');
    setTimeout(() => setActiveButton(null), 500);
  };

  const handleNext = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setCurrentSongIndex((prev) => (prev + 1) % songs.length);
    setActiveButton('next');
    setTimeout(() => {
      setActiveButton(null);
      if (isPlaying && audioRef.current) {
        audioRef.current.play();
      }
    }, 500);
  };

  const handlePrevious = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setCurrentSongIndex((prev) => (prev - 1 + songs.length) % songs.length);
    setActiveButton('prev');
    setTimeout(() => {
      setActiveButton(null);
      if (isPlaying && audioRef.current) {
        audioRef.current.play();
      }
    }, 500);
  };

  const handleMuteToggle = () => {
    setIsMuted(!isMuted);
    setActiveButton('volume');
    setTimeout(() => setActiveButton(null), 500);
  };

  const handleVolumeAdjust = (newVolume) => {
    const roundedVolume = Math.round(newVolume);
    setVolume(roundedVolume);
    setIsMuted(roundedVolume === 0);
  };

  const handleTimelineClick = (e) => {
    const timeline = e.currentTarget;
    const rect = timeline.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    const newTime = percentage * duration;
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const VolumeIcon = () => {
    if (isMuted || volume === 0) return <VolumeX />;
    if (volume < 50) return <Volume1 />;
    return <Volume2 />;
  };

  return (
    <div className="flex w-full max-w-2xl bg-gray-800 rounded-lg">
      <div className="flex-1 p-4">
        <div className="w-full h-64 bg-gray-900 rounded-lg mb-4 flex flex-col items-center justify-center text-white overflow-hidden relative">
          {songs[currentSongIndex].artwork ? (
            <img 
              src={songs[currentSongIndex].artwork} 
              alt={`${songs[currentSongIndex].title} artwork`}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.parentElement.classList.add('no-artwork');
                e.target.remove();
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-800 to-gray-900">
              <div className="text-6xl font-bold text-gray-600">♪</div>
            </div>
          )}
          <div className="absolute bottom-0 w-full bg-black bg-opacity-50 p-4">
            <h2 className="text-2xl font-bold mb-1">{songs[currentSongIndex].title}</h2>
            <p className="text-gray-200">{songs[currentSongIndex].artist}</p>
          </div>
        </div>

        <div className="flex justify-between text-white text-sm mb-1">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>

        <div 
          className="w-full h-2 bg-gray-600 rounded-full mb-4 cursor-pointer"
          onClick={handleTimelineClick}
        >
          <div 
            className="h-full bg-blue-500 rounded-full"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        <div className="flex justify-center">
          <div className="flex items-center space-x-6">
            <button 
              className={`p-2 rounded-full text-white ${activeButton === 'prev' ? 'bg-gray-600' : 'bg-gray-800'} transition-colors`}
              onClick={handlePrevious}
            >
              <SkipBack className="w-8 h-8" />
            </button>
            <button 
              className={`p-3 rounded-full text-white ${activeButton === 'play' ? 'bg-gray-600' : 'bg-gray-800'} transition-colors`}
              onClick={handlePlayPause}
            >
              {isPlaying ? 
                <Pause className="w-10 h-10" /> : 
                <Play className="w-10 h-10" />
              }
            </button>
            <button 
              className={`p-2 rounded-full text-white ${activeButton === 'next' ? 'bg-gray-600' : 'bg-gray-800'} transition-colors`}
              onClick={handleNext}
            >
              <SkipForward className="w-8 h-8" />
            </button>
          </div>
        </div>
      </div>

      <div className="w-16 bg-gray-700 rounded-r-lg flex flex-col items-center py-4 space-y-4">
        <button 
          className={`p-2 rounded-full text-white ${activeButton === 'volume' ? 'bg-gray-600' : 'bg-gray-700'} transition-colors`}
          onClick={handleMuteToggle}
        >
          <VolumeIcon />
        </button>
        <div className="h-64 flex items-center">
          <input
            type="range"
            min="0"
            max="100"
            value={isMuted ? 0 : volume}
            onChange={(e) => handleVolumeAdjust(parseInt(e.target.value))}
            className="w-64 -rotate-90"
          />
        </div>
      </div>
    </div>
  );
};

export default MediaPlayer;