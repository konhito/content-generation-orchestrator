import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { ScriptProps } from "../types/script";

interface TitleCardProps {
  title: string;
  subtitle?: string;
  style: ScriptProps["style"];
}

/**
 * Full-screen title card with dramatic reveal animation.
 */
export const TitleCard: React.FC<TitleCardProps> = ({ title, subtitle, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title animation
  const titleOpacity = interpolate(frame, [0, fps], [0, 1], {
    extrapolateRight: "clamp",
  });
  const titleScale = interpolate(frame, [0, fps], [0.8, 1], {
    extrapolateRight: "clamp",
  });

  // Subtitle animation (delayed)
  const subtitleOpacity = interpolate(frame, [fps * 0.8, fps * 1.5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subtitleY = interpolate(frame, [fps * 0.8, fps * 1.5], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Accent line animation
  const lineWidth = interpolate(frame, [fps * 0.3, fps * 1.2], [0, 200], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 30,
        backgroundColor: style.backgroundColor,
      }}
    >
      <h1
        style={{
          fontSize: 96,
          fontWeight: "bold",
          color: style.primaryColor,
          fontFamily: style.fontFamily,
          textAlign: "center",
          margin: 0,
          opacity: titleOpacity,
          transform: `scale(${titleScale})`,
          maxWidth: "80%",
        }}
      >
        {title}
      </h1>

      {/* Accent line */}
      <div
        style={{
          width: lineWidth,
          height: 4,
          backgroundColor: style.secondaryColor,
          borderRadius: 2,
        }}
      />

      {subtitle && (
        <p
          style={{
            fontSize: 36,
            color: "#cccccc",
            fontFamily: style.fontFamily,
            textAlign: "center",
            margin: 0,
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
            maxWidth: "70%",
            lineHeight: 1.5,
          }}
        >
          {subtitle}
        </p>
      )}
    </AbsoluteFill>
  );
};
