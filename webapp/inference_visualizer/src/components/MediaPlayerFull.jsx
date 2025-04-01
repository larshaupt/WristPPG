"use client";

import React, { useState, useEffect } from 'react';
import MediaPlayer from './MediaPlayer';

const SERVER_IP = ''; // Replace with your known IP address

const FullscreenPlayer = () => {
  const [currentGesture, setCurrentGesture] = useState("No Gesture");
  const [rotation, setRotation] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`http://${SERVER_IP}:5000/data`);
        if (response.ok) {
          const newData = await response.json();
          setCurrentGesture(newData.gesture);
          setRotation(newData.rotation || 0);
          setIsConnected(true);
        } else {
          setIsConnected(false);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        setIsConnected(false);
      }
    };

    const timer = setInterval(fetchData, 50);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative h-screen w-full bg-gray-900 flex items-center justify-center p-4">
      <MediaPlayer currentGesture={currentGesture} rotation={rotation} />
      {/* Optional connection status indicator */}
      <div className={`absolute top-4 right-4 w-3 h-3 rounded-full ${
        isConnected ? 'bg-green-500' : 'bg-red-500'
      }`} />
    </div>
  );
};

export default FullscreenPlayer;