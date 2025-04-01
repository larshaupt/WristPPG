import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Minimize2, Maximize2 } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';

const ProbabilityChart = ({ data, isVisible, onToggle }) => {
  return (
    <Card className="basis-3/4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Class Probabilities</CardTitle>
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
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={data}
                margin={{ top: 10, right: 20, left: 20, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="name"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  interval={0}
                  fontSize={20}
                />
                <YAxis 
                  domain={[0, 100]}
                  fontSize={20}
                />
                <Tooltip />
                <Bar dataKey="probability" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export default ProbabilityChart;