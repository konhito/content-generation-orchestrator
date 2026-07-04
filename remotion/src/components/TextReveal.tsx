import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface TextRevealProps {
  text: string;
  style?: React.CSSProperties;
  delay?: number; // delay in frames
  duration?: number; // duration in frames
}

/**
 * Text component with fade-in and slide-up animation.
 */
export const TextReveal: React.FC<TextRevealProps> = ({
  text,
  style = {},
  delay = 0,
  duration,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const animDuration = duration ?? fps * 0.8;
  const adjustedFrame = frame - delay;

  const opacity = interpolate(adjustedFrame, [0, animDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(adjustedFrame, [0, animDuration], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        ...style,
      }}
    >
      {text}
    </div>
  );
};
