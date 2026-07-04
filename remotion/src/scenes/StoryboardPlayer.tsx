/**
 * StoryboardPlayer - Dynamic storyboard renderer
 *
 * This component takes a storyboard JSON and renders it dynamically,
 * without requiring code generation for each new storyboard.
 */

import React, { useMemo } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  Audio,
  Sequence,
  staticFile,
} from "remotion";
import { getComponent, hasComponent } from "../components/registry";
import type {
  Storyboard,
  Beat,
  Element,
  Animation,
  Position,
  Transition,
} from "../types/storyboard";

// Audio scene definition
interface AudioScene {
  id: string;
  file: string;
  start_seconds: number;
  duration_seconds: number;
}

// Audio configuration in storyboard
interface AudioConfig {
  base_path?: string;
  scenes?: AudioScene[];
}

export interface StoryboardPlayerProps {
  storyboard?: Storyboard & { audio?: AudioConfig };
}

// Empty storyboard fallback for type safety
const emptyStoryboard: Storyboard = {
  id: "empty",
  title: "Empty",
  duration_seconds: 1,
  beats: [],
};

export const StoryboardPlayer: React.FC<StoryboardPlayerProps> = ({
  storyboard = emptyStoryboard,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const currentTimeSeconds = frame / fps;

  // Get active beats at current time
  const activeBeats = useMemo(() => {
    return storyboard.beats.filter(
      (beat) =>
        currentTimeSeconds >= beat.start_seconds &&
        currentTimeSeconds < beat.end_seconds
    );
  }, [storyboard.beats, currentTimeSeconds]);

  // Collect all elements from active beats, avoiding duplicates
  const activeElements = useMemo(() => {
    const elementMap = new Map<string, { element: Element; beat: Beat }>();

    for (const beat of activeBeats) {
      if (beat.elements) {
        for (const element of beat.elements) {
          // Later beats override earlier ones for same element ID
          elementMap.set(element.id, { element, beat });
        }
      }
    }

    return Array.from(elementMap.values());
  }, [activeBeats]);

  // Get background color from style or default
  const backgroundColor =
    storyboard.style?.background_color || "#0f0f1a";

  // Get audio scenes from storyboard
  const audioConfig = (storyboard as StoryboardPlayerProps["storyboard"])?.audio;
  const audioScenes = audioConfig?.scenes || [];

  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        fontFamily: storyboard.style?.font_family || "Inter, sans-serif",
      }}
    >
      {/* Render audio tracks */}
      {audioScenes.map((scene) => {
        const startFrame = Math.floor(scene.start_seconds * fps);
        const durationFrames = Math.ceil(scene.duration_seconds * fps);

        // Construct the audio path - use absolute path from base_path
        const audioPath = audioConfig?.base_path
          ? `${audioConfig.base_path}/${scene.file}`
          : scene.file;

        return (
          <Sequence key={scene.id} from={startFrame} durationInFrames={durationFrames}>
            <Audio src={audioPath} />
          </Sequence>
        );
      })}

      {/* Render visual elements */}
      {activeElements.map(({ element, beat }) => (
        <ElementRenderer
          key={element.id}
          element={element}
          beat={beat}
          currentTimeSeconds={currentTimeSeconds}
          fps={fps}
          width={width}
          height={height}
          storyboard={storyboard}
        />
      ))}
    </AbsoluteFill>
  );
};

interface ElementRendererProps {
  element: Element;
  beat: Beat;
  currentTimeSeconds: number;
  fps: number;
  width: number;
  height: number;
  storyboard: Storyboard;
}

const ElementRenderer: React.FC<ElementRendererProps> = ({
  element,
  beat,
  currentTimeSeconds,
  fps,
  width,
  height,
  storyboard,
}) => {
  // Check if component exists
  if (!hasComponent(element.component)) {
    console.warn(`Component "${element.component}" not found in registry`);
    return null;
  }

  const Component = getComponent(element.component);

  // Calculate position
  const position = resolvePosition(element.position, width, height);

  // Calculate enter/exit transitions
  const enterOpacity = calculateTransition(
    element.enter,
    currentTimeSeconds,
    beat.start_seconds,
    "enter"
  );
  const exitOpacity = calculateTransition(
    element.exit,
    currentTimeSeconds,
    beat.end_seconds,
    "exit"
  );
  const opacity = Math.min(enterOpacity, exitOpacity);

  // Calculate animation state
  const animationProps = calculateAnimations(
    element.animations || [],
    currentTimeSeconds,
    fps
  );

  // Calculate sync point triggers
  const syncProps = calculateSyncPoints(
    beat.sync_points || [],
    element.id,
    currentTimeSeconds,
    fps
  );

  // Build style object from storyboard global style
  const style = storyboard.style
    ? {
        backgroundColor: storyboard.style.background_color || "#0f0f1a",
        primaryColor: storyboard.style.primary_color || "#00d9ff",
        secondaryColor: storyboard.style.secondary_color || "#ff6b35",
        fontFamily: storyboard.style.font_family || "Inter, sans-serif",
      }
    : {
        backgroundColor: "#0f0f1a",
        primaryColor: "#00d9ff",
        secondaryColor: "#ff6b35",
        fontFamily: "Inter, sans-serif",
      };

  // Merge all props
  const finalProps = {
    ...element.props,
    ...animationProps,
    ...syncProps,
    style, // Pass global style to all components
  };

  return (
    <div
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        transform: `translate(-50%, -50%)`,
        opacity,
      }}
    >
      <Component {...finalProps} />
    </div>
  );
};

/**
 * Resolve position from storyboard format to pixel values.
 */
