// components/MediaPlayerPanel.jsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Minimize2, Maximize2 } from "lucide-react";
import MediaPlayer from './MediaPlayer';

const MediaPlayerPanel = ({ isVisible, onToggle, currentGesture, rotation }) => {
  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Media Player</CardTitle>
        <Button 
          variant="ghost" 
          size="icon"
          onClick={onToggle}
        >
          {isVisible ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </Button>
      </CardHeader>
      {isVisible && (
        <CardContent className="flex justify-center">
          <MediaPlayer 
            currentGesture={currentGesture}
            rotation={rotation}
          />
        </CardContent>
      )}
    </Card>
  );
};

export default MediaPlayerPanel;