import React from "react";
import {Img, interpolate, spring, staticFile} from "remotion";

import {resolveCharacterState, type CharacterState, type CharacterTrack} from "./characterTypes";
import {SHORTS_COLORS, SHORTS_MOTION} from "./shortsStyle";

export const characterAssetPaths = (state: CharacterState) => {
  const mood = state.mouth.endsWith("_s") ? "sad" : "happy";
  const eyeEmotion = SUPPORTED_EYE_EMOTIONS.has(state.emotion) ? state.emotion : "content";
  const eyes = state.blinking
    ? `${eyeEmotion}/${eyeEmotion}_blink/02.png`
    : `${eyeEmotion}/${eyeEmotion}_${state.head}.png`;
  return {
    body: `characters/synctoon/character_1/body/${state.pose}.png`,
    head: `characters/synctoon/character_1/head/${state.head}/${state.head}.png`,
    eyes: `characters/synctoon/character_1/eyes/${eyes}`,
    mouth: `characters/synctoon/character_1/mouth/${mood}/${state.mouth}.png`,
  };
};

const SUPPORTED_EYE_EMOTIONS = new Set([
  "angry",
  "angry_2",
  "bore",
  "bore_2",
  "content",
  "content_2",
  "crazy",
  "crazy_2",
  "evil_laugh",
  "happy",
  "happy_2",
  "sad",
  "sad_2",
  "surprised",
  "surprised_2",
  "worried",
  "worried_2",
]);

interface ShortsCharacterSceneProps {
  track: CharacterTrack;
  frame: number;
  fps: number;
  scale: number;
  position?: string;
  characterScale?: number;
  motion?: string;
  showStage?: boolean;
}

const layerStyle = (left: number, top: number, width: number, height: number): React.CSSProperties => ({
  position: "absolute",
  left,
  top,
  width,
  height,
  objectFit: "contain",
});

export const ShortsCharacterScene: React.FC<ShortsCharacterSceneProps> = ({
  track,
  frame,
  fps,
  scale,
  position = "lower_center",
  characterScale = 1,
  motion = "gentle_bob",
  showStage = true,
}) => {
  const time = Math.max(0, frame / fps);
  const state = resolveCharacterState(track, time);
  const paths = characterAssetPaths(state);
  const entrance = spring({frame, fps, config: SHORTS_MOTION.smoothSpring});
  const beatFrames = Math.max(1, track.duration_seconds * fps);
  const bob = Math.sin(frame * (motion === "snap_shift" ? 0.42 : 0.16)) * (motion === "subtle_bob" ? 4 : motion === "snap_shift" ? 12 : 8);
  const sway = Math.sin(frame * (motion === "quick_shift" ? 0.24 : 0.11)) * (motion === "side_bob" ? 18 : 7);
  const lean = motion === "snap_shift" ? Math.sin(frame * 0.33) * 2.5 : motion === "quick_shift" ? 1.4 : 0.8;
  const drift = interpolate(frame, [0, beatFrames], [10, -10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const positionOffsetMap: Record<string, {left: number; top: number; width: number; height: number}> = {
    lower_center: {left: 90, top: 210, width: 900, height: 1000},
    side_left: {left: -90, top: 220, width: 560, height: 900},
    side_right: {left: 520, top: 220, width: 560, height: 900},
    upper_left: {left: 20, top: 30, width: 620, height: 840},
    upper_right: {left: 440, top: 30, width: 620, height: 840},
    center_float: {left: 150, top: 140, width: 780, height: 920},
    lower_left: {left: 10, top: 260, width: 620, height: 860},
    lower_right: {left: 430, top: 260, width: 620, height: 860},
  };
  const positionOffset = positionOffsetMap[position] || positionOffsetMap.lower_center;
  const stageScale = position.includes("side") ? 0.92 : 1;
  const characterTilt = position.includes("side")
    ? (position === "side_left" ? -1.2 : 1.2)
    : 0.4;
  const motionScale = 0.96 + entrance * 0.05;

  return (
    <div style={{position: "relative", width: 1080 * scale, height: 1500 * scale, overflow: "hidden"}}>
      {showStage && (
        <div style={{
          position: "absolute",
          inset: `${120 * scale}px ${80 * scale}px ${170 * scale}px`,
          borderRadius: 48 * scale,
          border: `${2 * scale}px solid ${SHORTS_COLORS.primary}44`,
          background: `radial-gradient(circle at 50% 35%, ${SHORTS_COLORS.primary}22, ${SHORTS_COLORS.surface}dd 65%)`,
          boxShadow: `0 30px 100px ${SHORTS_COLORS.primary}18`,
        }} />
      )}
      <div style={{
        position: "absolute",
        left: positionOffset.left * scale,
        top: positionOffset.top * scale,
        width: positionOffset.width * scale,
        height: positionOffset.height * scale,
        transform: `translate(${sway * scale}px, ${(drift + bob) * scale}px) rotate(${characterTilt + lean}deg) scale(${characterScale * motionScale * stageScale})`,
        opacity: entrance,
        transformOrigin: position.includes("side") ? "center center" : "center bottom",
      }}>
        <Img src={staticFile(paths.body)} data-asset={paths.body} style={layerStyle(185 * scale, 470 * scale, 570 * scale, 510 * scale)} />
        <Img src={staticFile(paths.head)} data-asset={paths.head} style={layerStyle(185 * scale, 190 * scale, 570 * scale, 510 * scale)} />
        <Img src={staticFile(paths.eyes)} data-asset={paths.eyes} style={layerStyle(225 * scale, 250 * scale, 500 * scale, 300 * scale)} />
        <Img src={staticFile(paths.mouth)} data-asset={paths.mouth} style={layerStyle(365 * scale, 480 * scale, 220 * scale, 100 * scale)} />
      </div>
    </div>
  );
};