function resolvePosition(
  position: Position | undefined,
  width: number,
  height: number
): { x: number; y: number } {
  if (!position) {
    return { x: width / 2, y: height / 2 };
  }

  let x: number;
  let y: number;

  // Resolve X
  if (typeof position.x === "number") {
    x = position.x;
  } else if (position.x === "left") {
    x = width * 0.2;
  } else if (position.x === "right") {
    x = width * 0.8;
  } else {
    x = width / 2;
  }

  // Resolve Y
  if (typeof position.y === "number") {
    y = position.y;
  } else if (position.y === "top") {
    y = height * 0.2;
  } else if (position.y === "bottom") {
    y = height * 0.8;
  } else {
    y = height / 2;
  }

  return { x, y };
}

/**
 * Calculate transition opacity (enter or exit).
 */
function calculateTransition(
  transition: Transition | undefined,
  currentTime: number,
  boundaryTime: number,
  type: "enter" | "exit"
): number {
  if (!transition || transition.type === "none") {
    return 1;
  }

  const duration = transition.duration_seconds || 0.3;
  const delay = transition.delay_seconds || 0;

  if (type === "enter") {
    const startTime = boundaryTime + delay;
    const endTime = startTime + duration;

    if (currentTime < startTime) return 0;
    if (currentTime >= endTime) return 1;

    return interpolate(
      currentTime,
      [startTime, endTime],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    // Exit transition
    const startTime = boundaryTime - duration - delay;
    const endTime = boundaryTime - delay;

    if (currentTime < startTime) return 1;
    if (currentTime >= endTime) return 0;

    return interpolate(
      currentTime,
      [startTime, endTime],
      [1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  }
}

/**
 * Calculate props from animations based on current time.
 */
function calculateAnimations(
  animations: Animation[],
  currentTimeSeconds: number,
  fps: number
): Record<string, unknown> {
  const props: Record<string, unknown> = {};

  for (const animation of animations) {
    const animationStart = animation.at_seconds;
    const animationDuration = animation.duration_seconds || 0.3;
    const animationEnd = animationStart + animationDuration;

    // Check if this animation should affect current state
    if (currentTimeSeconds >= animationStart) {
      const progress = Math.min(
        1,
        (currentTimeSeconds - animationStart) / animationDuration
      );

      // Apply easing
      const easedProgress = applyEasing(progress, animation.easing);

      // Handle different animation actions
      switch (animation.action) {
        case "activate":
        case "activate_all":
          props.isActive = true;
          props.activateAt = Math.floor(animationStart * fps);
          break;

        case "activate_sequential":
          props.mode = "decode";
          props.activateAt = Math.floor(animationStart * fps);
          if (animation.params?.delay_between) {
            props.tokenDelay = Math.floor(
              (animation.params.delay_between as number) * fps
            );
          }
          break;

        case "fill":
          props.animateAt = Math.floor(animationStart * fps);
          props.animationDuration = Math.floor(animationDuration * fps);
          break;

        case "show_status":
          // Status is shown after gauge fills
          break;

        case "fade_in":
          props.opacity = easedProgress;
          break;

        case "fade_out":
          props.opacity = 1 - easedProgress;
          break;

        case "scale":
          const fromScale = (animation.params?.from as number) || 1;
          const toScale = (animation.params?.to as number) || 1;
          props.scale = fromScale + (toScale - fromScale) * easedProgress;
          break;

        case "type_in":
          // Type-in effect handled by component
          props.typeProgress = easedProgress;
          break;

        case "move":
          // Move animation
          if (animation.params?.to) {
            props.moveProgress = easedProgress;
            props.moveTo = animation.params.to;
          }
          break;

        default:
          // Pass action and params to component to handle
          props[`animation_${animation.action}`] = {
            progress: easedProgress,
            params: animation.params,
          };
      }
    }
  }

  return props;
}

/**
 * Calculate props from sync points.
 */
function calculateSyncPoints(
  syncPoints: Array<{
    trigger_seconds: number;
    target: string;
    action: string;
    params?: Record<string, unknown>;
  }>,
  elementId: string,
  currentTimeSeconds: number,
  fps: number
): Record<string, unknown> {
  const props: Record<string, unknown> = {};

  for (const syncPoint of syncPoints) {
    if (syncPoint.target !== elementId) continue;

    if (currentTimeSeconds >= syncPoint.trigger_seconds) {
      // Sync point has triggered
      switch (syncPoint.action) {
        case "activate":
        case "activate_all":
          props.isActive = true;
          props.activateAt = Math.floor(syncPoint.trigger_seconds * fps);
          break;

        case "activate_next":
          // For sequential activation, increment counter
          const currentCount = (props.activatedCount as number) || 0;
          props.activatedCount = currentCount + 1;
          break;

        default:
          props[`sync_${syncPoint.action}`] = {
            triggered: true,
            at: syncPoint.trigger_seconds,
            params: syncPoint.params,
          };
      }
    }
  }

  return props;
}

/**
 * Apply easing function to progress.
 */
function applyEasing(
  progress: number,
  easing?: "linear" | "ease-in" | "ease-out" | "ease-in-out" | "spring"
): number {
  switch (easing) {
    case "ease-in":
      return Easing.in(Easing.cubic)(progress);
    case "ease-out":
      return Easing.out(Easing.cubic)(progress);
    case "ease-in-out":
      return Easing.inOut(Easing.cubic)(progress);
    case "spring":
      // Approximate spring with overshoot
      return Easing.out(Easing.back(1.5))(progress);
    case "linear":
    default:
      return progress;
  }
}

export default StoryboardPlayer;
