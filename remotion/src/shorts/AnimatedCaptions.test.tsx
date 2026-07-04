/**
 * Tests for AnimatedCaptions component.
 *
 * Tests the three-word karaoke-style caption display for YouTube Shorts.
 */

import { describe, it, expect, vi } from "vitest";
import React from "react";

// Mock remotion modules
vi.mock("remotion", () => ({
  interpolate: (
    value: number,
    inputRange: number[],
    outputRange: number[],
    options?: { extrapolateRight?: string }
  ) => {
    const [inMin, inMax] = inputRange;
    const [outMin, outMax] = outputRange;

    let ratio = (value - inMin) / (inMax - inMin);

    if (options?.extrapolateRight === "clamp") {
      ratio = Math.min(Math.max(ratio, 0), 1);
    }

    return outMin + ratio * (outMax - outMin);
  },
  useVideoConfig: () => ({
    fps: 30,
    width: 1080,
    height: 1920,
    durationInFrames: 300,
  }),
}));

// Mock ShortsPlayer exports
vi.mock("./ShortsPlayer", () => ({
  SHORTS_COLORS: {
    text: "#ffffff",
    textDim: "#888888",
    textMuted: "#666666",
    primary: "#00d4ff",
    primaryGlow: "#00d4ff60",
  },
  SHORTS_FONTS: {
    primary: "Inter, sans-serif",
  },
}));

// Import after mocks
import { AnimatedCaptions, SimpleAnimatedCaptions } from "./AnimatedCaptions";

// ============================================================================
// Test Helpers
// ============================================================================

interface WordTimestamp {
  word: string;
  start_seconds: number;
  end_seconds: number;
}

const createWordTimestamps = (words: string[], startTime = 0): WordTimestamp[] => {
  return words.map((word, i) => ({
    word,
    start_seconds: startTime + i * 0.5,
    end_seconds: startTime + i * 0.5 + 0.4,
  }));
};

// Helper to get chunk words from the result
const getChunkWords = (result: React.ReactElement): React.ReactElement[] => {
  const wordContainer = result.props.children; // inner div with word spans
  return React.Children.toArray(wordContainer.props.children) as React.ReactElement[];
};

// ============================================================================
// AnimatedCaptions Tests
// ============================================================================

