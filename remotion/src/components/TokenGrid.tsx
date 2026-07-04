import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface TokenGridProps {
  rows: number;
  cols: number;
  tokenColor: string;
  backgroundColor: string;
  animationMode: "sequential" | "parallel" | "none";
  cellSize?: number;
  gap?: number;
}

/**
 * Grid of tokens that animate in different patterns.
 * - sequential: tokens light up one by one (decode mode)
 * - parallel: all tokens light up at once (prefill mode)
 */
export const TokenGrid: React.FC<TokenGridProps> = ({
  rows,
  cols,
  tokenColor,
  backgroundColor,
  animationMode,
  cellSize = 60,
  gap = 8,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const totalCells = rows * cols;

  // Calculate animation progress for each cell
  const getCellOpacity = (index: number): number => {
    if (animationMode === "none") return 1;

    if (animationMode === "parallel") {
      // All cells animate together
      return interpolate(frame, [fps * 0.5, fps * 1.5], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }

    // Sequential: each cell has a staggered animation
    const cellDelay = (index / totalCells) * (durationInFrames * 0.6);
    const cellDuration = fps * 0.3;
    return interpolate(
      frame,
      [cellDelay, cellDelay + cellDuration],
      [0, 1],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }
    );
  };

  const getCellScale = (index: number): number => {
    if (animationMode === "none") return 1;

    if (animationMode === "parallel") {
      return interpolate(frame, [fps * 0.5, fps * 1.5], [0.5, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }

    const cellDelay = (index / totalCells) * (durationInFrames * 0.6);
    const cellDuration = fps * 0.3;
    return interpolate(
      frame,
      [cellDelay, cellDelay + cellDuration],
      [0.5, 1],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }
    );
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
        gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
        gap: gap,
      }}
    >
      {Array.from({ length: totalCells }).map((_, index) => (
        <div
          key={index}
          style={{
            width: cellSize,
            height: cellSize,
            borderRadius: 8,
            backgroundColor: tokenColor,
            opacity: getCellOpacity(index),
            transform: `scale(${getCellScale(index)})`,
            boxShadow: `0 0 20px ${tokenColor}40`,
          }}
        />
      ))}
    </div>
  );
};
