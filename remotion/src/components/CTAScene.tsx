/**
 * CTAScene - Reusable Call-to-Action component for YouTube Shorts
 *
 * Creates maximum engagement through:
 * 1. Hook Question (0-2s): Large text fades in with emphasis
 * 2. Thumbnail Preview (2-4s): Slides up from bottom
 * 3. Teaser Cuts (4-5s): Quick 0.3s flashes
 * 4. CTA Text (5-7s): Animated with bouncing arrow
 * 5. Voiceover: "Want to know how they solved this? Full breakdown in the description."
 */

import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Sequence,
} from "remotion";

// Default colors (can be overridden via props)
const DEFAULT_COLORS = {
  background: "#FAFAFA",
  text: "#1A1A1A",
  textMuted: "#888888",
  primary: "#0066FF",
  primaryGlow: "#0088FF",
  purple: "#8844FF",
  glowMedium: "rgba(0, 102, 255, 0.3)",
  glowStrong: "rgba(0, 102, 255, 0.5)",
  shadow: "rgba(0, 0, 0, 0.08)",
};

// Default fonts
const DEFAULT_FONTS = {
  heading: '"Outfit", -apple-system, BlinkMacSystemFont, sans-serif',
  primary: '"Outfit", -apple-system, BlinkMacSystemFont, sans-serif',
};

export interface CTASceneProps {
  /** Frame offset for when this scene starts */
  startFrame?: number;
  /** Optional thumbnail URL - if not provided, shows gradient placeholder */
  thumbnailUrl?: string;
  /** Main CTA text shown below thumbnail */
  ctaText: string;
  /** Hook question shown at top - creates curiosity */
  hookQuestion: string;
  /** Optional channel name shown at bottom */
  channelName?: string;
  /** Optional teaser frame URLs for quick flashes */
  teaserClips?: string[];
  /** Optional color overrides */
  colors?: Partial<typeof DEFAULT_COLORS>;
  /** Optional font overrides */
  fonts?: Partial<typeof DEFAULT_FONTS>;
}

