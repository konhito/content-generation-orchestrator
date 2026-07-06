/**
 * ShortsProgressBar - Thin progress indicator at bottom of shorts
 */

import React from "react";
import { SHORTS_COLORS } from "./ShortsPlayer";

interface ShortsProgressBarProps {
  progress: number; // 0-1
  scale: number;
  height?: number;
}

export const ShortsProgressBar: React.FC<ShortsProgressBarProps> = ({
  progress,
  scale,
  height = 8,
}) => {
  // Clamp progress
  const clampedProgress = Math.max(0, Math.min(1, progress));

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: height * scale,
        background: "rgba(148, 163, 184, 0.22)",
      }}
    >
      {/* Progress fill */}
      <div
        style={{
          height: "100%",
          width: `${clampedProgress * 100}%`,
          background: `linear-gradient(90deg, ${SHORTS_COLORS.primary} 0%, ${SHORTS_COLORS.accent} 100%)`,
          boxShadow: `0 -4px 18px ${SHORTS_COLORS.primaryGlow}`,
          transition: "width 0.1s linear",
        }}
      />
    </div>
  );
};

export default ShortsProgressBar;
