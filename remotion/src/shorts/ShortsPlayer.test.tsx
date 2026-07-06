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

  it("keeps mode boundaries visually continuous without transition overlays", () => {
    expect(transitionForModes("character", "component")).toBe("hard-cut");
    expect(transitionForModes("component", "character")).toBe("hard-cut");
    expect(transitionForModes("character", "meme")).toBe("hard-cut");
    expect(transitionForModes("component", "component")).toBe("hard-cut");
  });

  it("uses mixed renderer when a visual recipe exists", () => {
    expect(rendererForBeat({visual_recipe: {recipe_id: "x"}} as any)).toBe("mixed");
  });

  it("keeps legacy character renderer without visual recipe", () => {
    expect(rendererForBeat({mode: "character", character_data: {}} as any)).toBe("character");
  });

  it("keeps character beats character-only even when visual metadata exists", () => {
    expect(rendererForBeat({
      mode: "character",
      character_data: {},
      visual: {type: "flow_diagram", primary_text: ""},
    } as any)).toBe("character");
  });
});
