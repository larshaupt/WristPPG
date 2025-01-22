import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const GesturePacman = () => {
  const [playerPos, setPlayerPos] = useState({ x: 1, y: 1 });
  const [score, setScore] = useState(0);
  const [dots, setDots] = useState([]);
  const [currentGesture, setCurrentGesture] = useState("No Gesture");
  const [isSimulated, setIsSimulated] = useState(true);
  
  // Define the maze layout (0 = wall, 1 = path)
  const initialMaze = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  ];

  // Initialize dots
  useEffect(() => {
    const newDots = [];
    initialMaze.forEach((row, y) => {
      row.forEach((cell, x) => {
        if (cell === 1 && !(x === 1 && y === 1)) {
          newDots.push({ x, y });
        }
      });
    });
    setDots(newDots);
  }, []);

  // Try to fetch gesture data, fall back to simulation if server not available
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:5000/data');
        const data = await response.json();
        setIsSimulated(false);
        
        if (data.gesture !== currentGesture) {
          setCurrentGesture(data.gesture);
          handleGestureMove(data.gesture);
        }
      } catch (error) {
        setIsSimulated(true); // Enable simulation mode if server unavailable
      }
    };

    const timer = setInterval(fetchData, 100);
    return () => clearInterval(timer);
  }, [currentGesture]);

  // Handle keyboard controls (only active in simulation mode)
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (!isSimulated) return; // Only handle keyboard if in simulation mode

      const keyToGesture = {
        'ArrowUp': 'Swipe Forward',
        'ArrowDown': 'Swipe Backward',
        'ArrowLeft': 'Swipe Left',
        'ArrowRight': 'Swipe Right'
      };

      const gesture = keyToGesture[e.key];
      if (gesture) {
        setCurrentGesture(gesture);
        handleGestureMove(gesture);
        
        setTimeout(() => {
          setCurrentGesture("No Gesture");
        }, 500);
      }
    };

    if (isSimulated) {
      window.addEventListener('keydown', handleKeyPress);
      return () => window.removeEventListener('keydown', handleKeyPress);
    }
  }, [isSimulated, playerPos, dots, score]);

  const handleGestureMove = (gesture) => {
    // Only handle specific directional gestures
    const validGestures = {
      "Swipe Forward": { x: 0, y: -1 },
      "Swipe Backward": { x: 0, y: 1 },
      "Swipe Right": { x: 1, y: 0 },
      "Swipe Left": { x: -1, y: 0 }
    };

    const move = validGestures[gesture];
    if (!move) return; // Ignore any gesture not in validGestures

    const newPos = {
      x: playerPos.x + move.x,
      y: playerPos.y + move.y
    };

    // Check if the new position is valid (not a wall)
    if (initialMaze[newPos.y]?.[newPos.x] === 1) {
      setPlayerPos(newPos);
      
      // Check if there's a dot at the new position
      const dotIndex = dots.findIndex(dot => dot.x === newPos.x && dot.y === newPos.y);
      if (dotIndex !== -1) {
        setDots(dots.filter((_, index) => index !== dotIndex));
        setScore(score + 10);
      }
    }
  };

  // Win condition
  useEffect(() => {
    if (dots.length === 0) {
      alert("Congratulations! You've won!");
    }
  }, [dots]);

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>
            Gesture Pacman {isSimulated ? "(Simulated)" : "(Live Gestures)"}
          </CardTitle>
          <Badge variant="default">Score: {score}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-4">
          <Badge variant="secondary">Current Gesture: {currentGesture}</Badge>
          {isSimulated && (
            <div className="text-sm text-muted-foreground mb-4">
              Use arrow keys to control Pacman
            </div>
          )}
          <div className="inline-grid gap-0" style={{ 
            gridTemplateColumns: `repeat(${initialMaze[0].length}, 30px)` 
          }}>
            {initialMaze.map((row, y) => 
              row.map((cell, x) => (
                <div
                  key={`${x}-${y}`}
                  className={`
                    w-8 h-8 flex items-center justify-center
                    ${cell === 0 ? 'bg-blue-800' : 'bg-black'}
                  `}
                >
                  {playerPos.x === x && playerPos.y === y ? (
                    <div className="w-6 h-6 bg-yellow-400 rounded-full" />
                  ) : dots.some(dot => dot.x === x && dot.y === y) ? (
                    <div className="w-2 h-2 bg-white rounded-full" />
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GesturePacman;