describe("AnimatedCaptions", () => {
  const defaultProps = {
    text: "This is a test caption with more words",
    wordTimestamps: createWordTimestamps([
      "This", "is", "a", "test", "caption", "with", "more", "words"
    ]),
    currentTime: 0,
    beatStartTime: 0,
    scale: 1,
  };

  describe("Three Word Chunk Display", () => {
    it("should show three words at a time", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.2, // During "This" (first word of first chunk)
      });

      const chunkWords = getChunkWords(result);

      // Should show exactly 3 words in the first chunk
      expect(chunkWords.length).toBe(3);
      expect(chunkWords[0].props.children).toBe("This");
      expect(chunkWords[1].props.children).toBe("is");
      expect(chunkWords[2].props.children).toBe("a");
    });

    it("should highlight the currently spoken word", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.7, // During "is" (second word)
      });

      const chunkWords = getChunkWords(result);

      // "is" should be highlighted (active)
      expect(chunkWords[1].props.style.fontWeight).toBe(700);
      expect(chunkWords[1].props.style.color).toBe("#00d4ff");

      // "This" should be past (white)
      expect(chunkWords[0].props.style.fontWeight).toBe(500);
      expect(chunkWords[0].props.style.color).toBe("#ffffff");

      // "a" should be future (muted)
      expect(chunkWords[2].props.style.fontWeight).toBe(500);
      expect(chunkWords[2].props.style.color).toBe("#666666");
    });

    it("should advance to next chunk when current chunk is complete", () => {
      // First chunk: "This is a" (words 0-2)
      const resultChunk1 = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.2, // During "This"
      });

      // Second chunk: "test caption with" (words 3-5)
      const resultChunk2 = AnimatedCaptions({
        ...defaultProps,
        currentTime: 1.7, // During "test" (word index 3)
      });

      const chunk1Words = getChunkWords(resultChunk1);
      const chunk2Words = getChunkWords(resultChunk2);

      expect(chunk1Words[0].props.children).toBe("This");
      expect(chunk2Words[0].props.children).toBe("test");
    });

    it("should handle beat-local time correctly", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 5.7, // 0.7s into beat that starts at 5s
        beatStartTime: 5.0,
      });

      const chunkWords = getChunkWords(result);

      // Should show first chunk, with "is" highlighted
      expect(chunkWords[0].props.children).toBe("This");
      expect(chunkWords[1].props.children).toBe("is");
      expect(chunkWords[1].props.style.fontWeight).toBe(700); // "is" is active
    });
  });

  describe("Chunk Index Calculation", () => {
    it("should show first chunk before any timestamp", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: -0.1,
      });

      const chunkWords = getChunkWords(result);
      expect(chunkWords[0].props.children).toBe("This");
    });

    it("should show last chunk after all timestamps", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 10.0, // Well past all timestamps
      });

      const chunkWords = getChunkWords(result);

      // Last chunk should contain "more" and "words" (partial chunk)
      expect(chunkWords.length).toBe(2); // Only 2 words in last chunk
      expect(chunkWords[0].props.children).toBe("more");
      expect(chunkWords[1].props.children).toBe("words");
    });

    it("should handle empty word timestamps gracefully", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        wordTimestamps: [],
        currentTime: 1.0,
      });

      // Should not crash and should show some words
      expect(result).toBeDefined();
    });
  });

  describe("Styling", () => {
    it("should apply correct font size for readability", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        scale: 1,
        currentTime: 0.2,
      });

      const chunkWords = getChunkWords(result);

      // Font size should be 36 * scale
      expect(chunkWords[0].props.style.fontSize).toBe(36);
    });

    it("should scale font size with scale prop", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        scale: 0.5,
        currentTime: 0.2,
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords[0].props.style.fontSize).toBe(18); // 36 * 0.5
    });

    it("should apply uppercase text transform", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.2,
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords[0].props.style.textTransform).toBe("uppercase");
    });

    it("should apply bold font weight to active word", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.2, // "This" is active
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords[0].props.style.fontWeight).toBe(700);
    });

    it("should have glow text shadow on active word", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.2,
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords[0].props.style.textShadow).toContain("0 0 20px");
    });

    it("should not have text shadow on inactive words", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.2, // "This" is active
      });

      const chunkWords = getChunkWords(result);

      // "is" and "a" should have no text shadow
      expect(chunkWords[1].props.style.textShadow).toBe("none");
      expect(chunkWords[2].props.style.textShadow).toBe("none");
    });
  });

  describe("Container Styling", () => {
    it("should have proper gap between words", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        scale: 1,
        currentTime: 0.2,
      });

      const wordContainer = result.props.children;

      expect(wordContainer.props.style.gap).toBe("32px");
    });

    it("should scale gap with scale prop", () => {
      const result = AnimatedCaptions({
        ...defaultProps,
        scale: 0.5,
        currentTime: 0.2,
      });

      const wordContainer = result.props.children;

      expect(wordContainer.props.style.gap).toBe("16px"); // 32 * 0.5
    });
  });

  describe("Fade Animation", () => {
    it("should fade in at the start of the beat", () => {
      // At time 0, opacity should be starting to fade in
      const resultAtStart = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0,
      });

      // At time 0.3, should be fully faded in
      const resultFadedIn = AnimatedCaptions({
        ...defaultProps,
        currentTime: 0.3,
      });

      expect(resultAtStart.props.style.opacity).toBeLessThan(
        resultFadedIn.props.style.opacity
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle single word text", () => {
      const result = AnimatedCaptions({
        text: "Hello",
        wordTimestamps: [{ word: "Hello", start_seconds: 0, end_seconds: 0.5 }],
        currentTime: 0.2,
        beatStartTime: 0,
        scale: 1,
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords.length).toBe(1);
      expect(chunkWords[0].props.children).toBe("Hello");
    });

    it("should handle two word text", () => {
      const result = AnimatedCaptions({
        text: "Hello world",
        wordTimestamps: [
          { word: "Hello", start_seconds: 0, end_seconds: 0.5 },
          { word: "world", start_seconds: 0.6, end_seconds: 1.0 },
        ],
        currentTime: 0.2,
        beatStartTime: 0,
        scale: 1,
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords.length).toBe(2);
      expect(chunkWords[0].props.children).toBe("Hello");
      expect(chunkWords[1].props.children).toBe("world");
    });

    it("should handle text with punctuation", () => {
      const result = AnimatedCaptions({
        text: "Hello, world!",
        wordTimestamps: [
          { word: "Hello,", start_seconds: 0, end_seconds: 0.5 },
          { word: "world!", start_seconds: 0.6, end_seconds: 1.0 },
        ],
        currentTime: 0.2,
        beatStartTime: 0,
        scale: 1,
      });

      const chunkWords = getChunkWords(result);

      expect(chunkWords[0].props.children).toBe("Hello,");
    });

    it("should handle mismatched word count between text and timestamps", () => {
      // More words in text than timestamps
      const result = AnimatedCaptions({
        text: "This has more words than timestamps",
        wordTimestamps: [
          { word: "This", start_seconds: 0, end_seconds: 0.5 },
          { word: "has", start_seconds: 0.6, end_seconds: 1.0 },
        ],
        currentTime: 0.2,
        beatStartTime: 0,
        scale: 1,
      });

      // Should not crash
      expect(result).toBeDefined();
    });
  });
});

