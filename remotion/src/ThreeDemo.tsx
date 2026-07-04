import React, { useRef } from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { ThreeSceneWrapper } from "./components/three";
import { useFrame } from "@react-three/fiber";
import { Mesh, MeshStandardMaterial } from "three";

// Animated rotating cube component
const RotatingCube: React.FC<{ color: string; position: [number, number, number] }> = ({
  color,
  position,
}) => {
  const meshRef = useRef<Mesh>(null);
  const frame = useCurrentFrame();

  // Rotate based on Remotion frame
  const rotation = (frame / 30) * Math.PI * 0.5;

  return (
    <mesh ref={meshRef} position={position} rotation={[rotation * 0.5, rotation, 0]}>
      <boxGeometry args={[1.5, 1.5, 1.5]} />
      <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
    </mesh>
  );
};

// Floating sphere with pulsing animation
const PulsingSphere: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = 1 + Math.sin(frame * 0.1) * 0.2;
  const y = Math.sin(frame * 0.05) * 0.5;

  return (
    <mesh position={[3, y, 0]} scale={[pulse, pulse, pulse]}>
      <sphereGeometry args={[0.8, 32, 32]} />
      <meshStandardMaterial color="#00d4ff" metalness={0.5} roughness={0.2} />
    </mesh>
  );
};

// Torus that rotates on a different axis
const SpinningTorus: React.FC = () => {
  const frame = useCurrentFrame();
  const rotation = (frame / 30) * Math.PI;

  return (
    <mesh position={[-3, 0, 0]} rotation={[Math.PI / 2, rotation, 0]}>
      <torusGeometry args={[0.8, 0.3, 16, 48]} />
      <meshStandardMaterial color="#ff6b6b" metalness={0.4} roughness={0.3} />
    </mesh>
  );
};

// Grid floor for depth perception
const GridFloor: React.FC = () => {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.5, 0]}>
      <planeGeometry args={[20, 20, 20, 20]} />
      <meshStandardMaterial color="#1a1a2e" wireframe opacity={0.3} transparent />
    </mesh>
  );
};

// Main demo composition
export const ThreeDemo: React.FC = () => {
  const frame = useCurrentFrame();

  // Camera slowly orbits
  const cameraAngle = (frame / 300) * Math.PI * 2;
  const cameraX = Math.sin(cameraAngle) * 8;
  const cameraZ = Math.cos(cameraAngle) * 8;

  // Title fade in
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {/* 3D Scene */}
      <ThreeSceneWrapper
        cameraPosition={[cameraX, 3, cameraZ]}
        cameraFov={60}
        backgroundColor="#0f0f1a"
      >
        <RotatingCube color="#6c5ce7" position={[0, 0, 0]} />
        <PulsingSphere />
        <SpinningTorus />
        <GridFloor />

        {/* Extra ambient light for better visibility */}
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={0.5} color="#ffffff" />
        <pointLight position={[-5, 3, -5]} intensity={0.3} color="#00d4ff" />
      </ThreeSceneWrapper>

      {/* Overlay title */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
          fontFamily: "Inter, sans-serif",
          color: "white",
          fontSize: 48,
          fontWeight: 700,
          textShadow: "0 2px 20px rgba(0,0,0,0.5)",
        }}
      >
        Three.js Demo
      </div>

      {/* Subtitle */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
          fontFamily: "Inter, sans-serif",
          color: "rgba(255,255,255,0.7)",
          fontSize: 24,
        }}
      >
        Hybrid 2D/3D Remotion Scene
      </div>
    </div>
  );
};
