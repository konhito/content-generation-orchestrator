export type ShortBeatMode = "character" | "component" | "meme";
export type TransitionKind = "accent-expand" | "accent-contract" | "punch-cut" | "hard-cut";

export const rendererForMode = (mode?: string): "character" | "visual" =>
  mode === "character" ? "character" : "visual";

export const transitionForModes = (from?: string, to?: string): TransitionKind => {
  return "hard-cut";
};
