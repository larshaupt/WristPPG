'use client';

import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const LiveSignalViewer = () => {
    const [data, setData] = useState([]);
    const [currentGesture, setCurrentGesture] = useState("No Gesture");
    const [confidence, setConfidence] = useState(0);
    const [probabilities, setProbabilities] = useState([]);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('http://localhost:5000/data', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const newData = await response.json();
                setData(newData.imu_data);
                setCurrentGesture(newData.gesture);
                setConfidence(newData.confidence);
                setProbabilities(newData.probabilities || []); // Assuming backend provides this
                setError(null);
            } catch (err) {
                setError(err.message);
                console.error("Failed to fetch data:", err);
            }
        };

        const timer = setInterval(fetchData, 100);  // Poll every 100ms
        return () => clearInterval(timer);
    }, []);
    
    return (
        <div className="w-full p-4 space-y-4">
            <div className="flex flex-row gap-4">
                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>Current Gesture</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <Badge variant={currentGesture === "No Gesture" ? "secondary" : "default"} 
                                   className="text-lg py-2 px-4">
                                {currentGesture}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                                Confidence: {confidence.toFixed(1)}%
                            </span>
                        </div>
                    </CardContent>
                </Card>
                
                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>Class Probabilities</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart 
                                    data={probabilities}
                                    margin={{ top: 5, right: 30, left: 20, bottom: 50 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis 
                                        dataKey="name"
                                        angle={-45}
                                        textAnchor="end"
                                        height={60}
                                        interval={0}
                                    />
                                    <YAxis domain={[0, 100]} />
                                    <Tooltip />
                                    <Bar dataKey="probability" fill="#8884d8" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card className="w-full">
                <CardHeader>
                    <CardTitle>Accelerometer Data</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey={(entry, index) => index} label="Sample Index" />
                                <YAxis domain={[-2, 2]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="accelX" stroke="#8884d8" dot={false} />
                                <Line type="monotone" dataKey="accelY" stroke="#82ca9d" dot={false} />
                                <Line type="monotone" dataKey="accelZ" stroke="#ffc658" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            <Card className="w-full">
                <CardHeader>
                    <CardTitle>Gyroscope Data</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey={(entry, index) => index} label="Sample Index" />
                                <YAxis domain={[-2, 2]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="gyroX" stroke="#ff7300" dot={false} />
                                <Line type="monotone" dataKey="gyroY" stroke="#ff0000" dot={false} />
                                <Line type="monotone" dataKey="gyroZ" stroke="#00ff00" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default LiveSignalViewer;