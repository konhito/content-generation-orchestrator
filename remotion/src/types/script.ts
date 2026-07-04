import { z } from "zod";

/**
 * Visual element types that can be rendered
 */
export const VisualElementSchema = z.object({
  type: z.enum(["text", "token_grid", "bar_chart", "arrow", "box", "code"]),
  props: z.record(z.unknown()),
});

/**
 * Visual cue for a scene - describes what should be shown
 */
export const VisualCueSchema = z.object({
  description: z.string(),
  visualType: z.enum(["animation", "diagram", "code", "equation", "image"]),
  elements: z.array(z.string()),
  durationInSeconds: z.number(),
});

/**
 * A single scene in the video
 */
export const SceneSchema = z.object({
  sceneId: z.string(),
  sceneType: z.enum(["hook", "context", "explanation", "insight", "conclusion"]),
  title: z.string(),
  voiceover: z.string(),
  visualCue: VisualCueSchema,
  durationInSeconds: z.number(),
  notes: z.string().optional(),
});

/**
 * Full script props passed to the video
 */
export const ScriptPropsSchema = z.object({
  title: z.string(),
  scenes: z.array(SceneSchema),
  style: z.object({
    backgroundColor: z.string().default("#0f0f1a"),
    primaryColor: z.string().default("#00d9ff"),
    secondaryColor: z.string().default("#ff6b35"),
    accentColor: z.string().default("#00ff88"),
    fontFamily: z.string().default("Inter, sans-serif"),
  }).default({}),
});

// TypeScript types derived from Zod schemas
export type VisualElement = z.infer<typeof VisualElementSchema>;
export type VisualCue = z.infer<typeof VisualCueSchema>;
export type Scene = z.infer<typeof SceneSchema>;
export type ScriptProps = z.infer<typeof ScriptPropsSchema>;

/**
 * Default props for preview/testing
 */
export const defaultScriptProps: ScriptProps = {
  title: "LLM Inference Explained",
  scenes: [
    {
      sceneId: "the_speed_problem",
      sceneType: "hook",
      title: "The Speed Problem",
      voiceover: "Every time you send a message to ChatGPT, something remarkable happens.",
      visualCue: {
        description: "Show tokens appearing one by one, then speed up dramatically",
        visualType: "animation",
        elements: ["token_counter", "speed_indicator"],
        durationInSeconds: 15,
      },
      durationInSeconds: 15,
    },
    {
      sceneId: "the_two_phases",
      sceneType: "explanation",
      title: "The Two Phases",
      voiceover: "LLM inference has two distinct phases: prefill and decode.",
      visualCue: {
        description: "Split screen showing prefill vs decode",
        visualType: "animation",
        elements: ["token_grid", "gpu_bar"],
        durationInSeconds: 20,
      },
      durationInSeconds: 20,
    },
  ],
  style: {
    backgroundColor: "#0f0f1a",
    primaryColor: "#00d9ff",
    secondaryColor: "#ff6b35",
    accentColor: "#00ff88",
    fontFamily: "Inter, sans-serif",
  },
};
