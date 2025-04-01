// components/charts/OrientationChart.jsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Minimize2, Maximize2 } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const OrientationChart = ({ data, isVisible, onToggle }) => {
  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Orientation Angles</CardTitle>
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
      )}
    </Card>
  );
};

export default OrientationChart;