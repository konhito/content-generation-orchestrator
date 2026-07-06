/**
 * ShortsPlayer - Main player component for YouTube Shorts
 *
 * Layout (1080x1920):
 * - Top 70% (0-1344px): Visual area with simplified graphics
 * - Bottom 30% (1344-1920px): Animated captions + progress bar
 */

import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  Audio,
  staticFile,
} from "remotion";
import { ShortsVisualArea } from "./ShortsVisualArea";
import { AnimatedCaptions } from "./AnimatedCaptions";
import { ShortsProgressBar } from "./ShortsProgressBar";
import { ShortsCharacterScene } from "./ShortsCharacterScene";
import { ShortsMixedScene } from "./ShortsMixedScene";
import { ShortsTransition } from "./ShortsTransition";
import type { CharacterTrack } from "./characterTypes";
import type { VisualRecipe } from "./recipeTypes";
import { rendererForMode } from "./shortsDispatch";
import { SHORTS_COLORS, SHORTS_FONTS } from "./shortsStyle";

export { SHORTS_COLORS, SHORTS_FONTS, SHORTS_GLASS } from "./shortsStyle";

// Try to load custom short scenes from project directory
// This will be resolved by webpack alias @project-short-scenes
// Note: Components can't be serialized in props, so we import directly
let projectCustomScenes: Record<string, React.FC<{ startFrame?: number }>> = {};
try {
  // @ts-ignore - dynamically resolved by webpack
  projectCustomScenes = require("@project-short-scenes").default || {};
} catch {
  // No custom scenes available - will use generic ShortsVisualArea fallback
}

// Layout constants for 1080x1920 vertical format
export const SHORTS_LAYOUT = {
  width: 1080,
  height: 1920,
  visualArea: {
    top: 0,
    height: 1920, // Full bleed - 3D extends to bottom
  },
  captionArea: {
    top: 1920 - 230, // Overlay at bottom ~12% of frame (230px)
    height: 230,
  },
  progressBar: {
    height: 6,
  },
};

export interface SceneComponentConfig {
  component_type: string;
  props?: Record<string, unknown>;
  // Token grid
  tokens?: string[];
  mode?: "prefill" | "decode";
  rows?: number;
  cols?: number;
  // Progress bars
  bars?: Array<{ label: string; value: number; color?: string }>;
  // Code block
  code?: string;
  language?: string;
  highlight_lines?: number[];
  // Image
  image_path?: string;
  caption?: string;
  // Patch grid
  highlight_indices?: number[];
  // Embedding bars
  dimensions?: number;
  values?: number[];
  // Attention visual
  size?: number;
  pattern?: "self" | "cross" | "causal";
  // Masked grid
  masked_indices?: number[];
}

export interface ShortsBeat {
  id: string;
  start_seconds: number;
  end_seconds: number;
  visual: {
    type: string;
    primary_text: string;
    secondary_text?: string;
    tertiary_text?: string;
    icon?: string;
    color?: string;
    scene_config?: SceneComponentConfig;
    source_scene_id?: string;
  };
  caption_text: string;
  word_timestamps?: Array<{
    word: string;
    start_seconds: number;
    end_seconds: number;
  }>;
  // Custom scene generation fields
  visual_description?: string;
  visual_elements?: string[];
  component_name?: string;
  mode?: "character" | "component" | "meme";
  character_track?: string;
  character_data?: CharacterTrack;
  visual_recipe?: VisualRecipe;
}

// Type for custom scene component
export type BeatSceneComponent = React.FC<{ startFrame?: number }>;

export interface ShortsStoryboard {
  id: string;
  title: string;
  total_duration_seconds: number;
  beats: ShortsBeat[];
  hook_question?: string;
  cta_text?: string;
  voiceover_path?: string;
  audio?: {
    background_music?: {
      path: string;
      volume: number;
    };
  };
}

export const rendererForBeat = (beat: Partial<ShortsBeat>): "mixed" | "character" | "visual" => {
  if (beat.visual_recipe) return "mixed";
  if (rendererForMode(beat.mode) === "character" && beat.character_data) return "character";
  return "visual";
};

interface ShortsPlayerProps {
  storyboard?: ShortsStoryboard;
  voiceoverBasePath?: string;
}

