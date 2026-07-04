import React from "react";
import { ThreeCanvas } from "@remotion/three";
import { useVideoConfig } from "remotion";
import { PerspectiveCamera } from "@react-three/drei";

export interface ThreeSceneWrapperProps {
  children: React.ReactNode;
  cameraPosition?: [number, number, number];
  cameraFov?: number;
  enableDefaultLights?: boolean;
  backgroundColor?: string;
}

export const ThreeSceneWrapper: React.FC<ThreeSceneWrapperProps> = ({
  children,
  cameraPosition = [0, 0, 10],
  cameraFov = 50,
  enableDefaultLights = true,
  backgroundColor = "transparent",
}) => {
  const { width, height } = useVideoConfig();

  return (
    <ThreeCanvas
      width={width}
      height={height}
      style={{ backgroundColor }}
    >
      <PerspectiveCamera
        makeDefault
        position={cameraPosition}
        fov={cameraFov}
      />
      {enableDefaultLights && (
        <>
          <ambientLight intensity={0.4} />
          <directionalLight position={[10, 10, 5]} intensity={0.8} />
        </>
      )}
      {children}
    </ThreeCanvas>
  );
};
