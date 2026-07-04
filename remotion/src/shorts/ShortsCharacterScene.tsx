import React from "react";
import {Img, interpolate, spring, staticFile} from "remotion";

import {resolveCharacterState, type CharacterState, type CharacterTrack} from "./characterTypes";
import {SHORTS_COLORS, SHORTS_FONTS, SHORTS_MOTION} from "./shortsStyle";

export const characterAssetPaths = (state: CharacterState) => {
  const mood = state.mouth.endsWith("_s") ? "sad" : "happy";
  const eyes = state.blinking
    ? `${state.emotion}/${state.emotion}_blink/02.png`
    : `${state.emotion}/${state.emotion}_${state.head}.png`;
  return {
    body: `characters/synctoon/character_1/body/${state.pose}.png`,
    head: `characters/synctoon/character_1/head/${state.head}/${state.head}.png`,
    eyes: `characters/synctoon/character_1/eyes/${eyes}`,
    mouth: `characters/synctoon/character_1/mouth/${mood}/${state.mouth}.png`,
  };
};

interface ShortsCharacterSceneProps {
  track: CharacterTrack;
  frame: number;
  fps: number;
  scale: number;
  emphasis?: string;
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
  emphasis,
}) => {
  const time = Math.max(0, frame / fps);
  const state = resolveCharacterState(track, time);
  const paths = characterAssetPaths(state);
  const entrance = spring({frame, fps, config: SHORTS_MOTION.smoothSpring});
  const drift = interpolate(frame, [0, Math.max(1, track.duration_seconds * fps)], [12, -8], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{position: "relative", width: 1080 * scale, height: 1500 * scale, overflow: "hidden"}}>
      <div style={{
        position: "absolute",
        inset: `${120 * scale}px ${80 * scale}px ${170 * scale}px`,
        borderRadius: 48 * scale,
        border: `${2 * scale}px solid ${SHORTS_COLORS.primary}44`,
        background: `radial-gradient(circle at 50% 35%, ${SHORTS_COLORS.primary}22, ${SHORTS_COLORS.surface}dd 65%)`,
        boxShadow: `0 30px 100px ${SHORTS_COLORS.primary}18`,
      }} />
      <div style={{
        position: "absolute",
        left: 70 * scale,
        top: 170 * scale,
        width: 940 * scale,
        height: 1040 * scale,
        transform: `translateY(${drift * scale}px) scale(${0.94 + entrance * 0.06})`,
        opacity: entrance,
      }}>
        <Img src={staticFile(paths.body)} style={layerStyle(185 * scale, 470 * scale, 570 * scale, 510 * scale)} />
        <Img src={staticFile(paths.head)} style={layerStyle(185 * scale, 190 * scale, 570 * scale, 510 * scale)} />
        <Img src={staticFile(paths.eyes)} style={layerStyle(225 * scale, 250 * scale, 500 * scale, 300 * scale)} />
        <Img src={staticFile(paths.mouth)} style={layerStyle(365 * scale, 480 * scale, 220 * scale, 100 * scale)} />
      </div>
      {emphasis && (
        <div style={{
          position: "absolute",
          top: 120 * scale,
          left: 110 * scale,
          padding: `${18 * scale}px ${28 * scale}px`,
          borderRadius: 999,
          background: SHORTS_COLORS.primary,
          color: SHORTS_COLORS.background,
          fontFamily: SHORTS_FONTS.primary,
          fontWeight: 800,
          fontSize: 30 * scale,
          textTransform: "uppercase",
          letterSpacing: 1.5 * scale,
          transform: `scale(${0.9 + entrance * 0.1})`,
        }}>
          {emphasis}
        </div>
      )}
    </div>
  );
};
