// components/GestureDisplay.jsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const GestureDisplay = ({ currentGesture, confidence }) => {
  return (
    <Card className="basis-1/4">
      <CardHeader>
        <CardTitle>Current Gesture</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Badge 
            variant={currentGesture === "No Gesture" ? "secondary" : "default"} 
            className="text-lg py-2 px-4"
          >
            {currentGesture}
          </Badge>
          <span className="text-sm text-muted-foreground">
            Confidence: {confidence.toFixed(1)}%
          </span>
        </div>
      </CardContent>
    </Card>
  );
};

export default GestureDisplay;