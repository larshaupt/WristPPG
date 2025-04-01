// components/LiveSignalViewer.jsx
"use client";

import React, { useState, useEffect } from 'react';
import { Card } from "@/components/ui/card";
import GestureDisplay from './GestureDisplay';
import RotaryController from './RotaryController';
import MediaPlayerPanel from './MediaPlayerPanel';
import ProbabilityChart from './charts/ProbabilityChart';
import ProbabilityHistoryChart from './charts/ProbabilityHistoryChart';
import AccelerometerChart from './charts/AccelerometerChart';
import GyroscopeChart from './charts/GyroscopeChart';
import OrientationChart from './charts/OrientationChart';
const SERVER_IP = '129.132.75.227'; // Replace with your known IP address
const LiveSignalViewer = () => {
    const [data, setData] = useState([]);
    const [currentGesture, setCurrentGesture] = useState("No Gesture");
    const [confidence, setConfidence] = useState(0);
    const [probabilities, setProbabilities] = useState([]);
    const [probabilityHistory, setProbabilityHistory] = useState([]);
    const [rotation, setRotation] = useState(0);
    const [filteredGesture, setFilteredGesture] = useState(null);
    const maxHistoryLength = 100;

    // Panel visibility states
    const [visiblePanels, setVisiblePanels] = useState({
        probabilityHistory: false,
        accelerometer: true,
        gyroscope: true,
        orientation: true,
        currentProbabilities: true,
        mediaPlayer: true
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(`http://${SERVER_IP}:5000/data`);
                const newData = await response.json();
                console.log('API Response:', newData); // Log full API response
                
                setData(newData.imu_data);
                setCurrentGesture(newData.gesture);
                setFilteredGesture(newData.filtered_gesture); // Log filtered gesture
                console.log('Setting filtered gesture:', newData.filtered_gesture);
                
                setConfidence(newData.confidence);
                setProbabilities(newData.probabilities);
                
                if (visiblePanels.probabilityHistory) {
                    setProbabilityHistory(prevHistory => {
                        const timestamp = new Date().getTime();
                        const newHistoryPoint = {
                            timestamp,
                            ...Object.fromEntries(newData.probabilities.map(p => [p.name, p.probability]))
                        };
                        return [...prevHistory, newHistoryPoint].slice(-maxHistoryLength);
                    });
                }
                
                setRotation(newData.rotation || 0);
                console.log('Setting rotation:', newData.rotation || 0);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        const timer = setInterval(fetchData, 50);
        return () => clearInterval(timer);
    }, [visiblePanels.probabilityHistory]);

    const togglePanel = (panelName) => {
        setVisiblePanels(prev => ({
            ...prev,
            [panelName]: !prev[panelName]
        }));
    };

    return (
        <div className="w-full p-4 space-y-4">
            <div className="flex flex-row gap-4">
                <GestureDisplay 
                    currentGesture={currentGesture} 
                    confidence={confidence} 
                />
                <Card className="basis-1/4">
                    <RotaryController rotation={rotation} />
                </Card>
                <ProbabilityChart 
                    data={probabilities}
                    isVisible={visiblePanels.currentProbabilities}
                    onToggle={() => togglePanel('currentProbabilities')}
                />
            </div>

            <ProbabilityHistoryChart 
                data={probabilityHistory}
                probabilities={probabilities}
                isVisible={visiblePanels.probabilityHistory}
                onToggle={() => togglePanel('probabilityHistory')}
            />

            <MediaPlayerPanel 
                isVisible={visiblePanels.mediaPlayer}
                onToggle={() => togglePanel('mediaPlayer')}
                currentGesture={currentGesture}
                rotation={rotation}
            />

            <AccelerometerChart 
                data={data}
                isVisible={visiblePanels.accelerometer}
                onToggle={() => togglePanel('accelerometer')}
            />

            <GyroscopeChart 
                data={data}
                isVisible={visiblePanels.gyroscope}
                onToggle={() => togglePanel('gyroscope')}
            />

            <OrientationChart 
                data={data}
                isVisible={visiblePanels.orientation}
                onToggle={() => togglePanel('orientation')}
            />
        </div>
    );
};

export default LiveSignalViewer;