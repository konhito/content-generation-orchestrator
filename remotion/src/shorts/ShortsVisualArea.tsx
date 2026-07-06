/**
 * ShortsVisualArea - Renders the visual content for shorts
 *
 * Visual types (text-based):
 * - big_number: Large animated statistic
 * - comparison: Two values side by side
 * - text_highlight: Key phrase with emphasis
 * - simple_flow: A → B → C flow
 * - icon_stat: Icon with statistic
 * - key_point: Bullet point or insight
 * - question: Hook question display
 *
 * Visual types (scene components):
 * - token_grid: Animated token grid (prefill/decode)
 * - progress_bars: Animated progress/utilization bars
 * - code_block: Syntax-highlighted code snippet
 * - diagram: Simple diagram/flow
 * - image: Static image with animation
 */

import React from "react";
import { Img, Video, interpolate, spring, staticFile, useVideoConfig } from "remotion";
import { SHORTS_COLORS, SHORTS_FONTS, SHORTS_GLASS, ShortsBeat } from "./ShortsPlayer";
import {
  ShortsTokenGrid,
  ShortsProgressBars,
  ShortsCodeBlock,
  ShortsDiagram,
  ShortsImage,
  ShortsPatchGrid,
  ShortsEmbeddingBars,
  ShortsAttentionVisual,
  ShortsMaskedGrid,
} from "./ShortsSceneComponents";

export const GIPHY_PLAYBACK_RATE = 0.55;

const TEXT_VISUAL_TYPES = new Set(["big_number", "comparison", "text_highlight", "simple_flow", "icon_stat", "key_point", "question"]);

export const isTextVisualType = (visualType: string): boolean => TEXT_VISUAL_TYPES.has(visualType);

export const memeAssetRenderMode = (assetPath: string): "video" | "animated-image" | "image" => {
  if (isVideoAsset(assetPath)) {
    return "video";
  }
  if (isAnimatedAsset(assetPath)) {
    return "animated-image";
  }
  return "image";
};

interface ShortsVisualAreaProps {
  beat: ShortsBeat;
  frame: number;
  fps: number;
  scale: number;
}

export const flowStepsForBeat = (beat: ShortsBeat): string[] => {
  const explicit = [beat.visual.primary_text, beat.visual.secondary_text, beat.visual.tertiary_text]
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value));
  if (explicit.length > 0) {
    return explicit;
  }
  const caption = beat.caption_text?.trim() || "Key point";
  return caption.split(/\s+(?:versus|vs\.?|but|then)\s+/i).filter(Boolean).slice(0, 3);
};

