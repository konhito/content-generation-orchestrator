import {describe, expect, it} from "vitest";

import {rendererForBeat} from "./ShortsPlayer";
import {rendererForMode, transitionForModes} from "./shortsDispatch";

describe("Shorts mode dispatch", () => {
  it("dispatches all supported full-frame modes", () => {
    expect(rendererForMode("character")).toBe("character");
    expect(rendererForMode("meme")).toBe("visual");
    expect(rendererForMode("component")).toBe("visual");
    expect(rendererForMode(undefined)).toBe("visual");
  });

  it("uses purposeful mode-boundary transitions", () => {
    expect(transitionForModes("character", "component")).toBe("accent-expand");
    expect(transitionForModes("component", "character")).toBe("accent-contract");
    expect(transitionForModes("character", "meme")).toBe("punch-cut");
    expect(transitionForModes("component", "component")).toBe("hard-cut");
  });

  it("uses mixed renderer when a visual recipe exists", () => {
    expect(rendererForBeat({visual_recipe: {recipe_id: "x"}} as any)).toBe("mixed");
  });

  it("keeps legacy character renderer without visual recipe", () => {
    expect(rendererForBeat({mode: "character", character_data: {}} as any)).toBe("character");
  });
});
