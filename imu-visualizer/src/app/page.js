import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const LiveSignalViewer = () => {
    const [data, setData] = useState([]);
    const [currentGesture, setCurrentGesture] = useState("No Gesture");
    const [confidence, setConfidence] = useState(0);
    const windowSize = 150; // Number of samples to show

    // Simulated data update - replace this with your actual data source
    useEffect(() => {
      const fetchData = async () => {
          const response = await fetch('http://localhost:5000/data');
          const newData = await response.json();
          setData(newData.imu_data);
          setCurrentGesture(newData.gesture);
          setConfidence(newData.confidence);
      };
  
      const timer = setInterval(fetchData, 50);
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
                                <XAxis dataKey="timestamp" tick={false} />
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
                                <XAxis dataKey="timestamp" tick={false} />
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

            <Card className="w-full">
                <CardHeader>
                    <CardTitle>Orientation Angles</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="timestamp" tick={false} />
                                <YAxis domain={[-180, 180]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="orientation.yaw" name="Yaw" stroke="#9c27b0" dot={false} />
                                <Line type="monotone" dataKey="orientation.pitch" name="Pitch" stroke="#2196f3" dot={false} />
                                <Line type="monotone" dataKey="orientation.roll" name="Roll" stroke="#4caf50" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default LiveSignalViewer;