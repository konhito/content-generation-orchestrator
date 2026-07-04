/**
 * ShortsSceneComponents - Scene components adapted for vertical shorts format
 *
 * These wrap existing components and adapt them for:
 * - 1080x1920 vertical format
 * - Top 70% visual area (1344px height)
 * - Mobile-optimized sizing
 */

import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { SHORTS_COLORS, SHORTS_FONTS } from "./ShortsPlayer";

interface ShortsTokenGridProps {
  tokens?: string[];
  mode: "prefill" | "decode";
  rows?: number;
  cols?: number;
  scale: number;
  label?: string;
}

/**
 * Token Grid for shorts - shows prefill vs decode mode
 * Designed to fill visual area with bold, animated tokens
 */
export const ShortsTokenGrid: React.FC<ShortsTokenGridProps> = ({
  tokens = [],
  mode = "prefill",
  rows = 8,
  cols = 8,
  scale,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const totalCells = rows * cols;
  // Calculate cell size to fill available space
  const availableWidth = 950 * scale;
  const gap = 6 * scale;
  const cellSize = Math.floor((availableWidth - (cols - 1) * gap) / cols);

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  // Pulsing glow effect
  const pulseIntensity = 0.7 + Math.sin(frame * 0.1) * 0.3;

  const getCellAnimation = (index: number) => {
    if (mode === "prefill") {
      // All cells animate together with slight wave
      const row = Math.floor(index / cols);
      const col = index % cols;
      const waveDelay = (row + col) * 2;
      return interpolate(frame - waveDelay, [fps * 0.1, fps * 0.5], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }

    // Sequential: each cell has staggered animation
    const cellDelay = (index / totalCells) * (durationInFrames * 0.5);
    const cellDuration = fps * 0.3;
    return interpolate(frame, [cellDelay, cellDelay + cellDuration], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  };

  const tokenColor = mode === "prefill" ? SHORTS_COLORS.primary : SHORTS_COLORS.secondary;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
      }}
    >
      {/* Grid - fills visual area */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
          gap: gap,
          padding: 12 * scale,
          backgroundColor: `${tokenColor}08`,
          borderRadius: 16 * scale,
          boxShadow: `0 0 ${60 * pulseIntensity * scale}px ${tokenColor}20`,
        }}
      >
        {Array.from({ length: totalCells }).map((_, index) => {
          const progress = getCellAnimation(index);

          return (
            <div
              key={index}
              style={{
                width: cellSize,
                height: cellSize,
                borderRadius: 8 * scale,
                background: `linear-gradient(135deg, ${tokenColor}, ${tokenColor}90)`,
                opacity: progress,
                transform: `scale(${0.3 + progress * 0.7})`,
                boxShadow: `0 0 ${20 * scale}px ${tokenColor}60, inset 0 0 ${15 * scale}px rgba(255,255,255,0.1)`,
                border: `2px solid ${tokenColor}`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

interface ShortsProgressBarsProps {
  bars: Array<{
    label: string;
    value: number;
    color?: string;
  }>;
  scale: number;
}

/**
 * Progress Bars for shorts - stacked vertically
 */
export const ShortsProgressBars: React.FC<ShortsProgressBarsProps> = ({
  bars = [],
  scale,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  const barWidth = 700 * scale;
  const barHeight = 36 * scale;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 32 * scale,
        opacity: entryProgress,
      }}
    >
      {bars.map((bar, index) => {
        const delay = index * 10;
        const animatedValue = interpolate(
          frame - delay,
          [fps * 0.3, fps * 1.5],
          [0, bar.value],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        const color = bar.color || SHORTS_COLORS.primary;

        return (
          <div
            key={index}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 12 * scale,
            }}
          >
            {/* Label and percentage */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: 24 * scale,
                  fontFamily: SHORTS_FONTS.primary,
                  fontWeight: 600,
                  color: SHORTS_COLORS.text,
                }}
              >
                {bar.label}
              </span>
              <span
                style={{
                  fontSize: 24 * scale,
                  fontFamily: SHORTS_FONTS.mono,
                  fontWeight: 700,
                  color: color,
                }}
              >
                {Math.round(animatedValue * 100)}%
              </span>
            </div>

            {/* Bar */}
            <div
              style={{
                width: barWidth,
                height: barHeight,
                backgroundColor: "rgba(255,255,255,0.1)",
                borderRadius: barHeight / 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${animatedValue * 100}%`,
                  height: "100%",
                  backgroundColor: color,
                  borderRadius: barHeight / 2,
                  boxShadow: `0 0 ${20 * scale}px ${color}60`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

interface ShortsCodeBlockProps {
  code: string;
  language?: string;
  highlightLines?: number[];
  scale: number;
}

/**
 * Code Block for shorts - syntax highlighted with animation
 */
export const ShortsCodeBlock: React.FC<ShortsCodeBlockProps> = ({
  code = "",
  language = "python",
  highlightLines = [],
  scale,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  const lines = code.split("\n");

  // Simple syntax highlighting colors
  const keywordColor = SHORTS_COLORS.primary;
  const stringColor = SHORTS_COLORS.success;
  const commentColor = SHORTS_COLORS.textMuted;
  const numberColor = SHORTS_COLORS.warning;

  return (
    <div
      style={{
        backgroundColor: "rgba(0,0,0,0.6)",
        backdropFilter: "blur(10px)",
        borderRadius: 16 * scale,
        padding: `${24 * scale}px ${32 * scale}px`,
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
        maxWidth: 900 * scale,
        overflow: "hidden",
      }}
    >
      {/* Language tag */}
      <div
        style={{
          fontSize: 14 * scale,
          fontFamily: SHORTS_FONTS.mono,
          color: SHORTS_COLORS.primary,
          marginBottom: 16 * scale,
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        {language}
      </div>

      {/* Code lines */}
      <div
        style={{
          fontFamily: SHORTS_FONTS.mono,
          fontSize: 20 * scale,
          lineHeight: 1.5,
        }}
      >
        {lines.map((line, index) => {
          const lineDelay = index * 3;
          const lineOpacity = interpolate(
            frame - lineDelay,
            [fps * 0.2, fps * 0.5],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          const isHighlighted = highlightLines.includes(index + 1);

          return (
            <div
              key={index}
              style={{
                opacity: lineOpacity,
                color: SHORTS_COLORS.text,
                backgroundColor: isHighlighted
                  ? `${SHORTS_COLORS.primary}20`
                  : "transparent",
                padding: `${4 * scale}px ${8 * scale}px`,
                marginLeft: -8 * scale,
                marginRight: -8 * scale,
                borderLeft: isHighlighted
                  ? `3px solid ${SHORTS_COLORS.primary}`
                  : "3px solid transparent",
              }}
            >
              {line || " "}
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface ShortsDiagramProps {
  nodes: string[];
  arrows?: boolean;
  direction?: "horizontal" | "vertical";
  scale: number;
}

/**
 * Simple diagram/flow for shorts
 */
export const ShortsDiagram: React.FC<ShortsDiagramProps> = ({
  nodes = [],
  arrows = true,
  direction = "vertical",
  scale,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isVertical = direction === "vertical";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isVertical ? "column" : "row",
        alignItems: "center",
        gap: 16 * scale,
      }}
    >
      {nodes.map((node, index) => {
        const delay = index * 15;
        const progress = interpolate(frame - delay, [0, fps * 0.5], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        const isLast = index === nodes.length - 1;
        const nodeColor = isLast ? SHORTS_COLORS.primary : SHORTS_COLORS.text;

        return (
          <React.Fragment key={index}>
            {/* Node */}
            <div
              style={{
                backgroundColor: isLast
                  ? `${SHORTS_COLORS.primary}20`
                  : "rgba(255,255,255,0.05)",
                border: `2px solid ${isLast ? SHORTS_COLORS.primary : "rgba(255,255,255,0.1)"}`,
                borderRadius: 16 * scale,
                padding: `${20 * scale}px ${40 * scale}px`,
                opacity: progress,
                transform: `scale(${0.8 + progress * 0.2})`,
              }}
            >
              <span
                style={{
                  fontSize: 28 * scale,
                  fontFamily: SHORTS_FONTS.primary,
                  fontWeight: 600,
                  color: nodeColor,
                }}
              >
                {node}
              </span>
            </div>

            {/* Arrow */}
            {arrows && !isLast && (
              <div
                style={{
                  fontSize: 32 * scale,
                  color: SHORTS_COLORS.primary,
                  opacity: progress,
                }}
              >
                {isVertical ? "↓" : "→"}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

interface ShortsImageProps {
  src: string;
  caption?: string;
  scale: number;
}

/**
 * Image with caption for shorts
 */
export const ShortsImage: React.FC<ShortsImageProps> = ({
  src,
  caption,
  scale,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 24 * scale,
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
      }}
    >
      {/* Image container */}
      <div
        style={{
          maxWidth: 800 * scale,
          maxHeight: 600 * scale,
          borderRadius: 16 * scale,
          overflow: "hidden",
          boxShadow: `0 0 ${40 * scale}px rgba(0,0,0,0.5)`,
        }}
      >
        <img
          src={src}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
          }}
        />
      </div>

      {/* Caption */}
      {caption && (
        <div
          style={{
            fontSize: 24 * scale,
            fontFamily: SHORTS_FONTS.primary,
            color: SHORTS_COLORS.textMuted,
            textAlign: "center",
            maxWidth: 800 * scale,
          }}
        >
          {caption}
        </div>
      )}
    </div>
  );
};

interface ShortsPatchGridProps {
  rows?: number;
  cols?: number;
  scale: number;
  label?: string;
  showDividers?: boolean;
  highlightPatches?: number[];
}

/**
 * Patch Grid - Shows image divided into patches (like Vision Transformer)
 * Designed to fill most of the visual area (1080x1344)
 */
export const ShortsPatchGrid: React.FC<ShortsPatchGridProps> = ({
  rows = 8,
  cols = 8,
  scale,
  label,
  showDividers = true,
  highlightPatches = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  const totalPatches = rows * cols;
  // Calculate patch size to fill available width (~1000px usable)
  const availableWidth = 950 * scale;
  const patchSize = Math.floor((availableWidth - (cols - 1) * 6 * scale) / cols);
  const gap = 6 * scale;

  // Colors for patches - gradient from primary to accent
  const getColor = (index: number) => {
    const colors = [
      SHORTS_COLORS.primary,
      "#00b4d8",
      "#0096c7",
      "#0077b6",
      SHORTS_COLORS.accent,
      "#7c3aed",
      "#6d28d9",
      "#5b21b6",
    ];
    return colors[index % colors.length];
  };

  // Pulsing glow effect
  const pulseIntensity = 0.7 + Math.sin(frame * 0.1) * 0.3;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
      }}
    >
      {/* Grid container - no labels, just the visual */}
      <div
        style={{
          position: "relative",
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, ${patchSize}px)`,
          gridTemplateRows: `repeat(${rows}, ${patchSize}px)`,
          gap: gap,
          padding: 12 * scale,
          backgroundColor: "rgba(0, 212, 255, 0.03)",
          borderRadius: 16 * scale,
          boxShadow: `0 0 ${60 * pulseIntensity * scale}px rgba(0, 212, 255, 0.15)`,
        }}
      >
        {Array.from({ length: totalPatches }).map((_, index) => {
          const row = Math.floor(index / cols);
          const col = index % cols;
          const delay = (row + col) * 2;

          const patchProgress = interpolate(
            frame - delay,
            [fps * 0.1, fps * 0.5],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          const isHighlighted = highlightPatches.includes(index);
          const color = getColor(index);

          return (
            <div
              key={index}
              style={{
                width: patchSize,
                height: patchSize,
                borderRadius: 8 * scale,
                background: `linear-gradient(135deg, ${color}, ${color}90)`,
                opacity: patchProgress,
                transform: `scale(${0.3 + patchProgress * 0.7})`,
                border: isHighlighted
                  ? `3px solid ${SHORTS_COLORS.warning}`
                  : `2px solid ${color}`,
                boxShadow: isHighlighted
                  ? `0 0 ${30 * scale}px ${SHORTS_COLORS.warning}`
                  : `0 0 ${20 * scale}px ${color}60, inset 0 0 ${15 * scale}px rgba(255,255,255,0.1)`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

interface ShortsEmbeddingBarsProps {
  dimensions?: number;
  values?: number[];
  scale: number;
  label?: string;
}

/**
 * Embedding Bars - Animated bars showing embedding vector dimensions
 * Designed to fill most of the visual area with bold, animated bars
 */
export const ShortsEmbeddingBars: React.FC<ShortsEmbeddingBarsProps> = ({
  dimensions = 16,
  values,
  scale,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  // Calculate bar width to fill available space
  const availableWidth = 950 * scale;
  const gap = 6 * scale;
  const barWidth = Math.floor((availableWidth - (dimensions - 1) * gap) / dimensions);
  const maxHeight = 600 * scale;

  // Generate random-ish values if not provided
  const barValues = values || Array.from({ length: dimensions }, (_, i) =>
    0.3 + Math.sin(i * 1.5) * 0.3 + Math.cos(i * 0.8) * 0.2
  );

  // Pulsing glow effect
  const pulseIntensity = 0.7 + Math.sin(frame * 0.08) * 0.3;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
      }}
    >
      {/* Bars container - fills visual area */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          gap: gap,
          height: maxHeight + 40 * scale,
          padding: `${20 * scale}px`,
          backgroundColor: "rgba(0, 212, 255, 0.03)",
          borderRadius: 16 * scale,
          boxShadow: `0 0 ${60 * pulseIntensity * scale}px rgba(0, 212, 255, 0.15)`,
        }}
      >
        {barValues.slice(0, dimensions).map((value, index) => {
          const delay = index * 3;
          const barProgress = interpolate(
            frame - delay,
            [fps * 0.2, fps * 0.8],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          const animatedHeight = value * maxHeight * barProgress;

          // Color gradient based on position
          const hue = 180 + (index / dimensions) * 80; // Cyan to purple
          const color = `hsl(${hue}, 80%, 60%)`;

          return (
            <div
              key={index}
              style={{
                width: barWidth,
                height: animatedHeight,
                background: `linear-gradient(180deg, ${color}, ${color}90)`,
                borderRadius: `${6 * scale}px ${6 * scale}px 0 0`,
                boxShadow: `0 0 ${25 * scale}px ${color}60, inset 0 0 ${10 * scale}px rgba(255,255,255,0.1)`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

interface ShortsAttentionVisualProps {
  size?: number;
  scale: number;
  label?: string;
  pattern?: "self" | "cross" | "causal";
}

/**
 * Attention Visual - Shows attention pattern/heatmap
 * Designed to fill visual area with bold, glowing attention matrix
 */
export const ShortsAttentionVisual: React.FC<ShortsAttentionVisualProps> = ({
  size = 12,
  scale,
  label,
  pattern = "self",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  // Calculate cell size to fill available space
  const availableWidth = 900 * scale;
  const gap = 3 * scale;
  const cellSize = Math.floor((availableWidth - (size - 1) * gap) / size);

  // Pulsing glow effect
  const pulseIntensity = 0.7 + Math.sin(frame * 0.08) * 0.3;

  // Generate attention weights based on pattern (seeded by frame for consistency)
  const getWeight = (row: number, col: number): number => {
    const seed = row * 100 + col;
    const pseudoRandom = Math.sin(seed * 12.9898) * 0.5 + 0.5;

    if (pattern === "causal") {
      return col <= row ? 0.3 + pseudoRandom * 0.7 : 0;
    } else if (pattern === "cross") {
      return Math.abs(row - col) <= 1 ? 0.6 + pseudoRandom * 0.4 : pseudoRandom * 0.3;
    } else {
      const dist = Math.abs(row - col);
      return Math.max(0.1, 1 - dist * 0.1 + pseudoRandom * 0.2);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
      }}
    >
      {/* Attention matrix - fills visual area */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${size}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${size}, ${cellSize}px)`,
          gap: gap,
          padding: 12 * scale,
          backgroundColor: "rgba(0, 212, 255, 0.03)",
          borderRadius: 16 * scale,
          boxShadow: `0 0 ${60 * pulseIntensity * scale}px rgba(0, 212, 255, 0.15)`,
        }}
      >
        {Array.from({ length: size * size }).map((_, index) => {
          const row = Math.floor(index / size);
          const col = index % size;
          const weight = getWeight(row, col);

          const delay = (row + col) * 1.5;
          const cellProgress = interpolate(
            frame - delay,
            [fps * 0.1, fps * 0.6],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          const animatedWeight = weight * cellProgress;

          // Color based on weight intensity
          const hue = 180 + animatedWeight * 40;
          const color = `hsl(${hue}, 80%, ${50 + animatedWeight * 20}%)`;

          return (
            <div
              key={index}
              style={{
                width: cellSize,
                height: cellSize,
                borderRadius: 4 * scale,
                background: `linear-gradient(135deg, ${color}, ${color}80)`,
                opacity: 0.2 + animatedWeight * 0.8,
                boxShadow: animatedWeight > 0.5
                  ? `0 0 ${15 * scale}px ${color}60, inset 0 0 ${8 * scale}px rgba(255,255,255,0.1)`
                  : `inset 0 0 ${5 * scale}px rgba(255,255,255,0.05)`,
                transform: `scale(${0.3 + cellProgress * 0.7})`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

interface ShortsMaskedGridProps {
  rows?: number;
  cols?: number;
  maskedIndices?: number[];
  scale: number;
  label?: string;
}

/**
 * Masked Grid - Shows tokens with some masked (like BERT/MAE)
 * Designed to fill visual area with bold, animated masked/visible cells
 */
export const ShortsMaskedGrid: React.FC<ShortsMaskedGridProps> = ({
  rows = 8,
  cols = 8,
  maskedIndices = [5, 10, 18, 23, 30, 37, 42, 51, 58],
  scale,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entryProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  const totalCells = rows * cols;
  // Calculate cell size to fill available space
  const availableWidth = 950 * scale;
  const gap = 6 * scale;
  const cellSize = Math.floor((availableWidth - (cols - 1) * gap) / cols);

  // Pulsing glow effect
  const pulseIntensity = 0.7 + Math.sin(frame * 0.1) * 0.3;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: entryProgress,
        transform: `scale(${0.95 + entryProgress * 0.05})`,
      }}
    >
      {/* Grid - fills visual area */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
          gap: gap,
          padding: 12 * scale,
          backgroundColor: "rgba(0, 212, 255, 0.03)",
          borderRadius: 16 * scale,
          boxShadow: `0 0 ${60 * pulseIntensity * scale}px rgba(0, 212, 255, 0.15)`,
        }}
      >
        {Array.from({ length: totalCells }).map((_, index) => {
          const isMasked = maskedIndices.includes(index);
          const row = Math.floor(index / cols);
          const col = index % cols;
          const delay = (row + col) * 2;

          const cellProgress = interpolate(
            frame - delay,
            [fps * 0.1, fps * 0.5],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          // Masked cells have a stronger pulsing effect
          const maskPulse = isMasked ? 0.6 + Math.sin(frame * 0.15 + index) * 0.4 : 1;

          // Colors
          const visibleColor = SHORTS_COLORS.primary;
          const maskedColor = SHORTS_COLORS.warning;

          return (
            <div
              key={index}
              style={{
                width: cellSize,
                height: cellSize,
                borderRadius: 8 * scale,
                background: isMasked
                  ? `linear-gradient(135deg, ${maskedColor}50, ${maskedColor}30)`
                  : `linear-gradient(135deg, ${visibleColor}, ${visibleColor}90)`,
                border: isMasked
                  ? `3px dashed ${maskedColor}`
                  : `2px solid ${visibleColor}`,
                opacity: cellProgress * maskPulse,
                transform: `scale(${0.3 + cellProgress * 0.7})`,
                boxShadow: isMasked
                  ? `0 0 ${25 * maskPulse * scale}px ${maskedColor}60`
                  : `0 0 ${20 * scale}px ${visibleColor}60, inset 0 0 ${15 * scale}px rgba(255,255,255,0.1)`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: isMasked ? 32 * scale : 0,
                fontFamily: SHORTS_FONTS.mono,
                color: maskedColor,
                fontWeight: 700,
              }}
            >
              {isMasked ? "?" : ""}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default {
  ShortsTokenGrid,
  ShortsProgressBars,
  ShortsCodeBlock,
  ShortsDiagram,
  ShortsImage,
  ShortsPatchGrid,
  ShortsEmbeddingBars,
  ShortsAttentionVisual,
  ShortsMaskedGrid,
};
