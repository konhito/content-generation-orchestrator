import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { ScriptProps } from "../types/script";
import { SceneRenderer } from "./SceneRenderer";

/**
 * Main explainer video component that sequences all scenes.
 */
export const ExplainerVideo: React.FC<ScriptProps> = ({ title, scenes, style }) => {
  const { fps } = useVideoConfig();

  // Calculate frame offsets for each scene
  let currentFrame = 0;
  const sceneFrames = scenes.map((scene) => {
    const startFrame = currentFrame;
    const durationFrames = Math.ceil(scene.durationInSeconds * fps);
    currentFrame += durationFrames;
    return { scene, startFrame, durationFrames };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: style.backgroundColor }}>
      {sceneFrames.map(({ scene, startFrame, durationFrames }) => (
        <Sequence
          key={scene.sceneId}
          from={startFrame}
          durationInFrames={durationFrames}
          name={`Scene ${scene.sceneId}: ${scene.title}`}
        >
          <SceneRenderer scene={scene} style={style} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
