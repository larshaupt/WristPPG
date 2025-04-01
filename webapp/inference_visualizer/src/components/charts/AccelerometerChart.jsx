// components/charts/AccelerometerChart.jsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Minimize2, Maximize2 } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const AccelerometerChart = ({ data, isVisible, onToggle }) => {
  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Accelerometer Data</CardTitle>
        <Button 
          variant="ghost" 
          size="icon"
          onClick={onToggle}
        >
          {isVisible ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </Button>
      </CardHeader>
      {isVisible && (
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={false} />
                <YAxis domain={[-2, 2]} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="accelX" stroke="#8884d8" dot={false} name="X-Axis" />
                <Line type="monotone" dataKey="accelY" stroke="#82ca9d" dot={false} name="Y-Axis" />
                <Line type="monotone" dataKey="accelZ" stroke="#ffc658" dot={false} name="Z-Axis" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export default AccelerometerChart;