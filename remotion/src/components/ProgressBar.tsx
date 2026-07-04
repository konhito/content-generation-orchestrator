import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface ProgressBarProps {
  label: string;
  value: number; // 0 to 1
  color: string;
  backgroundColor?: string;
  width?: number;
  height?: number;
  showPercentage?: boolean;
}

/**
 * Animated progress/utilization bar with label.
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  label = "",
  value = 0,
  color = "#00d9ff",
  backgroundColor = "#333",
  width = 800,
  height = 40,
  showPercentage = true,
}) => {
  // Ensure value is a number
  const safeValue = typeof value === "number" ? value : 0;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animate the bar filling
  const animatedValue = interpolate(frame, [0, fps * 2], [0, safeValue], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Label fade in
  const labelOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateRight: "clamp",
  });

  const percentage = Math.round(animatedValue * 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          opacity: labelOpacity,
        }}
      >
        <span
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: "#ffffff",
            fontFamily: "Inter, sans-serif",
          }}
        >
          {label}
        </span>
        {showPercentage && (
          <span
            style={{
              fontSize: 24,
              fontWeight: 700,
              color: color,
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            {percentage}%
          </span>
        )}
      </div>
      <div
        style={{
          width,
          height,
          backgroundColor,
          borderRadius: height / 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${animatedValue * 100}%`,
            height: "100%",
            backgroundColor: color,
            borderRadius: height / 2,
            boxShadow: `0 0 20px ${color}60`,
            transition: "width 0.1s ease-out",
          }}
        />
      </div>
    </div>
  );
};
