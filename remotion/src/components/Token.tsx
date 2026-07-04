import React from "react";
import {
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
  Easing,
} from "remotion";

export interface TokenProps {
  text: string;
  isActive: boolean;
  activateAt?: number; // Frame at which to activate
  index?: number;
  style?: React.CSSProperties;
}

export const Token: React.FC<TokenProps> = ({
  text,
  isActive,
  activateAt = 0,
  index = 0,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Determine if we should be active based on frame
  const shouldBeActive = isActive && frame >= activateAt;

  // Fade in animation
  const fadeInDelay = index * 3; // Stagger by 3 frames
  const opacity = interpolate(frame, [fadeInDelay, fadeInDelay + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Activation animation (color change + glow)
  const activationProgress = shouldBeActive
    ? interpolate(frame, [activateAt, activateAt + 8], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      })
    : 0;

  // Pulse animation when active
  const pulseScale = shouldBeActive
    ? 1 +
      0.05 *
        Math.sin(
          ((frame - activateAt) / fps) * Math.PI * 2
        ) *
        Math.max(0, 1 - (frame - activateAt) / 30)
    : 1;

  // Colors
  const inactiveColor = "#3a3a4a";
  const activeColor = "#00d9ff";
  const backgroundColor = shouldBeActive
    ? interpolateColor(inactiveColor, activeColor, activationProgress)
    : inactiveColor;

  // Glow effect
  const glowIntensity = activationProgress * 20;
  const boxShadow = shouldBeActive
    ? `0 0 ${glowIntensity}px ${glowIntensity / 2}px rgba(0, 217, 255, ${activationProgress * 0.6})`
    : "none";

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "12px 20px",
        borderRadius: 8,
        backgroundColor,
        opacity,
        transform: `scale(${pulseScale})`,
        boxShadow,
        transition: "background-color 0.1s",
        ...style,
      }}
    >
      <span
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          fontWeight: 500,
          color: shouldBeActive ? "#ffffff" : "#a0a0a0",
        }}
      >
        {text}
      </span>
    </div>
  );
};

// Helper function to interpolate between two hex colors
function interpolateColor(
  color1: string,
  color2: string,
  progress: number
): string {
  const r1 = parseInt(color1.slice(1, 3), 16);
  const g1 = parseInt(color1.slice(3, 5), 16);
  const b1 = parseInt(color1.slice(5, 7), 16);

  const r2 = parseInt(color2.slice(1, 3), 16);
  const g2 = parseInt(color2.slice(3, 5), 16);
  const b2 = parseInt(color2.slice(5, 7), 16);

  const r = Math.round(r1 + (r2 - r1) * progress);
  const g = Math.round(g1 + (g2 - g1) * progress);
  const b = Math.round(b1 + (b2 - b1) * progress);

  return `rgb(${r}, ${g}, ${b})`;
}

export default Token;