export const ShortsVisualArea: React.FC<ShortsVisualAreaProps> = ({
  beat,
  frame,
  fps,
  scale,
}) => {
  const { visual } = beat;

  // Calculate beat-local frame for animations
  const beatStartFrame = beat.start_seconds * fps;
  const localFrame = frame - beatStartFrame;

  // Entry animation
  const entryProgress = spring({
    frame: localFrame,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  const entryScale = interpolate(entryProgress, [0, 1], [0.8, 1]);
  const entryOpacity = interpolate(entryProgress, [0, 1], [0, 1]);

  // Get color based on visual.color
  const getColor = (colorName: string = "primary"): string => {
    const colorMap: Record<string, string> = {
      primary: SHORTS_COLORS.primary,
      secondary: SHORTS_COLORS.secondary,
      accent: SHORTS_COLORS.accent,
      success: SHORTS_COLORS.success,
      warning: SHORTS_COLORS.warning,
      text: SHORTS_COLORS.text,
    };
    return colorMap[colorName] || SHORTS_COLORS.primary;
  };

  const color = getColor(visual.color);
  const staticMeme = visual.type === "meme_card";

  const renderVisual = () => {
    if (isTextVisualType(visual.type)) {
      return <AttentionGraphic color={color} scale={scale} frame={localFrame} />;
    }
    switch (visual.type) {
      case "big_number":
        return (
          <BigNumberVisual
            number={visual.primary_text}
            label={visual.secondary_text || ""}
            sublabel={visual.tertiary_text}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "comparison":
        return (
          <ComparisonVisual
            leftValue={visual.primary_text}
            rightValue={visual.secondary_text || ""}
            leftLabel={visual.tertiary_text || "Before"}
            rightLabel="After"
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "text_highlight":
        return (
          <TextHighlightVisual
            text={visual.primary_text}
            subtext={visual.secondary_text}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "simple_flow":
        return (
          <SimpleFlowVisual
            steps={[
              visual.primary_text,
              visual.secondary_text || "",
              visual.tertiary_text || "",
            ].filter(Boolean)}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "icon_stat":
        return (
          <IconStatVisual
            icon={visual.icon || ""}
            stat={visual.primary_text}
            label={visual.secondary_text || ""}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "key_point":
        return (
          <KeyPointVisual
            point={visual.primary_text}
            subpoint={visual.secondary_text}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "question":
        return (
          <QuestionVisual
            question={visual.primary_text}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      case "meme_card":
        return (
          <MemeCardVisual
            topText={visual.primary_text}
            bottomText={visual.secondary_text || ""}
            imagePath={visual.scene_config?.image_path || ""}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      // Scene component visuals
      case "token_grid":
        return (
          <ShortsTokenGrid
            tokens={visual.scene_config?.tokens || []}
            mode={visual.scene_config?.mode || "prefill"}
            rows={visual.scene_config?.rows || 4}
            cols={visual.scene_config?.cols || 4}
            scale={scale}
            label={visual.primary_text}
          />
        );

      case "progress_bars":
        return (
          <ShortsProgressBars
            bars={visual.scene_config?.bars || [
              { label: visual.primary_text, value: 0.8 },
            ]}
            scale={scale}
          />
        );

      case "code_block":
        return (
          <ShortsCodeBlock
            code={visual.scene_config?.code || visual.primary_text}
            language={visual.scene_config?.language || "python"}
            highlightLines={visual.scene_config?.highlight_lines || []}
            scale={scale}
          />
        );

      case "diagram":
        return (
          <ShortsDiagram
            nodes={[
              visual.primary_text,
              visual.secondary_text || "",
              visual.tertiary_text || "",
            ].filter(Boolean)}
            scale={scale}
          />
        );

      case "image":
        return (
          <ShortsImage
            src={toStaticAssetPath(visual.scene_config?.image_path || "")}
            caption={visual.scene_config?.caption || visual.secondary_text}
            scale={scale}
          />
        );

      case "patch_grid":
        return (
          <ShortsPatchGrid
            rows={visual.scene_config?.rows || 4}
            cols={visual.scene_config?.cols || 4}
            scale={scale}
            label={visual.primary_text}
            highlightPatches={visual.scene_config?.highlight_indices as number[] || []}
          />
        );

      case "embedding_bars":
        return (
          <ShortsEmbeddingBars
            dimensions={visual.scene_config?.dimensions as number || 8}
            values={visual.scene_config?.values as number[] || undefined}
            scale={scale}
            label={visual.primary_text}
          />
        );

      case "attention_visual":
        return (
          <AttentionGraphic
            color={color}
            scale={scale}
            frame={localFrame}
          />
        );

      case "masked_grid":
        return (
          <ShortsMaskedGrid
            rows={visual.scene_config?.rows || 4}
            cols={visual.scene_config?.cols || 4}
            maskedIndices={visual.scene_config?.masked_indices as number[] || [2, 5, 9, 12]}
            scale={scale}
            label={visual.primary_text}
          />
        );

      case "flow_diagram":
        // Flow diagram is rendered like simple_flow or diagram
        return (
          <SimpleFlowVisual
            steps={flowStepsForBeat(beat)}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );

      default:
        return (
          <TextHighlightVisual
            text={visual.primary_text}
            subtext={visual.secondary_text}
            color={color}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
        );
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: staticMeme ? 1 : entryOpacity,
        transform: staticMeme ? "none" : `scale(${entryScale})`,
        width: "100%",
        height: "100%",
      }}
    >
      {staticMeme ? (
        renderVisual()
      ) : (
        <div
          style={{
            ...SHORTS_GLASS,
            borderRadius: 28 * scale,
            padding: `${34 * scale}px ${36 * scale}px`,
            minWidth: 680 * scale,
            maxWidth: 980 * scale,
            minHeight: 360 * scale,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {renderVisual()}
        </div>
      )}
    </div>
  );
};

/**
 * Big Number Visual - Large animated statistic
 */
const BigNumberVisual: React.FC<{
  number: string;
  label: string;
  sublabel?: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ number, label, sublabel, color, scale, frame, fps }) => {
  // Animate number counting up effect
  const countProgress = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Pulsing glow effect
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
      }}
    >
      {/* Main number */}
      <div
        style={{
          fontSize: 120 * scale,
          fontFamily: SHORTS_FONTS.heading,
          fontWeight: 800,
          color: color,
          textShadow: `0 ${8 * scale}px ${24 * scale}px ${SHORTS_COLORS.primaryGlow}`,
          lineHeight: 1,
          marginBottom: 16 * scale,
        }}
      >
        {number}
      </div>

      {/* Label */}
      {label && (
        <div
          style={{
            fontSize: 36 * scale,
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 500,
            color: SHORTS_COLORS.text,
            opacity: 0.92,
            marginBottom: sublabel ? 8 * scale : 0,
          }}
        >
          {label}
        </div>
      )}

      {/* Sublabel */}
      {sublabel && (
        <div
          style={{
            fontSize: 24 * scale,
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 400,
            color: SHORTS_COLORS.textMuted,
          }}
        >
          {sublabel}
        </div>
      )}
    </div>
  );
};

/**
 * Comparison Visual - Side by side comparison
 */
const ComparisonVisual: React.FC<{
  leftValue: string;
  rightValue: string;
  leftLabel: string;
  rightLabel: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ leftValue, rightValue, leftLabel, rightLabel, color, scale, frame, fps }) => {
  // Staggered animation
  const leftEntry = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const rightEntry = interpolate(frame, [10, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 40 * scale,
        width: "100%",
      }}
    >
      {/* Left side */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: leftEntry,
          transform: `translateX(${(1 - leftEntry) * -30 * scale}px)`,
        }}
      >
        <div
          style={{
            fontSize: 64 * scale,
            fontFamily: SHORTS_FONTS.heading,
            fontWeight: 700,
            color: SHORTS_COLORS.textMuted,
          }}
        >
          {leftValue}
        </div>
        <div
          style={{
            fontSize: 24 * scale,
            fontFamily: SHORTS_FONTS.primary,
            color: SHORTS_COLORS.textMuted,
            marginTop: 8 * scale,
          }}
        >
          {leftLabel}
        </div>
      </div>

      {/* Arrow */}
      <div
        style={{
          fontSize: 48 * scale,
          color: color,
          opacity: rightEntry,
        }}
      >
        →
      </div>

      {/* Right side */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: rightEntry,
          transform: `translateX(${(1 - rightEntry) * 30 * scale}px)`,
        }}
      >
        <div
          style={{
            fontSize: 80 * scale,
            fontFamily: SHORTS_FONTS.heading,
            fontWeight: 800,
            color: color,
            textShadow: `0 ${8 * scale}px ${20 * scale}px ${SHORTS_COLORS.primaryGlow}`,
          }}
        >
          {rightValue}
        </div>
        <div
          style={{
            fontSize: 24 * scale,
            fontFamily: SHORTS_FONTS.primary,
            color: SHORTS_COLORS.text,
            marginTop: 8 * scale,
          }}
        >
          {rightLabel}
        </div>
      </div>
    </div>
  );
};

/**
 * Text Highlight Visual - Emphasized key phrase
 */
const TextHighlightVisual: React.FC<{
  text: string;
  subtext?: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ text, subtext, color, scale, frame, fps }) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        padding: `${40 * scale}px`,
      }}
    >
      <div
        style={{
          fontSize: 56 * scale,
          fontFamily: SHORTS_FONTS.heading,
          fontWeight: 700,
          color: color,
          textShadow: `0 ${8 * scale}px ${22 * scale}px ${SHORTS_COLORS.primaryGlow}`,
          lineHeight: 1.3,
          maxWidth: 900 * scale,
        }}
      >
        {text}
      </div>
      {subtext && (
        <div
          style={{
            fontSize: 32 * scale,
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 400,
            color: SHORTS_COLORS.text,
            marginTop: 24 * scale,
            opacity: 0.8,
          }}
        >
          {subtext}
        </div>
      )}
    </div>
  );
};

