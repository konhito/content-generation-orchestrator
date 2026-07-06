import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {describe, expect, it} from "vitest";

import {GIPHY_PLAYBACK_RATE, ShortsVisualArea, flowStepsForBeat, isTextVisualType, memeAssetRenderMode} from "./ShortsVisualArea";
import {SHORTS_COLORS} from "./shortsStyle";

describe("Shorts macOS glass theme", () => {
  it("uses light macOS glass color tokens", () => {
    expect(SHORTS_COLORS.background).toBe("#f5f7fb");
    expect(SHORTS_COLORS.surface).toContain("rgba(255, 255, 255");
    expect(SHORTS_COLORS.text).toBe("#111827");
    expect(SHORTS_COLORS.primary).toBe("#0a84ff");
  });

  it("renders visual cards with translucent glass styling", () => {
    const markup = renderToStaticMarkup(
      <ShortsVisualArea
        beat={{
          id: "beat_001",
          start_seconds: 0,
          end_seconds: 3,
          caption_text: "Caption",
          visual: {
            type: "question",
            primary_text: "Clean glass?",
          },
        } as any}
        frame={0}
        fps={30}
        scale={1}
      />,
    );

    expect(markup).toContain("backdrop-filter:blur(28px)");
    expect(markup).toContain("rgba(255, 255, 255, 0.42)");
    expect(markup).toContain("0 24px 70px rgba(15, 23, 42, 0.14)");
  });
});

describe("ShortsVisualArea meme cards", () => {
  it("renders the fetched meme image when image_path is present", () => {
    const markup = renderToStaticMarkup(
      <ShortsVisualArea
        beat={{
          id: "beat_001",
          start_seconds: 0,
          end_seconds: 3,
          caption_text: "Caption",
          visual: {
            type: "meme_card",
            primary_text: "MODEL SAID TRUST ME",
            secondary_text: "SOURCE SAID ABSOLUTELY NOT",
            scene_config: {
              component_type: "meme_card",
              image_path: "short/default/memes/assets/imgflip-asset.jpg",
            },
          },
        } as any}
        frame={0}
        fps={30}
        scale={1}
      />,
    );

    expect(markup).toContain("short/default/memes/assets/imgflip-asset.jpg");
    expect(markup).not.toContain("file://");
    expect(markup).toContain("Meme asset");
  });

  it("routes GIPHY mp4 memes to synchronized slow video playback", () => {
    expect(memeAssetRenderMode("short/default/memes/assets/giphy_abc.mp4")).toBe("video");
    expect(GIPHY_PLAYBACK_RATE).toBe(0.55);
  });

  it("derives flow steps from caption when generated labels are empty", () => {
    expect(flowStepsForBeat({
      caption_text: "Official details versus viral rumor",
      visual: {primary_text: "", secondary_text: "", tertiary_text: ""},
    } as any)).toEqual(["Official details", "viral rumor"]);
  });

  it("keeps attention components visual-only to avoid duplicate captions", () => {
    const markup = renderToStaticMarkup(
      <ShortsVisualArea
        beat={{
          id: "beat_001",
          start_seconds: 0,
          end_seconds: 3,
          caption_text: "Most people got it wrong",
          visual: {type: "attention_visual", primary_text: "VIRAL RUMOR"},
        } as any}
        frame={30}
        fps={30}
        scale={1}
      />,
    );

    expect(markup).not.toContain("VIRAL RUMOR");
    expect(markup).not.toContain("Most people got it wrong");
  });

  it("classifies all text-only component types for graphical replacement", () => {
    expect(["big_number", "comparison", "text_highlight", "simple_flow", "icon_stat", "key_point", "question"].every(isTextVisualType)).toBe(true);
    expect(isTextVisualType("token_grid")).toBe(false);
  });

  it("renders meme cards large and without pop or shake transforms", () => {
    const markup = renderToStaticMarkup(
      <ShortsVisualArea
        beat={{
          id: "beat_001",
          start_seconds: 0,
          end_seconds: 3,
          caption_text: "Caption",
          visual: {
            type: "meme_card",
            primary_text: "MODEL SAID TRUST ME",
            secondary_text: "SOURCE SAID ABSOLUTELY NOT",
          },
        } as any}
        frame={12}
        fps={30}
        scale={1}
      />,
    );

    expect(markup).toContain("width:940px");
    expect(markup).toContain("min-height:760px");
    expect(markup).not.toContain("rotate(");
    expect(markup).not.toContain("scale(");
  });
});
