import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Token } from "./Token";

export type TokenMode = "prefill" | "decode" | "inactive";

export interface TokenRowProps {
  tokens: string[];
  mode: TokenMode;
  activateAt?: number; // Frame at which activation begins
  tokenDelay?: number; // Frames between token activations (decode mode)
  label?: string;
  showLabel?: boolean;
  style?: React.CSSProperties;
}

export const TokenRow: React.FC<TokenRowProps> = ({
  tokens,
  mode,
  activateAt = 0,
  tokenDelay = 20, // ~0.67 seconds at 30fps
  label,
  showLabel = true,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Calculate activation frame for each token based on mode
  const getTokenActivateAt = (index: number): number => {
    if (mode === "inactive") {
      return Infinity; // Never activate
    }
    if (mode === "prefill") {
      return activateAt; // All activate at the same time
    }
    // Decode mode: sequential activation
    return activateAt + index * tokenDelay;
  };

  // Label opacity
  const labelOpacity =
    showLabel && label
      ? Math.min(1, Math.max(0, (frame - activateAt + 15) / 10))
      : 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        ...style,
      }}
    >
      {/* Label */}
      {label && (
        <div
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: 28,
            fontWeight: 600,
            color: "#e0e0e0",
            textTransform: "uppercase",
            letterSpacing: 4,
            opacity: labelOpacity,
          }}
        >
          {label}
        </div>
      )}

      {/* Tokens */}
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          gap: 12,
          flexWrap: "wrap",
          justifyContent: "center",
        }}
      >
        {tokens.map((token, index) => (
          <Token
            key={index}
            text={token}
            isActive={mode !== "inactive"}
            activateAt={getTokenActivateAt(index)}
            index={index}
          />
        ))}
      </div>
    </div>
  );
};

export default TokenRow;
