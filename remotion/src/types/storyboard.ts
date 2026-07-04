/**
 * TypeScript types for storyboard JSON structure.
 * These mirror the JSON schema in storyboards/schema/storyboard.schema.json
 */

export interface Storyboard {
  id: string;
  title: string;
  description?: string;
  duration_seconds: number;
  audio?: AudioConfig;
  style?: StyleConfig;
  beats: Beat[];
}

export interface AudioConfig {
  file: string;
  duration_seconds: number;
  word_timestamps?: WordTimestamp[];
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface StyleConfig {
  background_color?: string;
  primary_color?: string;
  secondary_color?: string;
  font_family?: string;
}

export interface Beat {
  id: string;
  start_seconds: number;
  end_seconds: number;
  voiceover?: string;
  elements?: Element[];
  sync_points?: SyncPoint[];
}

export interface Element {
  id: string;
  component: string;
  props?: Record<string, unknown>;
  position?: Position;
  animations?: Animation[];
  enter?: Transition;
  exit?: Transition;
}

export interface Position {
  x?: number | "left" | "center" | "right";
  y?: number | "top" | "center" | "bottom";
  anchor?: "top-left" | "top-center" | "top-right" | "center-left" | "center" | "center-right" | "bottom-left" | "bottom-center" | "bottom-right";
}

export interface Animation {
  action: string;
  at_seconds: number;
  duration_seconds?: number;
  easing?: "linear" | "ease-in" | "ease-out" | "ease-in-out" | "spring";
  params?: Record<string, unknown>;
}

export interface Transition {
  type?: "fade" | "slide" | "scale" | "none";
  direction?: "up" | "down" | "left" | "right";
  duration_seconds?: number;
  delay_seconds?: number;
}

export interface SyncPoint {
  trigger_word?: string;
  trigger_seconds: number;
  target: string;
  action: string;
  params?: Record<string, unknown>;
}

/**
 * Validate that an object conforms to the Storyboard interface.
 * Returns validation errors or empty array if valid.
 */
export function validateStoryboard(obj: unknown): string[] {
  const errors: string[] = [];

  if (!obj || typeof obj !== "object") {
    return ["Storyboard must be an object"];
  }

  const storyboard = obj as Record<string, unknown>;

  // Required fields
  if (typeof storyboard.id !== "string") {
    errors.push("Missing or invalid 'id' field");
  }
  if (typeof storyboard.title !== "string") {
    errors.push("Missing or invalid 'title' field");
  }
  if (typeof storyboard.duration_seconds !== "number") {
    errors.push("Missing or invalid 'duration_seconds' field");
  }
  if (!Array.isArray(storyboard.beats)) {
    errors.push("Missing or invalid 'beats' array");
  } else {
    // Validate each beat
    storyboard.beats.forEach((beat, index) => {
      const beatErrors = validateBeat(beat, index);
      errors.push(...beatErrors);
    });
  }

  return errors;
}

function validateBeat(beat: unknown, index: number): string[] {
  const errors: string[] = [];
  const prefix = `beats[${index}]`;

  if (!beat || typeof beat !== "object") {
    return [`${prefix}: must be an object`];
  }

  const b = beat as Record<string, unknown>;

  if (typeof b.id !== "string") {
    errors.push(`${prefix}: missing or invalid 'id'`);
  }
  if (typeof b.start_seconds !== "number") {
    errors.push(`${prefix}: missing or invalid 'start_seconds'`);
  }
  if (typeof b.end_seconds !== "number") {
    errors.push(`${prefix}: missing or invalid 'end_seconds'`);
  }

  // Validate elements if present
  if (b.elements !== undefined) {
    if (!Array.isArray(b.elements)) {
      errors.push(`${prefix}: 'elements' must be an array`);
    } else {
      b.elements.forEach((el, elIndex) => {
        const elErrors = validateElement(el, `${prefix}.elements[${elIndex}]`);
        errors.push(...elErrors);
      });
    }
  }

  return errors;
}

function validateElement(element: unknown, prefix: string): string[] {
  const errors: string[] = [];

  if (!element || typeof element !== "object") {
    return [`${prefix}: must be an object`];
  }

  const el = element as Record<string, unknown>;

  if (typeof el.id !== "string") {
    errors.push(`${prefix}: missing or invalid 'id'`);
  }
  if (typeof el.component !== "string") {
    errors.push(`${prefix}: missing or invalid 'component'`);
  }

  return errors;
}

/**
 * Calculate the total number of frames for a storyboard.
 */
export function calculateTotalFrames(storyboard: Storyboard, fps: number = 30): number {
  return Math.ceil(storyboard.duration_seconds * fps);
}

/**
 * Get all unique component types used in a storyboard.
 */
export function getUsedComponents(storyboard: Storyboard): string[] {
  const components = new Set<string>();

  for (const beat of storyboard.beats) {
    if (beat.elements) {
      for (const element of beat.elements) {
        components.add(element.component);
      }
    }
  }

  return Array.from(components);
}

/**
 * Get all elements that are active at a given time.
 */
export function getActiveElements(storyboard: Storyboard, timeSeconds: number): Element[] {
  const elements: Element[] = [];

  for (const beat of storyboard.beats) {
    if (timeSeconds >= beat.start_seconds && timeSeconds < beat.end_seconds) {
      if (beat.elements) {
        elements.push(...beat.elements);
      }
    }
  }

  return elements;
}
