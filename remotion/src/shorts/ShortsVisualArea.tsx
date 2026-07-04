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
import { interpolate, spring, useVideoConfig } from "remotion";
import { SHORTS_COLORS, SHORTS_FONTS, ShortsBeat } from "./ShortsPlayer";
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

interface ShortsVisualAreaProps {
  beat: ShortsBeat;
  frame: number;
  fps: number;
  scale: number;
}

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

  const renderVisual = () => {
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
            src={visual.scene_config?.image_path || ""}
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
          <ShortsAttentionVisual
            size={visual.scene_config?.size as number || 6}
            scale={scale}
            label={visual.primary_text}
            pattern={visual.scene_config?.pattern as "self" | "cross" | "causal" || "self"}
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
        opacity: entryOpacity,
        transform: `scale(${entryScale})`,
        width: "100%",
        height: "100%",
      }}
    >
      {renderVisual()}
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
  const glowIntensity = 0.5 + Math.sin(frame * 0.1) * 0.2;

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
          textShadow: `0 0 ${40 * glowIntensity}px ${color}, 0 0 ${80 * glowIntensity}px ${color}40`,
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
            opacity: 0.9,
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
            textShadow: `0 0 30px ${color}60`,
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
  const glowIntensity = 0.6 + Math.sin(frame * 0.08) * 0.2;

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
          textShadow: `0 0 ${30 * glowIntensity}px ${color}`,
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
                background: index === steps.length - 1 ? `${color}20` : "rgba(255,255,255,0.05)",
                border: `2px solid ${index === steps.length - 1 ? color : "rgba(255,255,255,0.1)"}`,
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
          textShadow: `0 0 30px ${color}60`,
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
        background: "rgba(255,255,255,0.03)",
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
  const glowIntensity = 0.5 + Math.sin(frame * 0.06) * 0.3;

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
          textShadow: `0 0 ${40 * glowIntensity}px ${color}`,
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

const MemeCardVisual: React.FC<{
  topText: string;
  bottomText: string;
  color: string;
  scale: number;
  frame: number;
  fps: number;
}> = ({ topText, bottomText, color, scale, frame, fps }) => {
  const pop = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 180 },
  });
  const opacity = interpolate(frame, [0, 0.2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shake = Math.sin(frame * 0.55) * 1.5;
  const scalePop = interpolate(pop, [0, 1], [0.72, 1]);

  return (
    <div
      style={{
        width: 820 * scale,
        minHeight: 620 * scale,
        borderRadius: 42 * scale,
        background: "linear-gradient(180deg, #ffffff 0%, #e8e8e8 100%)",
        border: `${8 * scale}px solid #111`,
        boxShadow: `0 ${28 * scale}px ${80 * scale}px rgba(0,0,0,0.45), 0 0 ${50 * scale}px ${color}66`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "space-between",
        padding: `${42 * scale}px ${34 * scale}px`,
        opacity,
        transform: `scale(${scalePop}) rotate(${shake}deg)`,
      }}
    >
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
          backgroundColor: "#111",
          color: color,
          fontFamily: SHORTS_FONTS.mono,
          fontSize: 28 * scale,
          fontWeight: 900,
          padding: `${12 * scale}px ${24 * scale}px`,
          borderRadius: 999,
          textTransform: "uppercase",
          boxShadow: `0 0 ${24 * scale}px ${color}88`,
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
    </div>
  );
};

export default ShortsVisualArea;
