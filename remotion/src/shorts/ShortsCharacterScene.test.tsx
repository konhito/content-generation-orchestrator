import {describe, expect, it} from "vitest";

import {resolveCharacterState, type CharacterTrack} from "./characterTypes";
import {characterAssetPaths} from "./ShortsCharacterScene";

const track: CharacterTrack = {
  version: 1,
  character_id: "character_1",
  duration_seconds: 3,
  base_pose: "body1",
  base_emotion: "content",
  events: [
    {start: 0, end: 1.5, pose: "body1", emotion: "content", head: "M"},
    {start: 1.5, end: 3, pose: "body24", emotion: "worried", head: "R"},
  ],
  mouth_cues: [{start: 1.8, end: 2.0, shape: "a_e_s"}],
  blink_cues: [{start: 1.85, end: 1.95}],
};

describe("resolveCharacterState", () => {
  it("selects performance, mouth, and blink state at a frame boundary", () => {
    expect(resolveCharacterState(track, 1.9)).toMatchObject({
      pose: "body24",
      emotion: "worried",
      head: "R",
      mouth: "a_e_s",
      blinking: true,
    });
  });

  it("uses base values between mouth and blink cues", () => {
    expect(resolveCharacterState(track, 0.5)).toMatchObject({
      pose: "body1",
      emotion: "content",
      head: "M",
      mouth: "m_b_close_h",
      blinking: false,
    });
  });
});

describe("characterAssetPaths", () => {
  it("maps layered state to project-public SyncToon assets", () => {
    expect(characterAssetPaths({
      pose: "body24", emotion: "worried", head: "R", mouth: "a_e_s", blinking: true,
    })).toEqual({
      body: "characters/synctoon/character_1/body/body24.png",
      head: "characters/synctoon/character_1/head/R/R.png",
      eyes: "characters/synctoon/character_1/eyes/worried/worried_blink/02.png",
      mouth: "characters/synctoon/character_1/mouth/sad/a_e_s.png",
    });
  });
});
