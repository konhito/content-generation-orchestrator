"""Vertical scene generator for YouTube Shorts."""

from pathlib import Path
from typing import Any

from ..config import Config, load_config
from ..project.loader import Project
from .models import ShortScript, ShortConfig


# Vertical styles template for 1080x1920 shorts
VERTICAL_STYLES_TEMPLATE = '''/**
 * Shared Style Constants for {project_title} - VERTICAL (YouTube Shorts)
 *
 * Light theme with glow effects optimized for 9:16 vertical format.
 * Canvas: 1080x1920 (YouTube Shorts format)
 */

import React from "react";

// Outfit font family (loaded via @remotion/google-fonts in Root.tsx)
const outfitFont = '"Outfit", -apple-system, BlinkMacSystemFont, sans-serif';

// ===== COLOR PALETTE - LIGHT THEME WITH GLOW =====
export const COLORS = {{
  // Background colors
  background: "#FAFAFA",
  surface: "#FFFFFF",
  surfaceAlt: "#F5F5F7",

  // Text colors
  text: "#1A1A1A",
  textDim: "#555555",
  textMuted: "#888888",

  // Accent colors (optimized for glow effects)
  primary: "#0066FF",
  primaryGlow: "#0088FF",
  secondary: "#FF6600",
  secondaryGlow: "#FF8800",
  success: "#00AA55",
  successGlow: "#00DD77",
  warning: "#F5A623",
  warningGlow: "#FFB840",
  error: "#E53935",
  errorGlow: "#FF5555",
  purple: "#8844FF",
  purpleGlow: "#AA66FF",
  cyan: "#00BCD4",
  cyanGlow: "#00E5FF",
  pink: "#E91E63",
  pinkGlow: "#FF4081",
  lime: "#76B900",
  limeGlow: "#9BE000",

  // Layer visualization
  layerActive: "#0066FF",
  layerCompleted: "#00AA55",
  layerPending: "#E0E0E5",

  // Borders and shadows
  border: "#E0E0E5",
  borderLight: "#EEEEEE",
  shadow: "rgba(0, 0, 0, 0.08)",

  // Glow-specific
  glowSubtle: "rgba(0, 102, 255, 0.15)",
  glowMedium: "rgba(0, 102, 255, 0.3)",
  glowStrong: "rgba(0, 102, 255, 0.5)",
}};

// ===== FONTS =====
export const FONTS = {{
  primary: outfitFont,
  heading: outfitFont,
  mono: "SF Mono, Monaco, Consolas, monospace",
  system: outfitFont,
}};

// ===== SCENE INDICATOR =====
export const SCENE_INDICATOR = {{
  container: {{
    top: 40,
    left: 24,
    width: 44,
    height: 44,
    borderRadius: 10,
  }},
  text: {{
    fontSize: 16,
    fontWeight: 600 as const,
  }},
}};

// ===== SIDEBAR AREA =====
// No sidebar for vertical format
export const SIDEBAR = {{
  width: 0,
  padding: 0,
  gap: 0,
  borderRadius: 8,
}};

// ===== LAYOUT GRID SYSTEM =====
// Designed for 1080x1920 canvas (YouTube Shorts / 9:16 vertical)
// All values are CALCULATED from base constraints - no hardcoded positions

// Base constraints for vertical format
const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const SIDEBAR_WIDTH = 0;
const SIDEBAR_GAP = 0;
const MARGIN_LEFT = 40;
const MARGIN_RIGHT = 40;
const TITLE_HEIGHT = 160;     // Space for title at top
const BOTTOM_MARGIN = 200;    // Space for CTA and references at bottom

// Derived values
const USABLE_LEFT = MARGIN_LEFT;
const USABLE_RIGHT = CANVAS_WIDTH - SIDEBAR_WIDTH - SIDEBAR_GAP;
const USABLE_WIDTH = USABLE_RIGHT - USABLE_LEFT;
const USABLE_TOP = TITLE_HEIGHT;
const USABLE_BOTTOM = CANVAS_HEIGHT - BOTTOM_MARGIN;
const USABLE_HEIGHT = USABLE_BOTTOM - USABLE_TOP;

// Quadrant calculations (2x3 grid for vertical - two columns, three rows)
const QUADRANT_WIDTH = USABLE_WIDTH / 2;
const QUADRANT_HEIGHT = USABLE_HEIGHT / 3;
const LEFT_CENTER_X = USABLE_LEFT + QUADRANT_WIDTH / 2;
const RIGHT_CENTER_X = USABLE_LEFT + QUADRANT_WIDTH + QUADRANT_WIDTH / 2;
const TOP_CENTER_Y = USABLE_TOP + QUADRANT_HEIGHT / 2;
const MIDDLE_CENTER_Y = USABLE_TOP + QUADRANT_HEIGHT + QUADRANT_HEIGHT / 2;
const BOTTOM_CENTER_Y = USABLE_TOP + QUADRANT_HEIGHT * 2 + QUADRANT_HEIGHT / 2;

export const LAYOUT = {{
  // Canvas dimensions (VERTICAL)
  canvas: {{
    width: CANVAS_WIDTH,
    height: CANVAS_HEIGHT,
  }},

  // Margins from edges
  margin: {{
    left: MARGIN_LEFT,
    right: MARGIN_RIGHT,
    top: 40,
    bottom: 60,
  }},

  // Sidebar area (none for vertical)
  sidebar: {{
    width: SIDEBAR_WIDTH,
    gap: SIDEBAR_GAP,
  }},

  // Content area bounds
  content: {{
    startX: USABLE_LEFT,
    endX: USABLE_RIGHT,
    width: USABLE_WIDTH,
    startY: USABLE_TOP,
    endY: USABLE_BOTTOM,
    height: USABLE_HEIGHT,
  }},

  // QUADRANT SYSTEM - 2x3 grid for vertical layout
  quadrants: {{
    // Usable bounds
    bounds: {{
      left: USABLE_LEFT,
      right: USABLE_RIGHT,
      top: USABLE_TOP,
      bottom: USABLE_BOTTOM,
      width: USABLE_WIDTH,
      height: USABLE_HEIGHT,
    }},
    // Quadrant centers (2 columns x 3 rows)
    topLeft: {{ cx: LEFT_CENTER_X, cy: TOP_CENTER_Y }},
    topRight: {{ cx: RIGHT_CENTER_X, cy: TOP_CENTER_Y }},
    middleLeft: {{ cx: LEFT_CENTER_X, cy: MIDDLE_CENTER_Y }},
    middleRight: {{ cx: RIGHT_CENTER_X, cy: MIDDLE_CENTER_Y }},
    bottomLeft: {{ cx: LEFT_CENTER_X, cy: BOTTOM_CENTER_Y }},
    bottomRight: {{ cx: RIGHT_CENTER_X, cy: BOTTOM_CENTER_Y }},
    // Quadrant dimensions
    quadrantWidth: QUADRANT_WIDTH,
    quadrantHeight: QUADRANT_HEIGHT,
  }},

  // Title area (centered at top for vertical)
  title: {{
    x: CANVAS_WIDTH / 2,
    y: 60,
    subtitleY: 110,
  }},
}};

// ===== ANIMATION =====
export const ANIMATION = {{
  fadeIn: 20,
  stagger: 5,
  spring: {{ damping: 20, stiffness: 120, mass: 1 }},
}};

// ===== FLEXIBLE LAYOUT HELPERS =====

/**
 * Get layout positions for a flexible grid (any number of columns/rows)
 */
export const getFlexibleGrid = (
  columns: number,
  rows: number,
  gap: number = 20
): Array<{{ cx: number; cy: number; width: number; height: number }}> => {{
  const cellWidth = (LAYOUT.content.width - (columns - 1) * gap) / columns;
  const cellHeight = (LAYOUT.content.height - (rows - 1) * gap) / rows;

  const cells: Array<{{ cx: number; cy: number; width: number; height: number }}> = [];

  for (let row = 0; row < rows; row++) {{
    for (let col = 0; col < columns; col++) {{
      const cx = LAYOUT.content.startX + (cellWidth + gap) * col + cellWidth / 2;
      const cy = LAYOUT.content.startY + (cellHeight + gap) * row + cellHeight / 2;
      cells.push({{ cx, cy, width: cellWidth, height: cellHeight }});
    }}
  }}

  return cells;
}};

/**
 * Get single centered position
 */
export const getCenteredPosition = (): {{ cx: number; cy: number; width: number; height: number }} => {{
  return {{
    cx: LAYOUT.content.startX + LAYOUT.content.width / 2,
    cy: LAYOUT.content.startY + LAYOUT.content.height / 2,
    width: LAYOUT.content.width,
    height: LAYOUT.content.height,
  }};
}};

/**
 * Get two-column layout
 */
export const getTwoColumnLayout = (gap: number = 20): {{
  left: {{ cx: number; cy: number; width: number; height: number }};
  right: {{ cx: number; cy: number; width: number; height: number }};
}} => {{
  const colWidth = (LAYOUT.content.width - gap) / 2;
  return {{
    left: {{
      cx: LAYOUT.content.startX + colWidth / 2,
      cy: LAYOUT.content.startY + LAYOUT.content.height / 2,
      width: colWidth,
      height: LAYOUT.content.height,
    }},
    right: {{
      cx: LAYOUT.content.startX + colWidth + gap + colWidth / 2,
      cy: LAYOUT.content.startY + LAYOUT.content.height / 2,
      width: colWidth,
      height: LAYOUT.content.height,
    }},
  }};
}};

/**
 * Get two-row layout (common for vertical videos)
 */
export const getTwoRowLayout = (gap: number = 20): {{
  top: {{ cx: number; cy: number; width: number; height: number }};
  bottom: {{ cx: number; cy: number; width: number; height: number }};
}} => {{
  const rowHeight = (LAYOUT.content.height - gap) / 2;
  return {{
    top: {{
      cx: LAYOUT.content.startX + LAYOUT.content.width / 2,
      cy: LAYOUT.content.startY + rowHeight / 2,
      width: LAYOUT.content.width,
      height: rowHeight,
    }},
    bottom: {{
      cx: LAYOUT.content.startX + LAYOUT.content.width / 2,
      cy: LAYOUT.content.startY + rowHeight + gap + rowHeight / 2,
      width: LAYOUT.content.width,
      height: rowHeight,
    }},
  }};
}};

/**
 * Get three-row layout (ideal for vertical videos)
 */
export const getThreeRowLayout = (gap: number = 20): {{
  top: {{ cx: number; cy: number; width: number; height: number }};
  middle: {{ cx: number; cy: number; width: number; height: number }};
  bottom: {{ cx: number; cy: number; width: number; height: number }};
}} => {{
  const rowHeight = (LAYOUT.content.height - 2 * gap) / 3;
  return {{
    top: {{
      cx: LAYOUT.content.startX + LAYOUT.content.width / 2,
      cy: LAYOUT.content.startY + rowHeight / 2,
      width: LAYOUT.content.width,
      height: rowHeight,
    }},
    middle: {{
      cx: LAYOUT.content.startX + LAYOUT.content.width / 2,
      cy: LAYOUT.content.startY + rowHeight + gap + rowHeight / 2,
      width: LAYOUT.content.width,
      height: rowHeight,
    }},
    bottom: {{
      cx: LAYOUT.content.startX + LAYOUT.content.width / 2,
      cy: LAYOUT.content.startY + 2 * (rowHeight + gap) + rowHeight / 2,
      width: LAYOUT.content.width,
      height: rowHeight,
    }},
  }};
}};

/**
 * Get centered style object for absolute positioning
 */
export const getCenteredStyle = (
  cx: number,
  cy: number,
  scale: number = 1
): React.CSSProperties => ({{
  position: "absolute",
  left: cx * scale,
  top: cy * scale,
  transform: "translate(-50%, -50%)",
}});
'''


