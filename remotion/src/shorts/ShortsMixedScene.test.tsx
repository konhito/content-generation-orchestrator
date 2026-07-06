import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {describe, expect, it} from "vitest";

import {
  recipeLayerPlan,
  shouldShowMixedStagePanel,
  shouldShowMixedVisualPanel,
  ShortsMixedScene,
  visualBeatForMixedScene,
} from "./ShortsMixedScene";
import type {VisualRecipe} from "./recipeTypes";

const recipe: VisualRecipe = {
  recipe_id: "host_foreground_concept_backdrop",
  layout: "character_foreground_visual_backdrop",
  intent: "explain",
  attention_strategy: "host_demonstrates_concept",
  character: {
    presence: "primary",
    position: "lower_center",
    scale: 0.82,
    pose_intent: "explain",
    body_type: "body35",
    head: "M",
    emotion: "curious",
    motion: "gentle_bob",
    gesture: "technical",
  },
  component: {
    role: "main_explanation",
    component_type: "concept_card",
    position: "background_stage",
    emphasis_words: ["predicts", "truth"],
  },
  meme: {
    role: "accent",
    style: "sticker_pop",
    timing: "after_key_claim",
    intensity: 0.35,
  },
  camera: {
    motion: "slow_push",
    punch_zoom_on: null,
  },
  transition: {
    transition_in: "match_cut",
    transition_out: "soft_cut",
  },
  background_image: "characters/synctoon/character_1/background/explanation/explanation.png",
};

describe("recipeLayerPlan", () => {
  it("keeps component behind the host for foreground recipes", () => {
    const plan = recipeLayerPlan(recipe);

    expect(plan.characterPosition).toBe("lower_center");
    expect(plan.componentPosition).toBe("background_stage");
    expect(plan.memeVisible).toBe(true);
  });

  it("moves host to sidecar for diagram recipes", () => {
    const plan = recipeLayerPlan({
      ...recipe,
      layout: "character_sidecar_visual_main",
      character: {...recipe.character, position: "side_left", scale: 0.58, motion: "side_bob"},
      component: {...recipe.component, position: "main_stage"},
    });

    expect(plan.characterPosition).toBe("side_left");
    expect(plan.componentPosition).toBe("main_stage");
  });

  it("keeps meme layers visible when the recipe requests them", () => {
    const plan = recipeLayerPlan(recipe);

    expect(plan.memeVisible).toBe(true);
  });

  it("does not frame character backdrop recipes inside a full-screen card", () => {
    expect(shouldShowMixedStagePanel({
      ...recipe,
      component: {...recipe.component, component_type: "text_highlight", position: "background_stage"},
      meme: {...recipe.meme, role: "none", intensity: 0},
    })).toBe(false);
    expect(shouldShowMixedVisualPanel({
      ...recipe,
      component: {...recipe.component, component_type: "text_highlight", position: "background_stage"},
      meme: {...recipe.meme, role: "none", intensity: 0},
    })).toBe(true);
  });

  it("keeps a smaller frame for explanation components and meme cards", () => {
    expect(shouldShowMixedStagePanel({
      ...recipe,
      component: {...recipe.component, component_type: "progress_bars", position: "main_stage"},
    })).toBe(true);
    expect(shouldShowMixedVisualPanel({
      ...recipe,
      component: {...recipe.component, component_type: "concept_card", position: "background_stage"},
    })).toBe(true);
    expect(shouldShowMixedStagePanel({
      ...recipe,
      component: {...recipe.component, component_type: "meme_card", position: "background_stage"},
    })).toBe(false);
    expect(shouldShowMixedVisualPanel({
      ...recipe,
      component: {...recipe.component, component_type: "meme_card", position: "background_stage"},
    })).toBe(true);
  });
});

describe("ShortsMixedScene", () => {
  it("exports a React component", () => {
    expect(typeof ShortsMixedScene).toBe("function");
    expect(
      React.isValidElement(
        <ShortsMixedScene beat={{} as any} frame={0} fps={30} scale={1} />,
      ),
    ).toBe(true);
  });

  it("normalizes nested visual beat timing to local scene frames", () => {
    const beat = visualBeatForMixedScene({
      start_seconds: 12,
      end_seconds: 18,
    } as any);

    expect(beat.start_seconds).toBe(0);
    expect(beat.end_seconds).toBe(6);
  });

  it("renders recipe background and fallback character when character data is missing", () => {
    const markup = renderToStaticMarkup(
      <ShortsMixedScene
        beat={{
          id: "beat_1",
          start_seconds: 0,
          end_seconds: 5,
          mode: "meme",
          visual_recipe: recipe,
          visual: {
            type: "meme_card",
            primary_text: "TOP",
            secondary_text: "BOTTOM",
            scene_config: {component_type: "meme_card"},
          },
        } as any}
        frame={12}
        fps={30}
        scale={1}
      />,
    );

    expect(markup).toContain("background/explanation/explanation.png");
    expect(markup).toContain("body/body35.png");
    expect(markup).toContain("head/M/M.png");
    expect(markup).not.toContain("rgba(245,247,251,0.24)");
  });
});
