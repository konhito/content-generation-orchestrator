/**
 * SingleScenePlayer - Renders a single scene for inspection/refinement
 *
 * This composition loads just ONE scene starting at frame 0, making it ideal for:
 * - Visual inspection and refinement
 * - Testing individual scenes
 * - Quick previews without loading the entire video
 *
 * Usage:
 *   http://localhost:3000/SingleScenePlayer?sceneType=thinking-models/beyond_linear_thinking&durationInSeconds=27.7
 */

import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  staticFile,
  useVideoConfig,
} from "remotion";
import { getSceneByPath } from "./index";
import { AmbientGlow, Vignette } from "../components/CinematicEffects";

/**
 * Props for SingleScenePlayer
 */
export interface SingleScenePlayerProps {
  /** Scene type path (e.g., "thinking-models/beyond_linear_thinking") */
  sceneType: string;
  /** Duration in seconds */
  durationInSeconds: number;
  /** Optional voiceover file path (relative to project's voiceover dir) */
  audioFile?: string;
  /** Base path for voiceover files */
  voiceoverBasePath?: string;
  /** Background color override */
  backgroundColor?: string;
}

/**
 * Parse URL search string to get scene props (pure function for testing)
 * Supports two formats:
 * 1. Direct query params: ?sceneType=project/scene&durationInSeconds=30
 * 2. Remotion JSON format: ?props={"sceneType":"project/scene","durationInSeconds":30}
 *
 * @param searchString - URL search string (e.g., "?sceneType=foo&durationInSeconds=30")
 * @returns Parsed props from URL
 */
export function parseUrlProps(searchString: string): Partial<SingleScenePlayerProps> {
  const params = new URLSearchParams(searchString);
  const result: Partial<SingleScenePlayerProps> = {};

  // First, try to parse Remotion's ?props={JSON} format
  const propsJson = params.get("props");
  if (propsJson) {
    try {
      const parsed = JSON.parse(propsJson);
      if (parsed.sceneType) result.sceneType = parsed.sceneType;
      if (parsed.durationInSeconds) result.durationInSeconds = parsed.durationInSeconds;
      if (parsed.audioFile) result.audioFile = parsed.audioFile;
      if (parsed.backgroundColor) result.backgroundColor = parsed.backgroundColor;
      if (parsed.voiceoverBasePath) result.voiceoverBasePath = parsed.voiceoverBasePath;
    } catch (e) {
      // Silently ignore malformed JSON - fall back to direct params or component props
    }
  }

  // Then, check for direct query params (these override JSON props if present)
  const sceneType = params.get("sceneType");
  if (sceneType) result.sceneType = sceneType;

  const duration = params.get("durationInSeconds");
  if (duration) result.durationInSeconds = parseFloat(duration);

  const audio = params.get("audioFile");
  if (audio) result.audioFile = audio;

  const bgColor = params.get("backgroundColor");
  if (bgColor) result.backgroundColor = bgColor;

  return result;
}

/**
 * React hook wrapper for parseUrlProps
 * Memoizes the result since URL doesn't change during render
 */
function useUrlProps(): Partial<SingleScenePlayerProps> {
  return useMemo(() => {
    if (typeof window === "undefined") return {};
    return parseUrlProps(window.location.search);
  }, []);
}

/**
 * SingleScenePlayer component
 *
 * Renders a single scene starting at frame 0.
 * Perfect for visual inspection where you don't want to navigate
 * through an entire video to find a specific scene.
 */
export const SingleScenePlayer: React.FC<SingleScenePlayerProps> = (props) => {
  const { fps } = useVideoConfig();

  // Merge URL params with props (URL params take precedence)
  const urlProps = useUrlProps();
  const {
    sceneType,
    durationInSeconds,
    audioFile,
    voiceoverBasePath = "voiceover",
    backgroundColor = "#0f0f1a",
  } = { ...props, ...urlProps };

  // Get the scene component from registry
  const SceneComponent = getSceneByPath(sceneType);

  // Debug: log what we're looking for
  console.log("[SingleScenePlayer] Looking for scene:", sceneType);
  console.log("[SingleScenePlayer] URL props:", urlProps);
  console.log("[SingleScenePlayer] Component props:", props);

  if (!SceneComponent) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          color: "#ff4444",
          fontSize: 24,
          fontFamily: "Inter, sans-serif",
          padding: 40,
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 20 }}>
          Scene not found: {sceneType}
        </div>
        <div style={{ color: "#888", fontSize: 16 }}>
          URL: {typeof window !== "undefined" ? window.location.href : "N/A"}
        </div>
        <div style={{ color: "#888", fontSize: 14, marginTop: 10 }}>
          Parsed urlProps: {JSON.stringify(urlProps)}
        </div>
        <div style={{ color: "#888", fontSize: 14, marginTop: 10 }}>
          Component props: {JSON.stringify(props)}
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {/* Ambient glow effect */}
      <AmbientGlow color="#00d9ff" intensity={0.15} />

      {/* The scene component - always starts at frame 0 */}
      <SceneComponent startFrame={0} />

      {/* Vignette for cinematic feel */}
      <Vignette intensity={0.3} />

      {/* Optional voiceover audio */}
      {audioFile && (
        <Audio
          src={staticFile(`${voiceoverBasePath}/${audioFile}`)}
          volume={1}
        />
      )}
    </AbsoluteFill>
  );
};

/**
 * Calculate duration in frames from props
 */
export function calculateSingleSceneDuration(
  props: SingleScenePlayerProps,
  fps: number = 30
): number {
  return Math.ceil(props.durationInSeconds * fps);
}

export default SingleScenePlayer;