export const ShortsPlayer: React.FC<ShortsPlayerProps> = ({
  storyboard,
  voiceoverBasePath = "voiceover",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const currentTime = frame / fps;

  // Calculate scale for different render sizes
  const scale = Math.min(width / SHORTS_LAYOUT.width, height / SHORTS_LAYOUT.height);

  // Handle missing storyboard
  if (!storyboard) {
    return (
      <AbsoluteFill
        style={{
          background: SHORTS_COLORS.background,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ color: SHORTS_COLORS.text, fontSize: 48 * scale }}>
          No storyboard provided
        </div>
      </AbsoluteFill>
    );
  }

  // Find current beat based on time (with overlap handling)
  const TRANSITION_OVERLAP = 0.15; // 4-5 frames at 30fps

  // Find which beats should be visible (current + overlapping transitions)
  const currentBeat = storyboard.beats.find(
    (beat) => currentTime >= beat.start_seconds && currentTime < beat.end_seconds
  );

  // Find previous beat (for fade out during transition)
  const prevBeatIndex = storyboard.beats.findIndex(
    (beat) => currentTime >= beat.start_seconds && currentTime < beat.end_seconds
  ) - 1;
  const prevBeat = prevBeatIndex >= 0 ? storyboard.beats[prevBeatIndex] : null;

  // Find next beat (for fade in during transition)
  const nextBeatIndex = storyboard.beats.findIndex(
    (beat) => currentTime >= beat.start_seconds && currentTime < beat.end_seconds
  ) + 1;
  const nextBeat = nextBeatIndex < storyboard.beats.length ? storyboard.beats[nextBeatIndex] : null;

  // If no current beat found, we might be in a gap - show nearest beat
  const fallbackBeat = !currentBeat ? storyboard.beats.find(
    (beat) => currentTime < beat.end_seconds
  ) || storyboard.beats[storyboard.beats.length - 1] : null;

  // Use current beat or fallback
  const activeBeat = currentBeat || fallbackBeat;

  // Calculate overall progress
  const progress = currentTime / storyboard.total_duration_seconds;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${SHORTS_COLORS.backgroundGradientStart} 0%, ${SHORTS_COLORS.backgroundGradientEnd} 100%)`,
      }}
    >
      {/* Animated background particles/grid */}
      <BackgroundEffect frame={frame} scale={scale} />

      {/* Visual Area - Full bleed */}
      <div
        style={{
          position: "absolute",
          top: SHORTS_LAYOUT.visualArea.top * scale,
          left: 0,
          width: width,
          height: SHORTS_LAYOUT.visualArea.height * scale,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Main Visual - use custom scene if available, else fallback to ShortsVisualArea */}
        {activeBeat && (
          <>
            <VisualRenderer
              beat={activeBeat}
              frame={frame}
              fps={fps}
              scale={scale}
            />
            <ShortsTransition
              from={prevBeat?.mode}
              to={activeBeat.mode}
              localFrame={Math.max(0, frame - Math.round(activeBeat.start_seconds * fps))}
              scale={scale}
            />
          </>
        )}
      </div>

      {/* Caption Area - Gradient overlay at bottom (~12% of frame) */}
      <div
        style={{
          position: "absolute",
          bottom: SHORTS_LAYOUT.progressBar.height * scale,
          left: 0,
          width: width,
          height: SHORTS_LAYOUT.captionArea.height * scale,
          background: "linear-gradient(to bottom, transparent 0%, rgba(245, 247, 251, 0.62) 30%, rgba(245, 247, 251, 0.92) 100%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: `0 ${24 * scale}px`,
        }}
      >
        {activeBeat && (
          <AnimatedCaptions
            text={activeBeat.caption_text}
            wordTimestamps={activeBeat.word_timestamps || []}
            currentTime={currentTime}
            beatStartTime={activeBeat.start_seconds}
            scale={scale}
          />
        )}
      </div>

      {/* Progress Bar (Very bottom) */}
      <ShortsProgressBar
        progress={progress}
        scale={scale}
        height={SHORTS_LAYOUT.progressBar.height}
      />

      {/* Audio - Voiceover */}
      {storyboard.voiceover_path && (
        <Audio src={staticFile(storyboard.voiceover_path)} />
      )}

      {/* Audio - Background Music */}
      {storyboard.audio?.background_music?.path && (
        <Audio
          src={staticFile(storyboard.audio.background_music.path)}
          volume={storyboard.audio.background_music.volume ?? 0.3}
        />
      )}
    </AbsoluteFill>
  );
};

/**
 * Visual renderer that uses custom scene if available, else fallback to ShortsVisualArea
 */
const VisualRenderer: React.FC<{
  beat: ShortsBeat;
  frame: number;
  fps: number;
  scale: number;
}> = ({ beat, frame, fps, scale }) => {
  if (rendererForBeat(beat) === "mixed") {
    return (
      <ShortsMixedScene
        beat={beat}
        frame={Math.max(0, frame - Math.round(beat.start_seconds * fps))}
        fps={fps}
        scale={scale}
      />
    );
  }

  if (rendererForMode(beat.mode) === "character" && beat.character_data) {
    const beatStartFrame = Math.round(beat.start_seconds * fps);
    return (
      <ShortsCharacterScene
        track={beat.character_data}
        frame={Math.max(0, frame - beatStartFrame)}
        fps={fps}
        scale={scale}
        showStage={false}
      />
    );
  }

  // Use module-level custom scenes (not props - components can't be serialized)
  const CustomScene = projectCustomScenes[beat.id];

  if (CustomScene) {
    // Calculate the start frame for this beat
    const beatStartFrame = Math.round(beat.start_seconds * fps);
    return <CustomScene startFrame={beatStartFrame} />;
  }

  // Fallback to generic visual area
  return (
    <ShortsVisualArea
      beat={beat}
      frame={frame}
      fps={fps}
      scale={scale}
    />
  );
};

/**
 * Animated background effect with subtle grid and particles
 */
const BackgroundEffect: React.FC<{ frame: number; scale: number }> = ({
  frame,
  scale,
}) => {
  // Subtle animated gradient
  const gradientShift = Math.sin(frame * 0.01) * 10;

  return (
    <>
      {/* Subtle radial glow */}
      <div
        style={{
          position: "absolute",
          top: "30%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 800 * scale,
          height: 800 * scale,
          background: `radial-gradient(circle, ${SHORTS_COLORS.primaryGlow} 0%, transparent 70%)`,
          opacity: 0.5 + Math.sin(frame * 0.02) * 0.2,
        }}
      />

      {/* Subtle grid pattern */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: `
            linear-gradient(rgba(10, 132, 255, 0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(10, 132, 255, 0.06) 1px, transparent 1px)
          `,
          backgroundSize: `${60 * scale}px ${60 * scale}px`,
          opacity: 0.3,
          transform: `translateY(${gradientShift * scale}px)`,
        }}
      />
    </>
  );
};

export default ShortsPlayer;
