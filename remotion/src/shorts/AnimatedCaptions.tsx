/**
 * AnimatedCaptions - Karaoke-style captions for shorts
 *
 * Features:
 * - Shows THREE words at a time
 * - Currently spoken word is highlighted
 * - Advances to next 3 words once current chunk is complete
 * - Large, eye-catching text optimized for mobile
 */

import React from "react";
import { interpolate, useVideoConfig } from "remotion";
import { SHORTS_COLORS, SHORTS_FONTS } from "./ShortsPlayer";

interface WordTimestamp {
  word: string;
  start_seconds: number;
  end_seconds: number;
}

interface AnimatedCaptionsProps {
  text: string;
  wordTimestamps: WordTimestamp[];
  currentTime: number;
  beatStartTime: number;
  scale: number;
}

export const AnimatedCaptions: React.FC<AnimatedCaptionsProps> = ({
  text,
  wordTimestamps,
  currentTime,
  beatStartTime,
  scale,
}) => {
  const { fps } = useVideoConfig();

  // Show THREE words at a time
  const WORDS_PER_CHUNK = 3;

  // If we have word timestamps, use them for highlighting
  const hasTimestamps = wordTimestamps.length > 0;

  // Split text into words for rendering
  const words = text.split(/\s+/).filter((w) => w.length > 0);

  // Calculate beat-local time (timestamps are relative to beat start)
  const beatLocalTime = currentTime - beatStartTime;

  // Determine which word is currently being spoken
  const getCurrentWordIndex = (): number => {
    if (!hasTimestamps) {
      // Without timestamps, highlight based on position in beat
      const beatDuration = 3; // Assume ~3 seconds per beat as fallback
      const beatProgress = beatLocalTime / beatDuration;
      return Math.floor(Math.min(beatProgress, 1) * words.length);
    }

    // Use beat-local time to compare against beat-relative timestamps
    for (let i = 0; i < wordTimestamps.length; i++) {
      const wt = wordTimestamps[i];
      if (beatLocalTime >= wt.start_seconds && beatLocalTime < wt.end_seconds) {
        return i;
      }
      if (beatLocalTime < wt.start_seconds) {
        return Math.max(0, i - 1);
      }
    }
    return wordTimestamps.length - 1;
  };

  const currentWordIndex = getCurrentWordIndex();

  // Determine which chunk of 3 words we're in
  const currentChunkIndex = Math.floor(currentWordIndex / WORDS_PER_CHUNK);

  // Get the start and end indices for the current chunk
  const chunkStart = currentChunkIndex * WORDS_PER_CHUNK;
  const chunkEnd = Math.min(chunkStart + WORDS_PER_CHUNK, words.length);

  // Get the words in the current chunk
  const chunkWords = words.slice(chunkStart, chunkEnd);

  const fadeIn = interpolate(beatLocalTime, [0, 0.2], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeIn,
        padding: `${8 * scale}px`,
      }}
    >
      {/* Three words in a row */}
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
          gap: `${32 * scale}px`,
          flexWrap: "wrap",
        }}
      >
        {chunkWords.map((word, indexInChunk) => {
          const globalIndex = chunkStart + indexInChunk;
          const isActive = globalIndex === currentWordIndex;
          const isPast = globalIndex < currentWordIndex;

          return (
            <span
              key={`${currentChunkIndex}-${indexInChunk}`}
              style={{
                fontSize: 36 * scale,
                fontFamily: SHORTS_FONTS.primary,
                fontWeight: isActive ? 700 : 500,
                color: isActive
                  ? SHORTS_COLORS.primary
                  : isPast
                    ? SHORTS_COLORS.text
                    : SHORTS_COLORS.textMuted,
                textShadow: isActive
                  ? `0 0 20px ${SHORTS_COLORS.primaryGlow}, 0 0 40px ${SHORTS_COLORS.primaryGlow}30`
                  : "none",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                transform: isActive ? "scale(1.1)" : "scale(1)",
                transition: "all 0.15s ease-out",
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
    </div>
  );
};

interface CaptionWordProps {
  word: string;
  isActive: boolean;
  isPast: boolean;
  isFuture: boolean;
  scale: number;
  fps: number;
  index: number;
  currentWordIndex: number;
}

const CaptionWord: React.FC<CaptionWordProps> = ({
  word,
  isActive,
  isPast,
  isFuture,
  scale,
  fps,
  index,
  currentWordIndex,
}) => {
  // Animation for active word
  const activeScale = isActive ? 1.05 : 1;

  // Color based on state
  let color = SHORTS_COLORS.textMuted; // Future words - dimmed
  if (isActive) {
    color = SHORTS_COLORS.primary; // Active word - highlighted
  } else if (isPast) {
    color = SHORTS_COLORS.text; // Past words - normal white
  }

  // Glow effect for active word
  const glowOpacity = isActive ? 0.8 : 0;

  return (
    <span
      style={{
        fontSize: 42 * scale,
        fontFamily: SHORTS_FONTS.primary,
        fontWeight: isActive ? 700 : 500,
        color,
        transform: `scale(${activeScale})`,
        transition: "all 0.15s ease-out",
        textShadow: isActive
          ? `0 0 20px ${SHORTS_COLORS.primaryGlow}, 0 0 40px ${SHORTS_COLORS.primaryGlow}40`
          : "none",
        display: "inline-block",
      }}
    >
      {word}
    </span>
  );
};

/**
 * Simplified captions without word-level sync
 * Shows text with a typewriter effect
 */
export const SimpleAnimatedCaptions: React.FC<{
  text: string;
  progress: number; // 0-1 progress through the beat
  scale: number;
}> = ({ text, progress, scale }) => {
  // Show more characters as progress increases
  const visibleLength = Math.floor(text.length * Math.min(progress * 1.5, 1));
  const visibleText = text.slice(0, visibleLength);

  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        justifyContent: "center",
        padding: `${20 * scale}px`,
      }}
    >
      <div
        style={{
          background: "rgba(0, 0, 0, 0.6)",
          backdropFilter: "blur(10px)",
          borderRadius: 16 * scale,
          padding: `${24 * scale}px ${32 * scale}px`,
          maxWidth: 1000 * scale,
        }}
      >
        <div
          style={{
            fontSize: 42 * scale,
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 600,
            color: SHORTS_COLORS.text,
            textAlign: "center",
            lineHeight: 1.4,
          }}
        >
          {visibleText}
          {visibleLength < text.length && (
            <span
              style={{
                opacity: 0.5,
                animation: "blink 0.5s infinite",
              }}
            >
              |
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnimatedCaptions;