export const CTAScene: React.FC<CTASceneProps> = ({
  startFrame = 0,
  thumbnailUrl,
  ctaText,
  hookQuestion,
  channelName,
  teaserClips = [],
  colors: colorOverrides = {},
  fonts: fontOverrides = {},
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Merge defaults with overrides
  const colors = { ...DEFAULT_COLORS, ...colorOverrides };
  const fonts = { ...DEFAULT_FONTS, ...fontOverrides };

  // Calculate scale based on canvas size (supports both vertical and horizontal)
  const isVertical = height > width;
  const scale = isVertical
    ? Math.min(width / 1080, height / 1920)
    : Math.min(width / 1920, height / 1080);

  // ===== Animation Phases =====

  // Phase 1: Hook question fades in with scale emphasis (0-30 frames = 0-1s)
  const questionOpacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const questionScale = spring({
    frame: localFrame,
    fps,
    config: { damping: 15, stiffness: 100 },
  });

  // Phase 2: Thumbnail slides up (30-90 frames = 1-3s)
  const thumbnailY = interpolate(localFrame, [30, 75], [200, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const thumbnailOpacity = interpolate(localFrame, [30, 60], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Phase 3: Play button pulse (continuous after thumbnail appears)
  const playButtonPulse = 1 + Math.sin(localFrame * 0.1) * 0.05;

  // Phase 4: CTA text fades in (90-120 frames = 3-4s)
  const ctaOpacity = interpolate(localFrame, [90, 120], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Phase 5: Arrow bounce (continuous after CTA appears)
  const arrowBounce = Math.sin(localFrame * 0.15) * 8;

  // Glow intensity pulse
  const glowPulse = 0.7 + Math.sin(localFrame * 0.08) * 0.3;

  return (
    <div
      style={{
        position: "absolute",
        width: "100%",
        height: "100%",
        background: colors.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 40 * scale,
        overflow: "hidden",
      }}
    >
      {/* Hook Question */}
      <div
        style={{
          fontSize: (isVertical ? 48 : 56) * scale,
          fontFamily: fonts.heading,
          fontWeight: 700,
          color: colors.text,
          textAlign: "center",
          marginBottom: (isVertical ? 60 : 40) * scale,
          opacity: questionOpacity,
          transform: `scale(${questionScale})`,
          textShadow: `0 0 ${30 * glowPulse}px ${colors.primaryGlow}`,
          maxWidth: (isVertical ? 900 : 1400) * scale,
          lineHeight: 1.3,
        }}
      >
        {hookQuestion}
      </div>

      {/* Thumbnail Preview */}
      <div
        style={{
          position: "relative",
          width: (isVertical ? 700 : 800) * scale,
          height: (isVertical ? 400 : 450) * scale,
          borderRadius: 20 * scale,
          overflow: "hidden",
          boxShadow: `0 20px 60px ${colors.shadow}, 0 0 40px ${colors.glowMedium}`,
          opacity: thumbnailOpacity,
          transform: `translateY(${thumbnailY * scale}px)`,
          border: `4px solid ${colors.primary}`,
        }}
      >
        {thumbnailUrl ? (
          <Img
            src={thumbnailUrl}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        ) : (
          <div
            style={{
              width: "100%",
              height: "100%",
              background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.purple} 100%)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                fontSize: 80 * scale,
                color: "white",
              }}
            >
              ▶
            </div>
          </div>
        )}

        {/* Play button overlay */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: `translate(-50%, -50%) scale(${playButtonPulse})`,
            width: 100 * scale,
            height: 100 * scale,
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.95)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 0 ${30 * glowPulse}px ${colors.glowStrong}`,
          }}
        >
          <div
            style={{
              width: 0,
              height: 0,
              borderLeft: `${40 * scale}px solid ${colors.primary}`,
              borderTop: `${24 * scale}px solid transparent`,
              borderBottom: `${24 * scale}px solid transparent`,
              marginLeft: 8 * scale,
            }}
          />
        </div>
      </div>

      {/* Teaser clips (quick flashes) */}
      {teaserClips.length > 0 && (
        <>
          {teaserClips.map((clip, index) => {
            const clipStartFrame = 120 + index * 9; // ~0.3s each
            const clipOpacity = interpolate(
              localFrame,
              [clipStartFrame, clipStartFrame + 3, clipStartFrame + 6, clipStartFrame + 9],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            return (
              <div
                key={index}
                style={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  width: (isVertical ? 300 : 400) * scale,
                  height: (isVertical ? 200 : 250) * scale,
                  borderRadius: 12 * scale,
                  overflow: "hidden",
                  opacity: clipOpacity,
                  border: `2px solid ${colors.primary}`,
                }}
              >
                <Img
                  src={clip}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                  }}
                />
              </div>
            );
          })}
        </>
      )}

      {/* CTA Text */}
      <div
        style={{
          marginTop: (isVertical ? 60 : 40) * scale,
          opacity: ctaOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            fontSize: (isVertical ? 36 : 42) * scale,
            fontFamily: fonts.primary,
            fontWeight: 600,
            color: colors.text,
            marginBottom: 20 * scale,
            textAlign: "center",
          }}
        >
          {ctaText}
        </div>

        {/* Animated arrow pointing down */}
        <div
          style={{
            fontSize: 48 * scale,
            color: colors.primary,
            transform: `translateY(${arrowBounce * scale}px)`,
            textShadow: `0 0 20px ${colors.primaryGlow}`,
          }}
        >
          ↓
        </div>
      </div>

      {/* Channel name (optional) */}
      {channelName && (
        <div
          style={{
            position: "absolute",
            bottom: 60 * scale,
            fontSize: 24 * scale,
            fontFamily: fonts.primary,
            color: colors.textMuted,
            opacity: ctaOpacity,
          }}
        >
          {channelName}
        </div>
      )}
    </div>
  );
};

export default CTAScene;
