import React from "react";
import {
  interpolate,
  useCurrentFrame,
  Easing,
} from "remotion";

export type GaugeStatus = "compute" | "memory" | "neutral";

export interface GPUGaugeProps {
  utilization: number; // 0-100
  animateAt?: number; // Frame at which to start filling
  animationDuration?: number; // Frames to complete animation
  status?: GaugeStatus;
  showLabel?: boolean;
  showPercentage?: boolean;
  label?: string;
  style?: React.CSSProperties;
}

export const GPUGauge: React.FC<GPUGaugeProps> = ({
  utilization,
  animateAt = 0,
  animationDuration = 20,
  status = "neutral",
  showLabel = true,
  showPercentage = true,
  label = "GPU Compute",
  style = {},
}) => {
  const frame = useCurrentFrame();

  // Animate the fill
  const fillProgress = interpolate(
    frame,
    [animateAt, animateAt + animationDuration],
    [0, utilization],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    }
  );

  // Fade in
  const opacity = interpolate(frame, [animateAt - 10, animateAt], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Status colors
  const statusColors: Record<GaugeStatus, { bar: string; glow: string; text: string }> = {
    compute: {
      bar: "#00ff88",
      glow: "rgba(0, 255, 136, 0.4)",
      text: "#00ff88",
    },
    memory: {
      bar: "#ff4757",
      glow: "rgba(255, 71, 87, 0.4)",
      text: "#ff4757",
    },
    neutral: {
      bar: "#00d9ff",
      glow: "rgba(0, 217, 255, 0.4)",
      text: "#00d9ff",
    },
  };

  const colors = statusColors[status];

  // Status label
  const statusLabel = status === "compute" ? "COMPUTE BOUND" : status === "memory" ? "MEMORY BOUND" : "";

  // Show status label after fill completes
  const statusLabelOpacity = interpolate(
    frame,
    [animateAt + animationDuration, animateAt + animationDuration + 10],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        opacity,
        ...style,
      }}
    >
      {/* Label */}
      {showLabel && (
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 20,
            fontWeight: 500,
            color: "#a0a0a0",
          }}
        >
          {label}
        </div>
      )}

      {/* Gauge container */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* Bar background */}
        <div
          style={{
            width: 300,
            height: 32,
            backgroundColor: "#1a1a2e",
            borderRadius: 6,
            overflow: "hidden",
            border: "1px solid #3a3a4a",
          }}
        >
          {/* Bar fill */}
          <div
            style={{
              width: `${fillProgress}%`,
              height: "100%",
              backgroundColor: colors.bar,
              boxShadow: `0 0 20px ${colors.glow}`,
              transition: "width 0.05s linear",
            }}
          />
        </div>

        {/* Percentage */}
        {showPercentage && (
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 24,
              fontWeight: 600,
              color: colors.text,
              minWidth: 70,
            }}
          >
            {Math.round(fillProgress)}%
          </div>
        )}
      </div>

      {/* Status label */}
      {statusLabel && (
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 18,
            fontWeight: 600,
            color: colors.text,
            textTransform: "uppercase",
            letterSpacing: 2,
            opacity: statusLabelOpacity,
          }}
        >
          {statusLabel}
        </div>
      )}
    </div>
  );
};

export default GPUGauge;
