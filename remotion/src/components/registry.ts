/**
 * Component Registry
 *
 * Maps component type names (used in storyboard JSON) to actual React components.
 * This allows storyboards to reference components by string name.
 */

import React from "react";
import { Token } from "./Token";
import { TokenRow } from "./TokenRow";
import { GPUGauge } from "./GPUGauge";
import { TitleCard } from "./TitleCard";
import { TextReveal } from "./TextReveal";
import { ProgressBar } from "./ProgressBar";

// Component type definition - using 'any' for dynamic props from storyboard
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type RegisteredComponent = React.FC<any>;

// Registry mapping component names to implementations
export const componentRegistry: Record<string, RegisteredComponent> = {
  // Core components
  "token": Token,
  "token_row": TokenRow,
  "gpu_gauge": GPUGauge,
  "title_card": TitleCard,
  "text_reveal": TextReveal,
  "progress_bar": ProgressBar,

  // Placeholder components (to be implemented)
  "prompt_input": createPlaceholder("prompt_input"),
  "container": createPlaceholder("container"),
  "divider": createPlaceholder("divider"),
  "highlight_overlay": createPlaceholder("highlight_overlay"),
};

/**
 * Get a component by name from the registry.
 * Throws if component is not found.
 */
export function getComponent(name: string): RegisteredComponent {
  const component = componentRegistry[name];
  if (!component) {
    throw new Error(`Component "${name}" not found in registry. Available: ${Object.keys(componentRegistry).join(", ")}`);
  }
  return component;
}

/**
 * Check if a component exists in the registry.
 */
export function hasComponent(name: string): boolean {
  return name in componentRegistry;
}

/**
 * List all registered component names.
 */
export function listComponents(): string[] {
  return Object.keys(componentRegistry);
}

/**
 * Create a placeholder component for components not yet implemented.
 * Shows a visible box with the component name for debugging.
 */
function createPlaceholder(name: string): RegisteredComponent {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const PlaceholderComponent: React.FC<any> = (props) => {
    return React.createElement("div", {
      style: {
        padding: "20px",
        border: "2px dashed #666",
        borderRadius: "8px",
        backgroundColor: "rgba(100, 100, 100, 0.2)",
        color: "#888",
        fontFamily: "monospace",
        fontSize: "14px",
      }
    }, `[${name}] ${JSON.stringify(props, null, 2).slice(0, 100)}...`);
  };
  PlaceholderComponent.displayName = `Placeholder_${name}`;
  return PlaceholderComponent;
}

export default componentRegistry;
