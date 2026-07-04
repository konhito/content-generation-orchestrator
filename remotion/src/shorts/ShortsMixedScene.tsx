import React from "react";
import {interpolate, spring} from "remotion";

import {ShortsCharacterScene} from "./ShortsCharacterScene";
import type {ShortsBeat} from "./ShortsPlayer";
import {ShortsVisualArea} from "./ShortsVisualArea";
import type {VisualRecipe} from "./recipeTypes";
import {SHORTS_COLORS, SHORTS_FONTS, SHORTS_MOTION} from "./shortsStyle";

type RecipeBeat = ShortsBeat & {visual_recipe?: VisualRecipe};

export const recipeLayerPlan = (recipe: VisualRecipe) => ({
  characterPosition: recipe.character.position,
  componentPosition: recipe.component.position,
  memeVisible: recipe.meme.role !== "none" && recipe.meme.intensity > 0,
});

export const ShortsMixedScene: React.FC<{
  beat: RecipeBeat;
  frame: number;
  fps: number;
  scale: number;
}> = ({beat, frame, fps, scale}) => {
  const recipe = beat.visual_recipe;
  if (!recipe || !beat.character_data) {
    return <ShortsVisualArea beat={beat} frame={frame} fps={fps} scale={scale} />;
  }

  const entrance = spring({frame, fps, config: SHORTS_MOTION.smoothSpring});
  const push = recipe.camera.motion === "slow_push"
    ? interpolate(frame, [0, 120], [0.97, 1.02], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
    : 1;
  const memePop = spring({
    frame: Math.max(
      0,
      frame - Math.round((beat.end_seconds - beat.start_seconds) * fps * 0.45),
    ),
    fps,
    config: SHORTS_MOTION.snappySpring,
  });

  return (
    <div style={{position: "relative", width: 1080 * scale, height: 1500 * scale, overflow: "hidden"}}>
      <div
        style={{
          position: "absolute",
          inset: `${120 * scale}px ${80 * scale}px ${170 * scale}px`,
          borderRadius: 48 * scale,
          border: `${2 * scale}px solid ${SHORTS_COLORS.primary}44`,
          background: `radial-gradient(circle at 50% 35%, ${SHORTS_COLORS.primary}1f, ${SHORTS_COLORS.surface}e8 65%)`,
          boxShadow: `0 30px 100px ${SHORTS_COLORS.primary}18`,
          transform: `scale(${push})`,
          opacity: entrance,
        }}
      />

      <div
        style={{
          position: "absolute",
          left: recipe.component.position === "main_stage" ? 360 * scale : 130 * scale,
          top: recipe.component.position === "main_stage" ? 260 * scale : 190 * scale,
          width: recipe.component.position === "main_stage" ? 600 * scale : 820 * scale,
          height: recipe.component.position === "main_stage" ? 760 * scale : 850 * scale,
          opacity: 0.82,
          transform: `scale(${push})`,
        }}
      >
        <ShortsVisualArea beat={beat} frame={frame} fps={fps} scale={scale * 0.78} />
      </div>

      <ShortsCharacterScene
        track={beat.character_data}
        frame={frame}
        fps={fps}
        scale={scale}
        emphasis={beat.visual.primary_text}
        position={recipe.character.position}
        characterScale={recipe.character.scale}
        showStage={false}
      />

      {recipe.meme.role !== "none" && recipe.meme.intensity > 0 && (
        <div
          style={{
            position: "absolute",
            right: 100 * scale,
            top: 230 * scale,
            padding: `${18 * scale}px ${24 * scale}px`,
            borderRadius: 28 * scale,
            background: "#fff",
            color: "#050509",
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 900,
            fontSize: 34 * scale,
            textTransform: "uppercase",
            boxShadow: `0 18px 60px ${SHORTS_COLORS.primary}55`,
            transform: `rotate(-3deg) scale(${0.2 + memePop * 0.8})`,
            opacity: Math.min(1, memePop) * recipe.meme.intensity * 1.4,
          }}
        >
          {recipe.meme.style === "interrupt_card" ? "WAIT, WHAT?" : "MEME CUT"}
        </div>
      )}
    </div>
  );
};