// ============================================================================
// SimpleAnimatedCaptions Tests
// ============================================================================

describe("SimpleAnimatedCaptions", () => {
  it("should show partial text based on progress", () => {
    const text = "Hello World";

    // At 0% progress
    const result0 = SimpleAnimatedCaptions({
      text,
      progress: 0,
      scale: 1,
    });

    // At 100% progress
    const result100 = SimpleAnimatedCaptions({
      text,
      progress: 1,
      scale: 1,
    });

    expect(result0).toBeDefined();
    expect(result100).toBeDefined();
  });

  it("should scale text size with scale prop", () => {
    const result = SimpleAnimatedCaptions({
      text: "Test",
      progress: 1,
      scale: 0.5,
    });

    const container = result.props.children;
    const textDiv = container.props.children;

    expect(textDiv.props.style.fontSize).toBe(21); // 42 * 0.5
  });

  it("should have dark background", () => {
    const result = SimpleAnimatedCaptions({
      text: "Test",
      progress: 0.5,
      scale: 1,
    });

    const container = result.props.children;

    expect(container.props.style.background).toContain("rgba(0, 0, 0");
  });
});

// ============================================================================
// Three Word Chunk Logic Tests
// ============================================================================

describe("Three Word Chunk Logic", () => {
  it("should group words into chunks of 3", () => {
    const words = ["one", "two", "three", "four", "five", "six"];
    const timestamps = createWordTimestamps(words);

    // First chunk (words 0-2)
    const resultChunk1 = AnimatedCaptions({
      text: words.join(" "),
      wordTimestamps: timestamps,
      currentTime: 0.2, // "one" is active
      beatStartTime: 0,
      scale: 1,
    });

    // Second chunk (words 3-5)
    const resultChunk2 = AnimatedCaptions({
      text: words.join(" "),
      wordTimestamps: timestamps,
      currentTime: 1.7, // "four" is active
      beatStartTime: 0,
      scale: 1,
    });

    const chunk1Words = getChunkWords(resultChunk1);
    const chunk2Words = getChunkWords(resultChunk2);

    expect(chunk1Words.length).toBe(3);
    expect(chunk1Words.map(w => w.props.children)).toEqual(["one", "two", "three"]);

    expect(chunk2Words.length).toBe(3);
    expect(chunk2Words.map(w => w.props.children)).toEqual(["four", "five", "six"]);
  });

  it("should handle partial last chunk", () => {
    const words = ["one", "two", "three", "four", "five"];
    const timestamps = createWordTimestamps(words);

    // Last chunk should have only 2 words
    const result = AnimatedCaptions({
      text: words.join(" "),
      wordTimestamps: timestamps,
      currentTime: 2.2, // "five" is active (word index 4)
      beatStartTime: 0,
      scale: 1,
    });

    const chunkWords = getChunkWords(result);

    expect(chunkWords.length).toBe(2);
    expect(chunkWords.map(w => w.props.children)).toEqual(["four", "five"]);
  });

  it("should highlight correct word within chunk", () => {
    const words = ["alpha", "beta", "gamma", "delta", "epsilon"];
    const timestamps = createWordTimestamps(words);

    // Test highlighting "beta" (index 1) in first chunk
    const result = AnimatedCaptions({
      text: words.join(" "),
      wordTimestamps: timestamps,
      currentTime: 0.7, // "beta" is active
      beatStartTime: 0,
      scale: 1,
    });

    const chunkWords = getChunkWords(result);

    // "alpha" is past
    expect(chunkWords[0].props.style.color).toBe("#ffffff");
    // "beta" is active
    expect(chunkWords[1].props.style.color).toBe("#00d4ff");
    // "gamma" is future
    expect(chunkWords[2].props.style.color).toBe("#666666");
  });
});
