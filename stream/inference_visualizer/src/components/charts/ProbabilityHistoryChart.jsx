// components/charts/ProbabilityHistoryChart.jsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Minimize2, Maximize2 } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const ProbabilityHistoryChart = ({ data, probabilities, isVisible, onToggle }) => {
  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Probability History</CardTitle>
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
                <XAxis 
                  dataKey="timestamp" 
                  tick={false}
                  label={{ value: 'Time', position: 'bottom' }} 
                />
                <YAxis 
                  domain={[0, 100]}
                  label={{ value: 'Probability (%)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  labelFormatter={(label) => new Date(label).toLocaleTimeString()}
                  formatter={(value) => [`${value.toFixed(1)}%`]}
                />
                <Legend />
                {probabilities.map((prob, index) => (
                  <Line 
                    key={prob.name}
                    type="monotone"
                    dataKey={prob.name}
                    name={prob.name}
                    stroke={`hsl(${index * (360 / probabilities.length)}, 70%, 50%)`}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export default ProbabilityHistoryChart;