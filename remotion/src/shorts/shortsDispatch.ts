export type ShortBeatMode = "character" | "component" | "meme";
export type TransitionKind = "accent-expand" | "accent-contract" | "punch-cut" | "hard-cut";

export const rendererForMode = (mode?: string): "character" | "visual" =>
  mode === "character" ? "character" : "visual";

export const transitionForModes = (from?: string, to?: string): TransitionKind => {
  if (to === "meme" || from === "meme") return "punch-cut";
  if (from === "character" && to === "component") return "accent-expand";
  if (from === "component" && to === "character") return "accent-contract";
  return "hard-cut";
};