# CTA scene template for YouTube Shorts
CTA_SCENE_TEMPLATE = '''/**
 * CTA Scene for {project_title} - YouTube Short
 *
 * Engaging call-to-action with hook question, thumbnail, and action prompt.
 */

import React from "react";
import {{ useCurrentFrame, useVideoConfig, interpolate, spring, Img }} from "remotion";
import {{ LAYOUT, COLORS, FONTS, ANIMATION }} from "./styles";

interface CTASceneProps {{
  startFrame?: number;
  hookQuestion: string;
  ctaText: string;
  thumbnailUrl?: string;
  channelName?: string;
}}

export const CTAScene: React.FC<CTASceneProps> = ({{
  startFrame = 0,
  hookQuestion,
  ctaText,
  thumbnailUrl,
  channelName = "",
}}) => {{
  const frame = useCurrentFrame();
  const {{ fps, width, height }} = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1080, height / 1920);

  // Animation phases
  const questionOpacity = interpolate(localFrame, [0, 20], [0, 1], {{
    extrapolateRight: "clamp",
  }});

  const questionScale = spring({{
    frame: localFrame,
    fps,
    config: {{ damping: 15, stiffness: 100 }},
  }});

  const thumbnailY = interpolate(localFrame, [20, 50], [200, 0], {{
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  }});

  const thumbnailOpacity = interpolate(localFrame, [20, 40], [0, 1], {{
    extrapolateRight: "clamp",
  }});

  const ctaOpacity = interpolate(localFrame, [60, 80], [0, 1], {{
    extrapolateRight: "clamp",
  }});

  const arrowBounce = Math.sin(localFrame * 0.15) * 8;

  const playButtonPulse = 1 + Math.sin(localFrame * 0.1) * 0.05;

  return (
    <div
      style={{{{
        position: "absolute",
        width: "100%",
        height: "100%",
        background: COLORS.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 40 * scale,
      }}}}
    >
      {{/* Hook Question */}}
      <div
        style={{{{
          fontSize: 48 * scale,
          fontFamily: FONTS.heading,
          fontWeight: 700,
          color: COLORS.text,
          textAlign: "center",
          marginBottom: 60 * scale,
          opacity: questionOpacity,
          transform: `scale(${{questionScale}})`,
          textShadow: `0 0 30px ${{COLORS.primaryGlow}}`,
          maxWidth: 900 * scale,
          lineHeight: 1.3,
        }}}}
      >
        {{hookQuestion}}
      </div>

      {{/* Thumbnail Preview */}}
      <div
        style={{{{
          position: "relative",
          width: 700 * scale,
          height: 400 * scale,
          borderRadius: 20 * scale,
          overflow: "hidden",
          boxShadow: `0 20px 60px ${{COLORS.shadow}}, 0 0 40px ${{COLORS.glowMedium}}`,
          opacity: thumbnailOpacity,
          transform: `translateY(${{thumbnailY * scale}}px)`,
          border: `4px solid ${{COLORS.primary}}`,
        }}}}
      >
        {{thumbnailUrl ? (
          <Img
            src={{thumbnailUrl}}
            style={{{{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}}}
          />
        ) : (
          <div
            style={{{{
              width: "100%",
              height: "100%",
              background: `linear-gradient(135deg, ${{COLORS.primary}} 0%, ${{COLORS.purple}} 100%)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}}}
          >
            <div
              style={{{{
                fontSize: 80 * scale,
                color: "white",
              }}}}
            >
              ▶
            </div>
          </div>
        )}}

        {{/* Play button overlay */}}
        <div
          style={{{{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: `translate(-50%, -50%) scale(${{playButtonPulse}})`,
            width: 100 * scale,
            height: 100 * scale,
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.95)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 0 30px ${{COLORS.glowStrong}}`,
          }}}}
        >
          <div
            style={{{{
              width: 0,
              height: 0,
              borderLeft: `${{40 * scale}}px solid ${{COLORS.primary}}`,
              borderTop: `${{24 * scale}}px solid transparent`,
              borderBottom: `${{24 * scale}}px solid transparent`,
              marginLeft: 8 * scale,
            }}}}
          />
        </div>
      </div>

      {{/* CTA Text */}}
      <div
        style={{{{
          marginTop: 60 * scale,
          opacity: ctaOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}}}
      >
        <div
          style={{{{
            fontSize: 36 * scale,
            fontFamily: FONTS.primary,
            fontWeight: 600,
            color: COLORS.text,
            marginBottom: 20 * scale,
          }}}}
        >
          {{ctaText}}
        </div>

        {{/* Animated arrow */}}
        <div
          style={{{{
            fontSize: 48 * scale,
            color: COLORS.primary,
            transform: `translateY(${{arrowBounce * scale}}px)`,
          }}}}
        >
          ↓
        </div>
      </div>

      {{/* Channel name */}}
      {{channelName && (
        <div
          style={{{{
            position: "absolute",
            bottom: 60 * scale,
            fontSize: 24 * scale,
            fontFamily: FONTS.primary,
            color: COLORS.textMuted,
            opacity: ctaOpacity,
          }}}}
        >
          {{channelName}}
        </div>
      )}}
    </div>
  );
}};

export default CTAScene;
'''


