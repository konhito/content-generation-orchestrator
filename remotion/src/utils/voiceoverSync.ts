/**
 * Voiceover Sync Utilities
 *
 * Provides helpers to sync visual animations with voiceover word timestamps.
 * Uses the manifest.json as the source of truth for timing.
 */

import { interpolate, Easing } from "remotion";

// Type definitions
export interface WordTimestamp {
  word: string;
  start_seconds: number;
  end_seconds: number;
}

export interface SceneVoiceover {
  scene_id: string;
  audio_path: string;
  duration_seconds: number;
  word_timestamps: WordTimestamp[];
}

/**
 * Get the frame number when a specific word starts
 */
export function getWordStartFrame(
  wordTimestamps: WordTimestamp[],
  wordOrPhrase: string,
  fps: number,
  occurrence: number = 1
): number {
  const searchWords = wordOrPhrase.toLowerCase().split(" ");
  let found = 0;

  for (let i = 0; i <= wordTimestamps.length - searchWords.length; i++) {
    const matches = searchWords.every((searchWord, j) =>
      wordTimestamps[i + j].word.toLowerCase().replace(/[.,!?]$/, "") === searchWord.replace(/[.,!?]$/, "")
    );

    if (matches) {
      found++;
      if (found === occurrence) {
        return Math.round(wordTimestamps[i].start_seconds * fps);
      }
    }
  }

  console.warn(`Word/phrase "${wordOrPhrase}" not found in timestamps`);
  return 0;
}

/**
 * Get the frame number when a specific word ends
 */
export function getWordEndFrame(
  wordTimestamps: WordTimestamp[],
  wordOrPhrase: string,
  fps: number,
  occurrence: number = 1
): number {
  const searchWords = wordOrPhrase.toLowerCase().split(" ");
  let found = 0;

  for (let i = 0; i <= wordTimestamps.length - searchWords.length; i++) {
    const matches = searchWords.every((searchWord, j) =>
      wordTimestamps[i + j].word.toLowerCase().replace(/[.,!?]$/, "") === searchWord.replace(/[.,!?]$/, "")
    );

    if (matches) {
      found++;
      if (found === occurrence) {
        const lastWordIndex = i + searchWords.length - 1;
        return Math.round(wordTimestamps[lastWordIndex].end_seconds * fps);
      }
    }
  }

  console.warn(`Word/phrase "${wordOrPhrase}" not found in timestamps`);
  return 0;
}

/**
 * Get start time in seconds for a word/phrase
 */
export function getWordStartTime(
  wordTimestamps: WordTimestamp[],
  wordOrPhrase: string,
  occurrence: number = 1
): number {
  const searchWords = wordOrPhrase.toLowerCase().split(" ");
  let found = 0;

  for (let i = 0; i <= wordTimestamps.length - searchWords.length; i++) {
    const matches = searchWords.every((searchWord, j) =>
      wordTimestamps[i + j].word.toLowerCase().replace(/[.,!?]$/, "") === searchWord.replace(/[.,!?]$/, "")
    );

    if (matches) {
      found++;
      if (found === occurrence) {
        return wordTimestamps[i].start_seconds;
      }
    }
  }

  return 0;
}

/**
 * Get end time in seconds for a word/phrase
 */
export function getWordEndTime(
  wordTimestamps: WordTimestamp[],
  wordOrPhrase: string,
  occurrence: number = 1
): number {
  const searchWords = wordOrPhrase.toLowerCase().split(" ");
  let found = 0;

  for (let i = 0; i <= wordTimestamps.length - searchWords.length; i++) {
    const matches = searchWords.every((searchWord, j) =>
      wordTimestamps[i + j].word.toLowerCase().replace(/[.,!?]$/, "") === searchWord.replace(/[.,!?]$/, "")
    );

    if (matches) {
      found++;
      if (found === occurrence) {
        const lastWordIndex = i + searchWords.length - 1;
        return wordTimestamps[lastWordIndex].end_seconds;
      }
    }
  }

  return 0;
}

/**
 * Check if a word/phrase has started being spoken at the current frame
 */
export function hasWordStarted(
  wordTimestamps: WordTimestamp[],
  wordOrPhrase: string,
  currentFrame: number,
  fps: number,
  occurrence: number = 1
): boolean {
  const startFrame = getWordStartFrame(wordTimestamps, wordOrPhrase, fps, occurrence);
  return currentFrame >= startFrame;
}

/**
 * Check if a word/phrase has finished being spoken at the current frame
 */
export function hasWordEnded(
  wordTimestamps: WordTimestamp[],
  wordOrPhrase: string,
  currentFrame: number,
  fps: number,
  occurrence: number = 1
): boolean {
  const endFrame = getWordEndFrame(wordTimestamps, wordOrPhrase, fps, occurrence);
  return currentFrame >= endFrame;
}

/**
 * Create a timing object with all key phrases for a scene
 * Returns frame numbers for easy use in animations
 */
export function createSceneTiming(
  wordTimestamps: WordTimestamp[],
  fps: number,
  phrases: Record<string, string | { phrase: string; occurrence?: number }>
): Record<string, { start: number; end: number }> {
  const timing: Record<string, { start: number; end: number }> = {};

  for (const [key, value] of Object.entries(phrases)) {
    const phrase = typeof value === "string" ? value : value.phrase;
    const occurrence = typeof value === "string" ? 1 : (value.occurrence ?? 1);

    timing[key] = {
      start: getWordStartFrame(wordTimestamps, phrase, fps, occurrence),
      end: getWordEndFrame(wordTimestamps, phrase, fps, occurrence),
    };
  }

  return timing;
}

/**
 * Interpolate a value based on voiceover timing
 * Useful for creating animations that sync to specific words
 */
export function interpolateByWord(
  wordTimestamps: WordTimestamp[],
  currentFrame: number,
  fps: number,
  config: {
    startWord: string;
    endWord: string;
    outputRange: [number, number];
    startOccurrence?: number;
    endOccurrence?: number;
    easing?: (t: number) => number;
    extrapolateLeft?: "clamp" | "extend" | "identity";
    extrapolateRight?: "clamp" | "extend" | "identity";
  }
): number {
  const startFrame = getWordStartFrame(
    wordTimestamps,
    config.startWord,
    fps,
    config.startOccurrence ?? 1
  );
  const endFrame = getWordEndFrame(
    wordTimestamps,
    config.endWord,
    fps,
    config.endOccurrence ?? 1
  );

  return interpolate(
    currentFrame,
    [startFrame, endFrame],
    config.outputRange,
    {
      easing: config.easing,
      extrapolateLeft: config.extrapolateLeft ?? "clamp",
      extrapolateRight: config.extrapolateRight ?? "clamp",
    }
  );
}
