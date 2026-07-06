import React from "react";
import {Img, staticFile} from "remotion";
import {interpolate, spring} from "remotion";

import {ShortsCharacterScene} from "./ShortsCharacterScene";
import type {ShortsBeat} from "./ShortsPlayer";
import {ShortsVisualArea} from "./ShortsVisualArea";
import type {VisualRecipe} from "./recipeTypes";
import {SHORTS_COLORS, SHORTS_GLASS, SHORTS_MOTION} from "./shortsStyle";
import type {CharacterTrack} from "./characterTypes";

type RecipeBeat = ShortsBeat & {visual_recipe?: VisualRecipe};

export const recipeLayerPlan = (recipe: VisualRecipe) => ({
  characterPosition: recipe.character.position,
  componentPosition: recipe.component.position,
  memeVisible: recipe.meme.role !== "none" && recipe.meme.intensity > 0,
});

export const shouldShowMixedStagePanel = (recipe: VisualRecipe) =>
  recipe.component.position === "main_stage";

export const shouldShowMixedVisualPanel = (recipe: VisualRecipe) =>
  recipe.component.position === "main_stage" ||
  recipe.component.position === "background_stage" ||
  recipe.component.component_type === "meme_card";

const recipeTheme = (recipe: VisualRecipe) => {
  if (recipe.meme.intensity > 0) return SHORTS_COLORS.secondary;
  if (recipe.intent === "hook" || recipe.attention_strategy === "visual_metaphor") return SHORTS_COLORS.primary;
  if (recipe.intent === "contrast" || recipe.intent === "reveal") return SHORTS_COLORS.accent;
  if (recipe.component.component_type.includes("chart") || recipe.component.component_type.includes("timeline")) {
    return SHORTS_COLORS.warning;
  }
  return SHORTS_COLORS.primary;
};

export const visualBeatForMixedScene = (beat: RecipeBeat): RecipeBeat => ({
  ...beat,
  start_seconds: 0,
  end_seconds: beat.end_seconds - beat.start_seconds,
});

export const ShortsMixedScene: React.FC<{
  beat: RecipeBeat;
  frame: number;
  fps: number;
  scale: number;
}> = ({beat, frame, fps, scale}) => {
  const recipe = beat.visual_recipe;
  if (!recipe) {
    return <ShortsVisualArea beat={beat} frame={frame} fps={fps} scale={scale} />;
  }

  const characterTrack = beat.character_data ?? fallbackCharacterTrack(recipe, beat.end_seconds - beat.start_seconds);
  const theme = recipeTheme(recipe);
  const entrance = spring({frame, fps, config: SHORTS_MOTION.smoothSpring});
  const push = recipe.camera.motion === "slow_push"
      ? interpolate(frame, [0, 120], [0.97, 1.02], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
    : 1;
  const visualBeat = visualBeatForMixedScene(beat);
  const mainStage = recipe.component.position === "main_stage";
  const memeStage = recipe.component.component_type === "meme_card";
  const showStagePanel = shouldShowMixedStagePanel(recipe);
  const showVisualPanel = shouldShowMixedVisualPanel(recipe);
  return (
    <div style={{position: "relative", width: 1080 * scale, height: 1500 * scale, overflow: "hidden"}}>
      {recipe.background_image ? (
        <Img
          src={staticFile(recipe.background_image)}
          data-asset={recipe.background_image}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "saturate(0.96) contrast(0.95)",
          }}
        />
      ) : null}
      {showStagePanel ? (
        <div
          style={{
            position: "absolute",
            inset: `${150 * scale}px ${110 * scale}px ${190 * scale}px`,
            borderRadius: 28 * scale,
            ...SHORTS_GLASS,
            background: "transparent",
            border: "none",
            boxShadow: "none",
            backdropFilter: "none",
            WebkitBackdropFilter: "none",
            transform: `scale(${push})`,
            opacity: entrance,
          }}
        />
      ) : null}

      {showVisualPanel ? (
        <div
          style={{
            position: "absolute",
            left: memeStage ? 40 * scale : mainStage ? 390 * scale : 135 * scale,
            top: memeStage ? 90 * scale : mainStage ? 220 * scale : 170 * scale,
            width: memeStage ? 1000 * scale : mainStage ? 590 * scale : 810 * scale,
            height: memeStage ? 900 * scale : mainStage ? 720 * scale : 610 * scale,
            borderRadius: memeStage ? 0 : 24 * scale,
            border: memeStage ? "none" : `1px solid ${SHORTS_COLORS.border}`,
            background: memeStage ? "transparent" : SHORTS_COLORS.surfaceSubtle,
            backdropFilter: memeStage ? undefined : "blur(24px)",
            WebkitBackdropFilter: memeStage ? undefined : "blur(24px)",
            boxShadow: memeStage ? "none" : `0 18px 70px ${SHORTS_COLORS.shadow}`,
            opacity: mainStage ? 0.98 : 0.92,
            overflow: "hidden",
            transform: memeStage ? "none" : `scale(${push})`,
          }}
          >
          <ShortsVisualArea beat={visualBeat} frame={frame} fps={fps} scale={scale * (memeStage ? 1 : mainStage ? 0.72 : 0.66)} />
        </div>
      ) : null}

      {recipe.character.presence !== "none" ? (
        <ShortsCharacterScene
          track={characterTrack}
          frame={frame}
          fps={fps}
          scale={scale}
          position={recipe.character.position}
          characterScale={recipe.character.scale * (mainStage ? 1 : 0.88)}
          motion={recipe.character.motion}
          showStage={false}
        />
      ) : null}
    </div>
  );
};

const fallbackCharacterTrack = (recipe: VisualRecipe, durationSeconds: number): CharacterTrack => {
  const duration = Math.max(0.5, durationSeconds || 4);
  return {
    version: 1,
    character_id: "character_1",
    duration_seconds: duration,
    base_pose: recipe.character.body_type || "body1",
    base_emotion: recipe.character.emotion || "content",
    events: [
      {
        start: 0,
        end: duration,
        pose: recipe.character.body_type || "body1",
        emotion: recipe.character.emotion || "content",
        head: recipe.character.head || "M",
      },
    ],
    mouth_cues: [],
    blink_cues: [{start: Math.min(1.2, duration / 2), end: Math.min(1.32, duration / 2 + 0.12)}],
  };
};
