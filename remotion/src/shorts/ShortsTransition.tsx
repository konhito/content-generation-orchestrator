import React from "react";
import {interpolate} from "remotion";

import {transitionForModes} from "./shortsDispatch";
import {SHORTS_COLORS, SHORTS_MOTION} from "./shortsStyle";

interface ShortsTransitionProps {
  from?: string;
  to?: string;
  localFrame: number;
  scale: number;
}

export const ShortsTransition: React.FC<ShortsTransitionProps> = ({from, to, localFrame, scale}) => {
  const kind = transitionForModes(from, to);
  if (kind === "hard-cut" || localFrame >= SHORTS_MOTION.transitionFrames) return null;
  const progress = interpolate(localFrame, [0, SHORTS_MOTION.transitionFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const punch = kind === "punch-cut";
  const contracting = kind === "accent-contract";
  const size = punch ? 1280 : (contracting ? 1300 - progress * 1220 : 80 + progress * 1220);
  return (
    <div style={{position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden"}}>
      <div style={{
        position: "absolute",
        left: "50%",
        top: "42%",
        width: size * scale,
        height: size * scale,
        borderRadius: punch ? 48 * scale : "50%",
        border: `${punch ? 18 : 8}px solid ${punch ? SHORTS_COLORS.warning : SHORTS_COLORS.primary}`,
        opacity: punch ? 1 - progress : 0.75 * (1 - progress),
        transform: `translate(-50%, -50%) rotate(${punch ? -2 + progress * 4 : 0}deg)`,
        boxShadow: `0 ${18 * scale}px ${60 * scale}px ${SHORTS_COLORS.primaryGlow}`,
      }} />
    </div>
  );
};