# Index template for short scenes
SHORT_INDEX_TEMPLATE = '''/**
 * Scene Registry for {project_title} - YouTube Short
 *
 * Auto-generated index mapping scene types to components.
 */

{imports}

// Export all scenes
{exports}

// Scene registry for dynamic rendering
export const sceneRegistry: Record<string, React.ComponentType<{{ startFrame?: number }}>> = {{
{registry_entries}
}};

// Get all available scene types
export const getAvailableScenes = (): string[] => Object.keys(sceneRegistry);

// Get scene component by type
export const getSceneComponent = (
  sceneType: string
): React.ComponentType<{{ startFrame?: number }}> | undefined => {{
  return sceneRegistry[sceneType];
}};
'''


class ShortSceneGenerator:
    """Generates vertical Remotion scenes for YouTube Shorts."""

    def __init__(self, config: Config | None = None):
        """Initialize the generator.

        Args:
            config: Configuration object. If None, loads default.
        """
        self.config = config or load_config()

    def generate_vertical_styles(
        self,
        scenes_dir: Path,
        project_title: str,
    ) -> Path:
        """Generate styles.ts with vertical LAYOUT for shorts.

        Args:
            scenes_dir: Directory to write styles.ts to.
            project_title: Title for the comment header.

        Returns:
            Path to the generated styles.ts file.
        """
        styles_path = scenes_dir / "styles.ts"
        content = VERTICAL_STYLES_TEMPLATE.format(project_title=project_title)

        scenes_dir.mkdir(parents=True, exist_ok=True)
        with open(styles_path, "w", encoding="utf-8") as f:
            f.write(content)

        return styles_path

    def generate_cta_scene(
        self,
        scenes_dir: Path,
        project_title: str,
    ) -> Path:
        """Generate the CTA scene component.

        Args:
            scenes_dir: Directory to write CTAScene.tsx to.
            project_title: Title for the comment header.

        Returns:
            Path to the generated CTAScene.tsx file.
        """
        cta_path = scenes_dir / "CTAScene.tsx"
        content = CTA_SCENE_TEMPLATE.format(project_title=project_title)

        scenes_dir.mkdir(parents=True, exist_ok=True)
        with open(cta_path, "w", encoding="utf-8") as f:
            f.write(content)

        return cta_path

    def generate_index(
        self,
        scenes_dir: Path,
        project_title: str,
        scene_components: list[dict[str, str]],
    ) -> Path:
        """Generate the index.ts file for short scenes.

        Args:
            scenes_dir: Directory to write index.ts to.
            project_title: Title for the comment header.
            scene_components: List of {name, filename, scene_key} dicts.

        Returns:
            Path to the generated index.ts file.
        """
        # Build imports
        imports = []
        exports = []
        registry_entries = []

        for scene in scene_components:
            name = scene["name"]
            filename = scene["filename"].replace(".tsx", "")
            scene_key = scene["scene_key"]

            imports.append(f'import {{ {name} }} from "./{filename}";')
            exports.append(f'export {{ {name} }} from "./{filename}";')
            registry_entries.append(f"  {scene_key}: {name},")

        content = SHORT_INDEX_TEMPLATE.format(
            project_title=project_title,
            imports="\n".join(imports),
            exports="\n".join(exports),
            registry_entries="\n".join(registry_entries),
        )

        index_path = scenes_dir / "index.ts"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

        return index_path

    def setup_short_scenes(
        self,
        project: Project,
        short_script: ShortScript,
        variant: str = "default",
    ) -> dict[str, Path]:
        """Setup scene directory structure for a short.

        Args:
            project: The source project.
            short_script: The short script with scenes.
            variant: Variant name.

        Returns:
            Dictionary with paths to generated files.
        """
        variant_dir = project.root_dir / "short" / variant
        scenes_dir = variant_dir / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)

        # Generate vertical styles
        styles_path = self.generate_vertical_styles(
            scenes_dir, f"{short_script.title}"
        )

        # Generate CTA scene
        cta_path = self.generate_cta_scene(scenes_dir, f"{short_script.title}")

        # Generate index with CTA scene
        scene_components = [
            {
                "name": "CTAScene",
                "filename": "CTAScene.tsx",
                "scene_key": "cta",
            }
        ]

        index_path = self.generate_index(
            scenes_dir, f"{short_script.title}", scene_components
        )

        return {
            "scenes_dir": scenes_dir,
            "styles_path": styles_path,
            "cta_path": cta_path,
            "index_path": index_path,
        }
