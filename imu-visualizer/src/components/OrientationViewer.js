import React, { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import OrientationViewer from "@/components/OrientationViewer";

const OrientationViewer = ({ orientation = { roll: 0, pitch: 0, yaw: 0 } }) => {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current || sceneRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    
    renderer.setSize(400, 400);
    mountRef.current.appendChild(renderer.domElement);
    
    // Add orbit controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    // Create IMU sensor model
    const board = new THREE.Group();

    // Main PCB board
    const boardGeometry = new THREE.BoxGeometry(2, 0.2, 3);
    const boardMaterial = new THREE.MeshPhongMaterial({ 
      color: 0x2d3748,
      shininess: 30
    });
    const boardMesh = new THREE.Mesh(boardGeometry, boardMaterial);
    board.add(boardMesh);

    // IMU Chip
    const chipGeometry = new THREE.BoxGeometry(0.8, 0.3, 0.8);
    const chipMaterial = new THREE.MeshPhongMaterial({ 
      color: 0x4a5568,
      shininess: 50
    });
    const chipMesh = new THREE.Mesh(chipGeometry, chipMaterial);
    chipMesh.position.y = 0.25;
    board.add(chipMesh);

    // Axes helpers
    const axesHelper = new THREE.AxesHelper(2);
    board.add(axesHelper);

    scene.add(board);

    // Position camera
    camera.position.set(3, 3, 3);
    camera.lookAt(0, 0, 0);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };

    // Store references for cleanup and updates
    sceneRef.current = {
      scene,
      camera,
      renderer,
      board,
      animate,
      controls
    };

    // Start animation
    animate();

    // Handle resize
    const handleResize = () => {
      if (mountRef.current) {
        const width = mountRef.current.clientWidth;
        camera.aspect = 1;
        camera.updateProjectionMatrix();
        renderer.setSize(width, width);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (mountRef.current) {
        mountRef.current.removeChild(renderer.domElement);
      }
      controls.dispose();
    };
  }, []);

  // Update orientation
  useEffect(() => {
    if (!sceneRef.current) return;

    const { board } = sceneRef.current;
    
    // Convert degrees to radians
    const rollRad = orientation.roll * (Math.PI / 180);
    const pitchRad = orientation.pitch * (Math.PI / 180);
    const yawRad = orientation.yaw * (Math.PI / 180);

    // Apply rotations in ZYX order (yaw, pitch, roll)
    board.rotation.set(pitchRad, yawRad, rollRad, 'ZYX');
  }, [orientation]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Sensor Orientation (Three.js)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between mb-4">
          <div className="text-sm">
            Roll: {orientation.roll.toFixed(1)}°
          </div>
          <div className="text-sm">
            Pitch: {orientation.pitch.toFixed(1)}°
          </div>
          <div className="text-sm">
            Yaw: {orientation.yaw.toFixed(1)}°
          </div>
        </div>
        
        <div ref={mountRef} className="w-full aspect-square" />
        
        <div className="flex justify-center mt-4 space-x-4">
          <div className="flex items-center">
            <div className="w-4 h-1 bg-red-500"></div>
            <span className="ml-2 text-sm">X (Red) - Roll</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-1 bg-green-500"></div>
            <span className="ml-2 text-sm">Y (Green) - Pitch</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-1 bg-blue-500"></div>
            <span className="ml-2 text-sm">Z (Blue) - Yaw</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default OrientationViewer;