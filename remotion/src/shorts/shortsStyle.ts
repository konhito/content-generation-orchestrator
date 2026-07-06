export const SHORTS_COLORS = {
  background: "#f5f7fb",
  backgroundGradientStart: "#fbfcff",
  backgroundGradientEnd: "#e9eef8",
  surface: "rgba(255, 255, 255, 0.42)",
  surfaceStrong: "rgba(255, 255, 255, 0.58)",
  surfaceSubtle: "rgba(255, 255, 255, 0.22)",
  text: "#111827",
  textMuted: "#64748b",
  primary: "#0a84ff",
  primaryGlow: "rgba(10, 132, 255, 0.28)",
  secondary: "#5e5ce6",
  accent: "#64d2ff",
  success: "#30d158",
  warning: "#ff9f0a",
  border: "rgba(255, 255, 255, 0.72)",
  borderMuted: "rgba(148, 163, 184, 0.28)",
  shadow: "rgba(15, 23, 42, 0.14)",
};

export const SHORTS_FONTS = {
  primary: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  heading: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  mono: '"SF Mono", Monaco, Consolas, monospace',
};

export const SHORTS_MOTION = {
  transitionFrames: 5,
  smoothSpring: {damping: 200},
  snappySpring: {damping: 20, stiffness: 200},
};

export const SHORTS_GLASS = {
  background: SHORTS_COLORS.surface,
  border: `1px solid ${SHORTS_COLORS.border}`,
  boxShadow: `0 24px 70px ${SHORTS_COLORS.shadow}, inset 0 1px 0 rgba(255, 255, 255, 0.72)`,
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
};
