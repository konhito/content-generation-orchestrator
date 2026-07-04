import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Scene, ScriptProps } from "../types/script";
import { TitleCard } from "../components/TitleCard";
import { TokenGrid } from "../components/TokenGrid";
import { ProgressBar } from "../components/ProgressBar";
import { TextReveal } from "../components/TextReveal";

interface SceneRendererProps {
  scene: Scene;
  style: ScriptProps["style"];
}

/**
 * Renders a single scene based on its type and visual cues.
 * Maps scene types and visual elements to specific components.
 */
export const SceneRenderer: React.FC<SceneRendererProps> = ({ scene, style }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Fade in/out for scene transitions
  const fadeIn = interpolate(frame, [0, fps * 0.5], [0, 1], {
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 0.5, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp" }
  );
  const opacity = Math.min(fadeIn, fadeOut);

  // Choose renderer based on scene type and visual cue
  const renderSceneContent = () => {
    const elements = scene.visualCue.elements;

    // Hook scenes: dramatic title reveal
    if (scene.sceneType === "hook") {
      return (
        <TitleCard
          title={scene.title}
          subtitle={getFirstSentence(scene.voiceover)}
          style={style}
        />
      );
    }

    // Explanation scenes: based on visual elements
    if (elements.includes("token_grid") || elements.includes("token_counter")) {
      return (
        <TokenGridScene scene={scene} style={style} />
      );
    }

    if (elements.includes("gpu_bar") || elements.includes("memory_bar")) {
      return (
        <UtilizationScene scene={scene} style={style} />
      );
    }

    // Default: text-based scene with title
    return (
      <DefaultScene scene={scene} style={style} />
    );
  };

  return (
    <AbsoluteFill style={{ opacity }}>
      {renderSceneContent()}
    </AbsoluteFill>
  );
};

/**
 * Scene with token grid animation (for prefill/decode visualization)
 */
const TokenGridScene: React.FC<SceneRendererProps> = ({ scene, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        padding: 80,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 40,
      }}
    >
      <TextReveal
        text={scene.title}
        style={{
          fontSize: 64,
          fontWeight: "bold",
          color: style.primaryColor,
          fontFamily: style.fontFamily,
        }}
      />
      <TokenGrid
        rows={4}
        cols={8}
        tokenColor={style.primaryColor}
        backgroundColor={style.backgroundColor}
        animationMode={scene.sceneType === "hook" ? "sequential" : "parallel"}
      />
      <TextReveal
        text={getFirstSentence(scene.voiceover)}
        style={{
          fontSize: 32,
          color: "#ffffff",
          fontFamily: style.fontFamily,
          textAlign: "center",
          maxWidth: 1200,
        }}
        delay={fps}
      />
    </AbsoluteFill>
  );
};

/**
 * Scene with utilization bars (GPU, memory bandwidth)
 */
const UtilizationScene: React.FC<SceneRendererProps> = ({ scene, style }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Animate GPU utilization based on scene content
  const isPrefill = scene.title.toLowerCase().includes("prefill");
  const gpuTarget = isPrefill ? 0.95 : 0.05;
  const memoryTarget = isPrefill ? 0.3 : 0.95;

  const progress = interpolate(frame, [fps, durationInFrames - fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        padding: 80,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 60,
      }}
    >
      <TextReveal
        text={scene.title}
        style={{
          fontSize: 64,
          fontWeight: "bold",
          color: style.primaryColor,
          fontFamily: style.fontFamily,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 40 }}>
        <ProgressBar
          label="GPU Compute Utilization"
          value={gpuTarget * progress}
          color={style.accentColor}
          backgroundColor="#333"
        />
        <ProgressBar
          label="Memory Bandwidth"
          value={memoryTarget * progress}
          color={style.secondaryColor}
          backgroundColor="#333"
        />
      </div>
      <TextReveal
        text={getFirstSentence(scene.voiceover)}
        style={{
          fontSize: 28,
          color: "#cccccc",
          fontFamily: style.fontFamily,
          maxWidth: 1400,
        }}
        delay={fps * 2}
      />
    </AbsoluteFill>
  );
};

/**
 * Default scene with title and text
 */
const DefaultScene: React.FC<SceneRendererProps> = ({ scene, style }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        padding: 100,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 40,
      }}
    >
      <TextReveal
        text={scene.title}
        style={{
          fontSize: 72,
          fontWeight: "bold",
          color: style.primaryColor,
          fontFamily: style.fontFamily,
          textAlign: "center",
        }}
      />
      <TextReveal
        text={scene.voiceover}
        style={{
          fontSize: 36,
          color: "#ffffff",
          fontFamily: style.fontFamily,
          textAlign: "center",
          maxWidth: 1400,
          lineHeight: 1.5,
        }}
        delay={fps}
      />
    </AbsoluteFill>
  );
};

/**
 * Helper to get first sentence from text
 */
function getFirstSentence(text: string): string {
  const match = text.match(/^[^.!?]+[.!?]/);
  return match ? match[0] : text.slice(0, 100);
}
