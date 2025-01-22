// components/MediaPlayer.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipForward, SkipBack, Volume2, Volume1, VolumeX } from 'lucide-react';

const MediaPlayer = ({ currentGesture, rotation }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration] = useState(235);
  const [volume, setVolume] = useState(70);
  const [isMuted, setIsMuted] = useState(false);
  const [activeButton, setActiveButton] = useState(null);
  const lastGesture = useRef(null);

  // Debug logging for props
  useEffect(() => {
    console.log('MediaPlayer received currentGesture:', currentGesture);
    console.log('MediaPlayer received rotation:', rotation);
  }, [currentGesture, rotation]);

  // Debug logging for button state
  useEffect(() => {
    console.log('Active button state:', activeButton);
  }, [activeButton]);

  // Handle gesture inputs with visual feedback
  useEffect(() => {
    if (currentGesture && currentGesture !== lastGesture.current) {
      console.log('Processing gesture:', currentGesture);
      lastGesture.current = currentGesture;
      
      switch (currentGesture) {
        case 'Swipe Right':
          console.log('Triggering next button');
          setActiveButton('next');
          setTimeout(() => setActiveButton(null), 500);
          break;
        case 'Swipe Left':
          console.log('Triggering prev button');
          setActiveButton('prev');
          setTimeout(() => setActiveButton(null), 500);
          break;
        case 'Side Tap':
          console.log('Triggering volume button');
          setActiveButton('volume');
          setIsMuted(!isMuted);
          setTimeout(() => setActiveButton(null), 500);
          break;
        case 'Swipe Backward':
          console.log('Triggering play button');
          setActiveButton('play');
          setIsPlaying(!isPlaying);
          setTimeout(() => setActiveButton(null), 500);
          break;
        default:
          console.log('Unknown gesture:', currentGesture);
          break;
      }
    }
  }, [currentGesture, isMuted, isPlaying]);

  // Handle incremental rotation for volume
  useEffect(() => {
    if (rotation !== undefined && rotation !== 0) {     

      const volumeChange = (rotation / 3.6);

      setVolume(prevVolume => {
        const newVolume = Math.min(Math.max(prevVolume + volumeChange, 0), 100);
        const roundedVolume = Math.round(newVolume);
        return roundedVolume;
      });
    }
    
  }, [rotation]);

  // Handle playback timer
  useEffect(() => {
    let interval;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= duration) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, duration]);

  const handleButtonClick = (buttonId, action) => {
    setActiveButton(buttonId);
    if (action) action();
    setTimeout(() => setActiveButton(null), 500);
  };

  const handleMuteToggle = () => {
    setIsMuted(!isMuted);
  };

  const handleVolumeAdjust = (newVolume) => {
    setVolume(newVolume);
    if (newVolume === 0) {
      setIsMuted(true);
    } else {
      setIsMuted(false);
    }
  };

  const handleTimelineClick = (e) => {
    const timeline = e.currentTarget;
    const rect = timeline.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    setCurrentTime(Math.floor(percentage * duration));
  };

  const VolumeIcon = () => {
    if (isMuted || volume === 0) return <VolumeX />;
    if (volume < 50) return <Volume1 />;
    return <Volume2 />;
  };

  return (
    <div className="flex w-full max-w-2xl bg-gray-800 rounded-lg">
      {/* Main content area */}
      <div className="flex-1 p-4">
        {/* Mock video display */}
        <div className="w-full h-64 bg-gray-900 rounded-lg mb-4 flex items-center justify-center">
          <img src="/api/placeholder/640/360" alt="Video placeholder" className="w-full h-full object-cover rounded-lg" />
        </div>

        {/* Progress bar */}
        <div 
          className="w-full h-2 bg-gray-600 rounded-full mb-4 cursor-pointer"
          onClick={handleTimelineClick}
        >
          <div 
            className="h-full bg-blue-500 rounded-full"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        {/* Centered Controls */}
        <div className="flex justify-center">
          <div className="flex items-center space-x-6">
            <button 
              className={`p-2 rounded-full text-white ${activeButton === 'prev' ? 'bg-gray-600' : 'bg-gray-800'} transition-colors`}
              onClick={() => handleButtonClick('prev')}
            >
              <SkipBack className="w-8 h-8" />
            </button>
            <button 
              className={`p-3 rounded-full text-white ${activeButton === 'play' ? 'bg-gray-600' : 'bg-gray-800'} transition-colors`}
              onClick={() => handleButtonClick('play', () => setIsPlaying(!isPlaying))}
            >
              {isPlaying ? 
                <Pause className="w-10 h-10" /> : 
                <Play className="w-10 h-10" />
              }
            </button>
            <button 
              className={`p-2 rounded-full text-white ${activeButton === 'next' ? 'bg-gray-600' : 'bg-gray-800'} transition-colors`}
              onClick={() => handleButtonClick('next')}
            >
              <SkipForward className="w-8 h-8" />
            </button>
          </div>
        </div>
      </div>

      {/* Vertical volume control */}
      <div className="w-16 bg-gray-700 rounded-r-lg flex flex-col items-center py-4 space-y-4">
        <button 
          className={`p-2 rounded-full text-white ${activeButton === 'volume' ? 'bg-gray-600' : 'bg-gray-700'} transition-colors`}
          onClick={() => handleButtonClick('volume', handleMuteToggle)}
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