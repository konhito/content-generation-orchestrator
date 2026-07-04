/**
 * Tests for SingleScenePlayer component.
 *
 * Tests the URL parsing logic for both formats:
 * 1. Direct query params: ?sceneType=project/scene&durationInSeconds=30
 * 2. Remotion JSON format: ?props={"sceneType":"project/scene","durationInSeconds":30}
 */

import { describe, it, expect, vi } from "vitest";

// Mock the scene registry (which uses @project-scenes webpack alias)
vi.mock("./index", () => ({
  getSceneByPath: () => null,
}));

// Mock remotion (used by SingleScenePlayer)
vi.mock("remotion", () => ({
  AbsoluteFill: () => null,
  Audio: () => null,
  staticFile: (path: string) => path,
  useVideoConfig: () => ({ fps: 30 }),
}));

// Mock cinematic effects
vi.mock("../components/CinematicEffects", () => ({
  AmbientGlow: () => null,
  Vignette: () => null,
}));

import {
  parseUrlProps,
  calculateSingleSceneDuration,
  type SingleScenePlayerProps,
} from "./SingleScenePlayer";

describe("parseUrlProps - Direct query params", () => {
  it("should parse sceneType from direct query param", () => {
    const result = parseUrlProps("?sceneType=thinking-models/beyond_linear_thinking");
    expect(result.sceneType).toBe("thinking-models/beyond_linear_thinking");
  });

  it("should parse durationInSeconds from direct query param", () => {
    const result = parseUrlProps("?sceneType=test&durationInSeconds=45.5");
    expect(result.durationInSeconds).toBe(45.5);
  });

  it("should parse audioFile from direct query param", () => {
    const result = parseUrlProps("?sceneType=test&durationInSeconds=30&audioFile=scene1.mp3");
    expect(result.audioFile).toBe("scene1.mp3");
  });

  it("should parse backgroundColor from direct query param", () => {
    const result = parseUrlProps("?sceneType=test&durationInSeconds=30&backgroundColor=%23ff0000");
    expect(result.backgroundColor).toBe("#ff0000");
  });

  it("should handle URL-encoded scene type", () => {
    const encoded = encodeURIComponent("thinking-models/beyond_linear_thinking");
    const result = parseUrlProps(`?sceneType=${encoded}&durationInSeconds=27.7`);
    expect(result.sceneType).toBe("thinking-models/beyond_linear_thinking");
    expect(result.durationInSeconds).toBe(27.7);
  });

  it("should return empty object for empty search string", () => {
    const result = parseUrlProps("");
    expect(result).toEqual({});
  });

  it("should return empty object for search string with no relevant params", () => {
    const result = parseUrlProps("?foo=bar&baz=qux");
    expect(result).toEqual({});
  });

  it("should handle integer durationInSeconds", () => {
    const result = parseUrlProps("?sceneType=test&durationInSeconds=30");
    expect(result.durationInSeconds).toBe(30);
  });
});

describe("parseUrlProps - Remotion JSON format", () => {
  it("should parse sceneType from JSON props", () => {
    const props = { sceneType: "thinking-models/beyond_linear_thinking", durationInSeconds: 30 };
    const result = parseUrlProps(`?props=${encodeURIComponent(JSON.stringify(props))}`);
    expect(result.sceneType).toBe("thinking-models/beyond_linear_thinking");
  });

  it("should parse durationInSeconds from JSON props", () => {
    const props = { sceneType: "test", durationInSeconds: 45.5 };
    const result = parseUrlProps(`?props=${encodeURIComponent(JSON.stringify(props))}`);
    expect(result.durationInSeconds).toBe(45.5);
  });

  it("should parse all props from JSON format", () => {
    const props = {
      sceneType: "thinking-models/hook",
      durationInSeconds: 30,
      audioFile: "scene1.mp3",
      backgroundColor: "#ff0000",
      voiceoverBasePath: "custom/path",
    };
    const result = parseUrlProps(`?props=${encodeURIComponent(JSON.stringify(props))}`);

    expect(result.sceneType).toBe("thinking-models/hook");
    expect(result.durationInSeconds).toBe(30);
    expect(result.audioFile).toBe("scene1.mp3");
    expect(result.backgroundColor).toBe("#ff0000");
    expect(result.voiceoverBasePath).toBe("custom/path");
  });

  it("should handle malformed JSON gracefully", () => {
    const result = parseUrlProps("?props={invalid json}");
    // Should return empty object, not throw
    expect(result).toEqual({});
  });

  it("should handle empty JSON props", () => {
    const result = parseUrlProps("?props={}");
    expect(result).toEqual({});
  });

  it("should handle JSON with only some props", () => {
    const props = { sceneType: "test" };
    const result = parseUrlProps(`?props=${encodeURIComponent(JSON.stringify(props))}`);
    expect(result.sceneType).toBe("test");
    expect(result.durationInSeconds).toBeUndefined();
  });
});

