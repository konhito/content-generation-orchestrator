/**
 * Common Scene Registry
 *
 * Placeholder for generic reusable scenes that can be shared across projects.
 * Examples: IntroScene, OutroScene, TransitionScene, etc.
 */

import React from "react";
import { SceneComponent } from "../index";

/**
 * Registry of common/shared scene components
 */
export const COMMON_SCENES: Record<string, SceneComponent> = {
  // Add common scenes here as they're created:
  // intro: IntroScene,
  // outro: OutroScene,
};

export function getCommonScene(type: string): SceneComponent | undefined {
  return COMMON_SCENES[type];
}
