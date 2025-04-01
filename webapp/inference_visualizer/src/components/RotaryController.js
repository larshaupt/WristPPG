import React, { useState, useEffect, useRef } from 'react';

const RotaryController = ({ rotation = 0 }) => {
  const [cumulativeRotation, setCumulativeRotation] = useState(0);
  const [isMoving, setIsMoving] = useState(false);
  
  useEffect(() => {
    // Only update if we get a non-zero rotation
    if (rotation !== 0) {
      setCumulativeRotation(prev => prev + rotation);
      setIsMoving(true);
      
      const timeout = setTimeout(() => {
        setIsMoving(false);
      }, 100);
      
      return () => clearTimeout(timeout);
    }
  }, [rotation]);

  return (
    <div className="flex justify-center items-center h-full w-full p-4">
      <div className="relative w-24 h-24">
        {/* Outer ring */}
        <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
        
        {/* Inner knob with indicator */}
        <div 
          className="absolute inset-2 rounded-full bg-blue-500 shadow-lg transform transition-transform duration-150"
          style={{ transform: `rotate(${cumulativeRotation}deg)` }}
        >
          <div 
            className={`absolute top-0 left-1/2 w-1 h-6 -translate-x-1/2 transition-colors duration-150 ${
              isMoving ? 'bg-green-400' : 'bg-red-400'
            }`} 
          />
        </div>
      </div>
    </div>
  );
};

export default RotaryController;