describe("parseUrlProps - Priority", () => {
  it("should prefer direct query params over JSON props", () => {
    const jsonProps = { sceneType: "json/scene", durationInSeconds: 10 };
    const searchString =
      `?props=${encodeURIComponent(JSON.stringify(jsonProps))}` +
      "&sceneType=direct/scene&durationInSeconds=20";

    const result = parseUrlProps(searchString);

    // Direct query params should override JSON props
    expect(result.sceneType).toBe("direct/scene");
    expect(result.durationInSeconds).toBe(20);
  });

  it("should use JSON props when direct params are not present", () => {
    const jsonProps = { sceneType: "json/scene", durationInSeconds: 10 };
    const result = parseUrlProps(`?props=${encodeURIComponent(JSON.stringify(jsonProps))}`);

    expect(result.sceneType).toBe("json/scene");
    expect(result.durationInSeconds).toBe(10);
  });

  it("should merge JSON and direct params when partial overlap", () => {
    const jsonProps = { sceneType: "json/scene", audioFile: "from-json.mp3" };
    const searchString =
      `?props=${encodeURIComponent(JSON.stringify(jsonProps))}` +
      "&durationInSeconds=30";

    const result = parseUrlProps(searchString);

    expect(result.sceneType).toBe("json/scene"); // From JSON
    expect(result.audioFile).toBe("from-json.mp3"); // From JSON
    expect(result.durationInSeconds).toBe(30); // From direct param
  });
});

describe("calculateSingleSceneDuration", () => {
  it("should calculate duration in frames correctly", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 30,
    };

    const frames = calculateSingleSceneDuration(props, 30);
    expect(frames).toBe(900); // 30 seconds * 30 fps
  });

  it("should handle fractional seconds", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 27.74,
    };

    const frames = calculateSingleSceneDuration(props, 30);
    expect(frames).toBe(833); // ceil(27.74 * 30) = ceil(832.2) = 833
  });

  it("should use default fps of 30 when not specified", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 10,
    };

    const frames = calculateSingleSceneDuration(props);
    expect(frames).toBe(300); // 10 seconds * 30 fps (default)
  });

  it("should handle custom fps", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 10,
    };

    const frames = calculateSingleSceneDuration(props, 60);
    expect(frames).toBe(600); // 10 seconds * 60 fps
  });

  it("should ceil the result to ensure full coverage", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 10.01,
    };

    const frames = calculateSingleSceneDuration(props, 30);
    expect(frames).toBe(301); // ceil(10.01 * 30) = ceil(300.3) = 301
  });

  it("should handle zero duration", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 0,
    };

    const frames = calculateSingleSceneDuration(props, 30);
    expect(frames).toBe(0);
  });

  it("should handle very small durations", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 0.033, // ~1 frame at 30fps
    };

    const frames = calculateSingleSceneDuration(props, 30);
    expect(frames).toBe(1); // ceil(0.033 * 30) = ceil(0.99) = 1
  });

  it("should handle large durations", () => {
    const props: SingleScenePlayerProps = {
      sceneType: "test/scene",
      durationInSeconds: 3600, // 1 hour
    };

    const frames = calculateSingleSceneDuration(props, 30);
    expect(frames).toBe(108000); // 3600 * 30
  });
});

describe("Edge cases", () => {
  it("should handle special characters in scene type", () => {
    const result = parseUrlProps(`?sceneType=${encodeURIComponent("project/scene_with-special.chars")}`);
    expect(result.sceneType).toBe("project/scene_with-special.chars");
  });

  it("should handle negative duration (invalid but should parse)", () => {
    const result = parseUrlProps("?sceneType=test&durationInSeconds=-10");
    expect(result.durationInSeconds).toBe(-10);
  });

  it("should handle NaN duration", () => {
    const result = parseUrlProps("?sceneType=test&durationInSeconds=notanumber");
    expect(result.durationInSeconds).toBeNaN();
  });

  it("should handle very long scene type paths", () => {
    const longPath = "project/" + "a".repeat(200);
    const result = parseUrlProps(`?sceneType=${encodeURIComponent(longPath)}`);
    expect(result.sceneType).toBe(longPath);
  });

  it("should handle unicode in scene type", () => {
    const result = parseUrlProps(`?sceneType=${encodeURIComponent("project/日本語")}`);
    expect(result.sceneType).toBe("project/日本語");
  });
});
