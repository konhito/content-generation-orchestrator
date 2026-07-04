import React from "react";
import {describe, expect, it} from "vitest";

import {recipeLayerPlan, ShortsMixedScene, visualBeatForMixedScene} from "./ShortsMixedScene";
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
    emotion: "curious",
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
      character: {...recipe.character, position: "side_left", scale: 0.58},
      component: {...recipe.component, position: "main_stage"},
    });

    expect(plan.characterPosition).toBe("side_left");
    expect(plan.componentPosition).toBe("main_stage");
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
});