/**
 * Simple Flow Visual - A → B → C
 */
const SimpleFlowVisual: React.FC<{
  steps: string[];
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ steps, color, scale, frame, fps }) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 24 * scale,
      }}
    >
      {steps.map((step, index) => {
        const delay = index * 15;
        const entry = interpolate(frame - delay, [0, 20], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <React.Fragment key={index}>
            {index > 0 && (
              <div
                style={{
                  fontSize: 36 * scale,
                  color: color,
                  opacity: entry,
                }}
              >
                ↓
              </div>
            )}
            <div
              style={{
                background: index === steps.length - 1 ? "rgba(10, 132, 255, 0.12)" : SHORTS_COLORS.surfaceStrong,
                border: `1px solid ${index === steps.length - 1 ? color : SHORTS_COLORS.borderMuted}`,
                borderRadius: 16 * scale,
                padding: `${20 * scale}px ${40 * scale}px`,
                opacity: entry,
                transform: `translateY(${(1 - entry) * 20 * scale}px)`,
              }}
            >
              <div
                style={{
                  fontSize: 36 * scale,
                  fontFamily: SHORTS_FONTS.primary,
                  fontWeight: 600,
                  color: index === steps.length - 1 ? color : SHORTS_COLORS.text,
                }}
              >
                {step}
              </div>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

/**
 * Icon Stat Visual - Icon with statistic
 */
const IconStatVisual: React.FC<{
  icon: string;
  stat: string;
  label: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ icon, stat, label, color, scale, frame, fps }) => {
  const bounce = Math.sin(frame * 0.1) * 5;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 24 * scale,
      }}
    >
      {/* Icon */}
      <div
        style={{
          fontSize: 80 * scale,
          transform: `translateY(${bounce * scale}px)`,
        }}
      >
        {icon}
      </div>

      {/* Stat */}
      <div
        style={{
          fontSize: 72 * scale,
          fontFamily: SHORTS_FONTS.heading,
          fontWeight: 800,
          color: color,
          textShadow: `0 ${8 * scale}px ${20 * scale}px ${SHORTS_COLORS.primaryGlow}`,
        }}
      >
        {stat}
      </div>

      {/* Label */}
      {label && (
        <div
          style={{
            fontSize: 28 * scale,
            fontFamily: SHORTS_FONTS.primary,
            color: SHORTS_COLORS.text,
            opacity: 0.8,
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
};

/**
 * Key Point Visual - Bullet point or insight
 */
const KeyPointVisual: React.FC<{
  point: string;
  subpoint?: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ point, subpoint, color, scale, frame, fps }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 24 * scale,
        padding: `${32 * scale}px`,
        background: SHORTS_COLORS.surfaceStrong,
        borderLeft: `4px solid ${color}`,
        borderRadius: `0 ${16 * scale}px ${16 * scale}px 0`,
        maxWidth: 900 * scale,
      }}
    >
      <div
        style={{
          fontSize: 48 * scale,
          color: color,
        }}
      >
        ★
      </div>
      <div>
        <div
          style={{
            fontSize: 40 * scale,
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 600,
            color: SHORTS_COLORS.text,
            lineHeight: 1.3,
          }}
        >
          {point}
        </div>
        {subpoint && (
          <div
            style={{
              fontSize: 28 * scale,
              fontFamily: SHORTS_FONTS.primary,
              color: SHORTS_COLORS.textMuted,
              marginTop: 12 * scale,
            }}
          >
            {subpoint}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Question Visual - Hook question display
 */
const QuestionVisual: React.FC<{
  question: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ question, color, scale, frame, fps }) => {
  const pulseScale = 1 + Math.sin(frame * 0.08) * 0.02;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        padding: `${40 * scale}px`,
        transform: `scale(${pulseScale})`,
      }}
    >
      {/* Question mark icon */}
      <div
        style={{
          fontSize: 80 * scale,
          color: color,
          marginBottom: 32 * scale,
          textShadow: `0 ${10 * scale}px ${22 * scale}px ${SHORTS_COLORS.primaryGlow}`,
        }}
      >
        ?
      </div>

      {/* Question text */}
      <div
        style={{
          fontSize: 48 * scale,
          fontFamily: SHORTS_FONTS.heading,
          fontWeight: 700,
          color: SHORTS_COLORS.text,
          lineHeight: 1.3,
          maxWidth: 900 * scale,
        }}
      >
        {question}
      </div>
    </div>
  );
};

const AttentionGraphic: React.FC<{color: string; scale: number; frame: number}> = ({color, scale, frame}) => (
  <div style={{display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 * scale, width: 620 * scale}}>
    {Array.from({length: 36}).map((_, index) => {
      const active = (index + Math.floor(frame / 4)) % 7 < 3;
      return <div key={index} style={{aspectRatio: "1", borderRadius: 12 * scale, background: active ? color : SHORTS_COLORS.surfaceStrong, opacity: active ? 0.9 : 0.45, boxShadow: active ? `0 ${8 * scale}px ${20 * scale}px ${SHORTS_COLORS.primaryGlow}` : "none"}} />;
    })}
  </div>
);

const MemeCardVisual: React.FC<{
  topText: string;
  bottomText: string;
  imagePath?: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ topText, bottomText, imagePath, color, scale, frame, fps }) => {
  return (
    <div
      style={{
        width: 940 * scale,
        minHeight: 760 * scale,
        borderRadius: 28 * scale,
        background: SHORTS_COLORS.surfaceStrong,
        backdropFilter: "blur(28px)",
        WebkitBackdropFilter: "blur(28px)",
        border: `${1.5 * scale}px solid ${SHORTS_COLORS.border}`,
        boxShadow: `0 ${28 * scale}px ${80 * scale}px ${SHORTS_COLORS.shadow}`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "space-between",
        padding: `${34 * scale}px ${30 * scale}px`,
      }}
      >
        {imagePath ? (
          <>
            <div
              style={{
                width: "100%",
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "rgba(255, 255, 255, 0.7)",
                borderRadius: 28 * scale,
                overflow: "hidden",
                border: `${1.5 * scale}px solid ${SHORTS_COLORS.borderMuted}`,
                minHeight: 610 * scale,
                }}
              >
              {memeAssetRenderMode(imagePath) === "video" ? (
                <Video
                  src={toStaticAssetPath(imagePath)}
                  muted
                  loop
                  playbackRate={GIPHY_PLAYBACK_RATE}
                  data-animated-meme="true"
                  data-playback-rate={String(GIPHY_PLAYBACK_RATE)}
                  data-asset={imagePath}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    display: "block",
                  }}
                />
              ) : (
                <Img
                  src={toStaticAssetPath(imagePath)}
                  alt="Meme asset"
                  data-asset={imagePath}
                  data-animated-meme={memeAssetRenderMode(imagePath) === "animated-image" ? "browser-default" : undefined}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    display: "block",
                  }}
                />
              )}
            </div>
          </>
        ) : (
          <>
            <div
              style={{
                color: "#080808",
                fontFamily: SHORTS_FONTS.heading,
                fontSize: 54 * scale,
                fontWeight: 950,
                lineHeight: 1.02,
                textAlign: "center",
                textTransform: "uppercase",
                letterSpacing: -2 * scale,
              }}
            >
              {topText}
            </div>
            <div
              style={{
                backgroundColor: "rgba(17, 24, 39, 0.92)",
                color: color,
                fontFamily: SHORTS_FONTS.mono,
                fontSize: 28 * scale,
                fontWeight: 900,
                padding: `${12 * scale}px ${24 * scale}px`,
                borderRadius: 999,
                textTransform: "uppercase",
                boxShadow: `0 ${12 * scale}px ${30 * scale}px ${SHORTS_COLORS.primaryGlow}`,
              }}
            >
              Meme cut
            </div>
            <div
              style={{
                color: "#080808",
                fontFamily: SHORTS_FONTS.heading,
                fontSize: 58 * scale,
                fontWeight: 1000,
                lineHeight: 1.02,
                textAlign: "center",
                textTransform: "uppercase",
                letterSpacing: -2 * scale,
              }}
            >
              {bottomText}
            </div>
          </>
        )}
    </div>
  );
};

export default ShortsVisualArea;

const toStaticAssetPath = (assetPath: string): string => {
  if (!assetPath) {
    return "";
  }
  if (/^(https?:)?\/\//.test(assetPath)) {
    return assetPath;
  }
  const normalized = assetPath.replace(/^file:\/\/+/, "").replace(/\\/g, "/");
  const shortIndex = normalized.indexOf("/short/");
  if (shortIndex >= 0) {
    return staticFile(normalized.slice(shortIndex + 1));
  }
  const rootIndex = normalized.indexOf("/projects/");
  if (rootIndex >= 0) {
    const suffix = normalized.slice(normalized.indexOf("/short/", rootIndex));
    if (suffix.startsWith("/short/")) {
      return staticFile(suffix.slice(1));
    }
  }
  return staticFile(normalized.replace(/^[\\/]+/, ""));
};

const isAnimatedAsset = (assetPath: string): boolean =>
  /\.(gif|webp|apng|avif)(?:$|[?#])/i.test(assetPath);

const isVideoAsset = (assetPath: string): boolean =>
  /\.(mp4|webm|mov)(?:$|[?#])/i.test(assetPath);
