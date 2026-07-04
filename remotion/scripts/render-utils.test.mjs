/**
 * Tests for render utility functions.
 */

import { describe, it, expect } from "vitest";

import {
  parseArgs,
  calculateDuration,
  buildProps,
  validateConfig,
  deriveStoryboardPath,
  deriveProjectDir,
  deriveShortsSceneDir,
  getFinalResolution,
  shouldSkipSceneValidation,
  getFrameRangeSuffix,
  RESOLUTION_PRESETS,
  SHORTS_RESOLUTION_PRESETS,
} from "./render-utils.mjs";

describe("parseArgs", () => {
  it("should return default values for empty args", () => {
    const config = parseArgs([]);
    expect(config.propsPath).toBeNull();
    expect(config.storyboardPath).toBeNull();
    expect(config.projectDir).toBeNull();
    expect(config.outputPath).toBe("./output.mp4");
    expect(config.compositionId).toBe("ScenePlayer");
    expect(config.voiceoverBasePath).toBe("voiceover");
    expect(config.width).toBeNull();
    expect(config.height).toBeNull();
    expect(config.concurrency).toBeNull();
    expect(config.fast).toBe(false);
    expect(config.frameRange).toBeNull();
  });

  it("should parse --project flag", () => {
    const config = parseArgs(["--project", "/path/to/project"]);
    expect(config.projectDir).toBe("/path/to/project");
  });

  it("should parse --storyboard flag", () => {
    const config = parseArgs(["--storyboard", "/path/to/storyboard.json"]);
    expect(config.storyboardPath).toBe("/path/to/storyboard.json");
  });

  it("should parse --props flag", () => {
    const config = parseArgs(["--props", "/path/to/props.json"]);
    expect(config.propsPath).toBe("/path/to/props.json");
  });

  it("should parse --output flag", () => {
    const config = parseArgs(["--output", "/output/video.mp4"]);
    expect(config.outputPath).toBe("/output/video.mp4");
  });

  it("should parse --composition flag", () => {
    const config = parseArgs(["--composition", "StoryboardPlayer"]);
    expect(config.compositionId).toBe("StoryboardPlayer");
  });

  it("should parse --voiceover-path flag", () => {
    const config = parseArgs(["--voiceover-path", "audio/voiceovers"]);
    expect(config.voiceoverBasePath).toBe("audio/voiceovers");
  });

  it("should parse --width flag", () => {
    const config = parseArgs(["--width", "3840"]);
    expect(config.width).toBe(3840);
  });

  it("should parse --height flag", () => {
    const config = parseArgs(["--height", "2160"]);
    expect(config.height).toBe(2160);
  });

  it("should parse multiple flags together", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--output", "/output/test.mp4",
      "--width", "1920",
      "--height", "1080",
      "--composition", "MyComp",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.outputPath).toBe("/output/test.mp4");
    expect(config.width).toBe(1920);
    expect(config.height).toBe(1080);
    expect(config.compositionId).toBe("MyComp");
  });

  it("should ignore flags without values", () => {
    const config = parseArgs(["--width"]);
    expect(config.width).toBeNull();
  });

  it("should parse 4K resolution correctly", () => {
    const config = parseArgs(["--width", "3840", "--height", "2160"]);
    expect(config.width).toBe(3840);
    expect(config.height).toBe(2160);
  });

  it("should parse --fast flag", () => {
    const config = parseArgs(["--fast"]);
    expect(config.fast).toBe(true);
  });

  it("should parse --concurrency flag", () => {
    const config = parseArgs(["--concurrency", "8"]);
    expect(config.concurrency).toBe(8);
  });

  it("should parse --concurrency with different values", () => {
    const config = parseArgs(["--concurrency", "16"]);
    expect(config.concurrency).toBe(16);
  });

  it("should handle --fast with other flags", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--fast",
      "--output", "/output/test.mp4",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.fast).toBe(true);
    expect(config.outputPath).toBe("/output/test.mp4");
  });

  it("should handle --concurrency with other flags", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--concurrency", "12",
      "--fast",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.concurrency).toBe(12);
    expect(config.fast).toBe(true);
  });

  it("should ignore --concurrency without value", () => {
    const config = parseArgs(["--concurrency"]);
    expect(config.concurrency).toBeNull();
  });

  it("should parse --frames with start-end range", () => {
    const config = parseArgs(["--frames", "0-3500"]);
    expect(config.frameRange).toEqual([0, 3500]);
  });

  it("should parse --frames with open-ended range (to end)", () => {
    const config = parseArgs(["--frames", "7001-"]);
    expect(config.frameRange).toEqual([7001, null]);
  });

  it("should parse --frames with middle range", () => {
    const config = parseArgs(["--frames", "3501-7000"]);
    expect(config.frameRange).toEqual([3501, 7000]);
  });

  it("should ignore --frames without value", () => {
    const config = parseArgs(["--frames"]);
    expect(config.frameRange).toBeNull();
  });

  it("should handle --frames with other flags", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--frames", "0-2500",
      "--concurrency", "1",
      "--gl", "angle",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.frameRange).toEqual([0, 2500]);
    expect(config.concurrency).toBe(1);
    expect(config.gl).toBe("angle");
  });

  it("should parse --gl flag", () => {
    const config = parseArgs(["--gl", "angle"]);
    expect(config.gl).toBe("angle");
  });

  it("should parse --gl with swiftshader", () => {
    const config = parseArgs(["--gl", "swiftshader"]);
    expect(config.gl).toBe("swiftshader");
  });
});

describe("calculateDuration", () => {
  it("should calculate duration for ScenePlayer with storyboard", () => {
    const props = {
      storyboard: {
        scenes: [
          { audio_duration_seconds: 10 },
          { audio_duration_seconds: 15 },
          { audio_duration_seconds: 5 },
        ],
        audio: { buffer_between_scenes_seconds: 1.0 },
      },
    };
    // 10 + 1 + 15 + 1 + 5 + 1 = 33
    expect(calculateDuration("ScenePlayer", props)).toBe(33);
  });

  it("should use default buffer of 1.0 when not specified", () => {
    const props = {
      storyboard: {
        scenes: [
          { audio_duration_seconds: 10 },
          { audio_duration_seconds: 20 },
        ],
      },
    };
    // 10 + 1 + 20 + 1 = 32
    expect(calculateDuration("ScenePlayer", props)).toBe(32);
  });

  it("should calculate duration for StoryboardPlayer", () => {
    const props = {
      storyboard: {
        duration_seconds: 120,
        beats: [],
      },
    };
    expect(calculateDuration("StoryboardPlayer", props)).toBe(120);
  });

  it("should calculate duration for legacy scenes format", () => {
    const props = {
      scenes: [
        { durationInSeconds: 30 },
        { durationInSeconds: 45 },
        { durationInSeconds: 15 },
      ],
    };
    expect(calculateDuration("LegacyPlayer", props)).toBe(90);
  });

  it("should use duration_seconds fallback", () => {
    const props = {
      duration_seconds: 180,
    };
    expect(calculateDuration("UnknownComp", props)).toBe(180);
  });

  it("should default to 60 seconds", () => {
    const props = {};
    expect(calculateDuration("UnknownComp", props)).toBe(60);
  });

  it("should handle empty scenes array", () => {
    const props = {
      storyboard: {
        scenes: [],
      },
    };
    expect(calculateDuration("ScenePlayer", props)).toBe(0);
  });

  it("should handle custom buffer value", () => {
    const props = {
      storyboard: {
        scenes: [
          { audio_duration_seconds: 10 },
          { audio_duration_seconds: 10 },
        ],
        audio: { buffer_between_scenes_seconds: 2.0 },
      },
    };
    // 10 + 2 + 10 + 2 = 24
    expect(calculateDuration("ScenePlayer", props)).toBe(24);
  });

  it("should calculate duration for ShortsPlayer", () => {
    const props = {
      storyboard: {
        total_duration_seconds: 45,
        beats: [],
      },
    };
    expect(calculateDuration("ShortsPlayer", props)).toBe(45);
  });

  it("should default to 60 for ShortsPlayer without total_duration_seconds", () => {
    const props = {
      storyboard: {
        beats: [],
      },
    };
    expect(calculateDuration("ShortsPlayer", props)).toBe(60);
  });

  it("should handle ShortsPlayer with various durations", () => {
    const durations = [30, 45, 60, 90];
    for (const duration of durations) {
      const props = {
        storyboard: {
          total_duration_seconds: duration,
          beats: [{ id: "beat_1" }],
        },
      };
      expect(calculateDuration("ShortsPlayer", props)).toBe(duration);
    }
  });
});

describe("buildProps", () => {
  it("should create props object with storyboard and voiceover path", () => {
    const storyboard = { title: "Test", scenes: [] };
    const voiceoverBasePath = "voiceover";

    const props = buildProps(storyboard, voiceoverBasePath);

    expect(props.storyboard).toBe(storyboard);
    expect(props.voiceoverBasePath).toBe(voiceoverBasePath);
  });

  it("should preserve storyboard data", () => {
    const storyboard = {
      title: "My Video",
      scenes: [{ scene_id: "scene1" }, { scene_id: "scene2" }],
    };

    const props = buildProps(storyboard, "audio");

    expect(props.storyboard.title).toBe("My Video");
    expect(props.storyboard.scenes).toHaveLength(2);
  });
});

describe("validateConfig", () => {
  it("should be valid with storyboardPath", () => {
    const config = { storyboardPath: "/path/to/storyboard.json" };
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should be valid with propsPath", () => {
    const config = { propsPath: "/path/to/props.json" };
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should be invalid without storyboardPath or propsPath", () => {
    const config = {};
    const result = validateConfig(config);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("required");
  });

  it("should be valid with both paths", () => {
    const config = {
      storyboardPath: "/path/to/storyboard.json",
      propsPath: "/path/to/props.json",
    };
    expect(validateConfig(config).valid).toBe(true);
  });
});

describe("deriveStoryboardPath", () => {
  it("should append storyboard/storyboard.json to project dir", () => {
    const result = deriveStoryboardPath("/projects/my-video");
    expect(result).toBe("/projects/my-video/storyboard/storyboard.json");
  });

  it("should handle trailing slash", () => {
    const result = deriveStoryboardPath("/projects/my-video/");
    expect(result).toBe("/projects/my-video//storyboard/storyboard.json");
  });
});

describe("deriveProjectDir", () => {
  it("should derive project dir from storyboard path", () => {
    const result = deriveProjectDir("/projects/my-video/storyboard/storyboard.json");
    expect(result).toBe("/projects/my-video");
  });

  it("should handle relative paths", () => {
    const result = deriveProjectDir("projects/test/storyboard/storyboard.json");
    expect(result).toBe("projects/test");
  });

  it("should derive project dir from a shorts storyboard path", () => {
    const result = deriveProjectDir("/projects/my-video/short/default/storyboard/shorts_storyboard.json");
    expect(result).toBe("/projects/my-video");
  });

  it("should derive project dir from a Windows shorts storyboard path", () => {
    const result = deriveProjectDir("D:\\projects\\my-video\\short\\default\\storyboard\\shorts_storyboard.json");
    expect(result).toBe("D:/projects/my-video");
  });
});

describe("deriveShortsSceneDir", () => {
  it("should derive shorts scenes dir from shorts storyboard path", () => {
    const result = deriveShortsSceneDir("/projects/my-video/short/default/storyboard/shorts_storyboard.json");
    expect(result).toBe("/projects/my-video/short/default/scenes");
  });

  it("should handle different variant names", () => {
    const result = deriveShortsSceneDir("/projects/test/short/teaser/storyboard/shorts_storyboard.json");
    expect(result).toBe("/projects/test/short/teaser/scenes");
  });

  it("should handle relative paths", () => {
    const result = deriveShortsSceneDir("projects/test/short/default/storyboard/shorts_storyboard.json");
    expect(result).toBe("projects/test/short/default/scenes");
  });

  it("should work with deeply nested project paths", () => {
    const result = deriveShortsSceneDir("/home/user/work/projects/my-video/short/v2/storyboard/shorts_storyboard.json");
    expect(result).toBe("/home/user/work/projects/my-video/short/v2/scenes");
  });
});

describe("getFinalResolution", () => {
  const mockComposition = { width: 1920, height: 1080 };

  it("should use composition dimensions when no custom dimensions", () => {
    const result = getFinalResolution(null, null, mockComposition);
    expect(result.width).toBe(1920);
    expect(result.height).toBe(1080);
    expect(result.isCustom).toBe(false);
  });

  it("should use custom width when provided", () => {
    const result = getFinalResolution(3840, null, mockComposition);
    expect(result.width).toBe(3840);
    expect(result.height).toBe(1080);
    expect(result.isCustom).toBe(true);
  });

  it("should use custom height when provided", () => {
    const result = getFinalResolution(null, 2160, mockComposition);
    expect(result.width).toBe(1920);
    expect(result.height).toBe(2160);
    expect(result.isCustom).toBe(true);
  });

  it("should use both custom dimensions when provided", () => {
    const result = getFinalResolution(3840, 2160, mockComposition);
    expect(result.width).toBe(3840);
    expect(result.height).toBe(2160);
    expect(result.isCustom).toBe(true);
  });

  it("should mark as custom when only width is changed", () => {
    const result = getFinalResolution(1280, null, mockComposition);
    expect(result.isCustom).toBe(true);
  });
});

describe("RESOLUTION_PRESETS", () => {
  it("should have 4k preset", () => {
    expect(RESOLUTION_PRESETS["4k"]).toEqual({ width: 3840, height: 2160 });
  });

  it("should have 1440p preset", () => {
    expect(RESOLUTION_PRESETS["1440p"]).toEqual({ width: 2560, height: 1440 });
  });

  it("should have 1080p preset", () => {
    expect(RESOLUTION_PRESETS["1080p"]).toEqual({ width: 1920, height: 1080 });
  });

  it("should have 720p preset", () => {
    expect(RESOLUTION_PRESETS["720p"]).toEqual({ width: 1280, height: 720 });
  });

  it("should have 480p preset", () => {
    expect(RESOLUTION_PRESETS["480p"]).toEqual({ width: 854, height: 480 });
  });

  it("should have 5 presets total", () => {
    expect(Object.keys(RESOLUTION_PRESETS)).toHaveLength(5);
  });

  it("should all maintain approximately 16:9 aspect ratio", () => {
    for (const [name, { width, height }] of Object.entries(RESOLUTION_PRESETS)) {
      const ratio = width / height;
      expect(Math.abs(ratio - 16/9)).toBeLessThan(0.01);
    }
  });
});

describe("SHORTS_RESOLUTION_PRESETS", () => {
  it("should have 4k preset (vertical)", () => {
    expect(SHORTS_RESOLUTION_PRESETS["4k"]).toEqual({ width: 2160, height: 3840 });
  });

  it("should have 1440p preset (vertical)", () => {
    expect(SHORTS_RESOLUTION_PRESETS["1440p"]).toEqual({ width: 1440, height: 2560 });
  });

  it("should have 1080p preset (vertical)", () => {
    expect(SHORTS_RESOLUTION_PRESETS["1080p"]).toEqual({ width: 1080, height: 1920 });
  });

  it("should have 720p preset (vertical)", () => {
    expect(SHORTS_RESOLUTION_PRESETS["720p"]).toEqual({ width: 720, height: 1280 });
  });

  it("should have 480p preset (vertical)", () => {
    expect(SHORTS_RESOLUTION_PRESETS["480p"]).toEqual({ width: 480, height: 854 });
  });

  it("should have 5 presets total", () => {
    expect(Object.keys(SHORTS_RESOLUTION_PRESETS)).toHaveLength(5);
  });

  it("should all maintain approximately 9:16 aspect ratio", () => {
    for (const [name, { width, height }] of Object.entries(SHORTS_RESOLUTION_PRESETS)) {
      const ratio = width / height;
      expect(Math.abs(ratio - 9/16)).toBeLessThan(0.01);
    }
  });

  it("should have same resolution names as landscape presets", () => {
    const landscapeKeys = Object.keys(RESOLUTION_PRESETS);
    const shortsKeys = Object.keys(SHORTS_RESOLUTION_PRESETS);
    expect(shortsKeys).toEqual(landscapeKeys);
  });

  it("should have inverted dimensions compared to landscape", () => {
    for (const key of Object.keys(RESOLUTION_PRESETS)) {
      const landscape = RESOLUTION_PRESETS[key];
      const shorts = SHORTS_RESOLUTION_PRESETS[key];
      expect(shorts.width).toBe(landscape.height);
      expect(shorts.height).toBe(landscape.width);
    }
  });
});

describe("getFrameRangeSuffix", () => {
  it("should return empty string for null/undefined input", () => {
    expect(getFrameRangeSuffix(null)).toBe("");
    expect(getFrameRangeSuffix(undefined)).toBe("");
    expect(getFrameRangeSuffix("")).toBe("");
  });

  it("should generate suffix for start-end range", () => {
    expect(getFrameRangeSuffix("0-2500")).toBe("frames-0-2500");
  });

  it("should generate suffix for middle range", () => {
    expect(getFrameRangeSuffix("2501-5000")).toBe("frames-2501-5000");
  });

  it("should generate suffix for open-ended range with 'end'", () => {
    expect(getFrameRangeSuffix("7501-")).toBe("frames-7501-end");
  });

  it("should handle single frame", () => {
    expect(getFrameRangeSuffix("100-100")).toBe("frames-100-100");
  });

  it("should handle large frame numbers", () => {
    expect(getFrameRangeSuffix("10000-20000")).toBe("frames-10000-20000");
  });
});

describe("shouldSkipSceneValidation", () => {
  it("should return true for ShortsPlayer", () => {
    expect(shouldSkipSceneValidation("ShortsPlayer")).toBe(true);
  });

  it("should return false for ScenePlayer", () => {
    expect(shouldSkipSceneValidation("ScenePlayer")).toBe(false);
  });

  it("should return false for StoryboardPlayer", () => {
    expect(shouldSkipSceneValidation("StoryboardPlayer")).toBe(false);
  });

  it("should return false for unknown compositions", () => {
    expect(shouldSkipSceneValidation("UnknownPlayer")).toBe(false);
    expect(shouldSkipSceneValidation("CustomPlayer")).toBe(false);
  });

  it("should be case-sensitive", () => {
    expect(shouldSkipSceneValidation("shortsplayer")).toBe(false);
    expect(shouldSkipSceneValidation("SHORTSPLAYER")).toBe(false);
  });
});

describe("Integration: Full argument parsing scenarios", () => {
  it("should handle typical 4K render command", () => {
    const config = parseArgs([
      "--project", "../projects/llm-inference",
      "--output", "./output-4k.mp4",
      "--width", "3840",
      "--height", "2160",
    ]);

    expect(config.projectDir).toBe("../projects/llm-inference");
    expect(config.outputPath).toBe("./output-4k.mp4");
    expect(config.width).toBe(3840);
    expect(config.height).toBe(2160);
  });

  it("should handle storyboard-only render", () => {
    const config = parseArgs([
      "--storyboard", "./storyboard.json",
      "--output", "./video.mp4",
    ]);

    expect(config.storyboardPath).toBe("./storyboard.json");
    expect(config.projectDir).toBeNull();
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should handle legacy props render", () => {
    const config = parseArgs([
      "--composition", "StoryboardPlayer",
      "--props", "./props.json",
      "--output", "./legacy.mp4",
    ]);

    expect(config.compositionId).toBe("StoryboardPlayer");
    expect(config.propsPath).toBe("./props.json");
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should handle fast render with concurrency", () => {
    const config = parseArgs([
      "--project", "../projects/test",
      "--output", "./fast-render.mp4",
      "--fast",
      "--concurrency", "8",
    ]);

    expect(config.projectDir).toBe("../projects/test");
    expect(config.outputPath).toBe("./fast-render.mp4");
    expect(config.fast).toBe(true);
    expect(config.concurrency).toBe(8);
  });

  it("should handle ShortsPlayer composition render", () => {
    const config = parseArgs([
      "--project", "../projects/llm-inference",
      "--composition", "ShortsPlayer",
      "--output", "./short.mp4",
      "--width", "1080",
      "--height", "1920",
    ]);

    expect(config.projectDir).toBe("../projects/llm-inference");
    expect(config.compositionId).toBe("ShortsPlayer");
    expect(config.width).toBe(1080);
    expect(config.height).toBe(1920);
  });

  it("should handle shorts 4K render", () => {
    const config = parseArgs([
      "--project", "../projects/test",
      "--composition", "ShortsPlayer",
      "--output", "./short-4k.mp4",
      "--width", "2160",
      "--height", "3840",
      "--storyboard", "../projects/test/short/default/storyboard/shorts_storyboard.json",
    ]);

    expect(config.compositionId).toBe("ShortsPlayer");
    expect(config.width).toBe(2160);
    expect(config.height).toBe(3840);
    expect(config.storyboardPath).toBe("../projects/test/short/default/storyboard/shorts_storyboard.json");
  });

  it("should handle shorts voiceover path", () => {
    const config = parseArgs([
      "--project", "../projects/test",
      "--composition", "ShortsPlayer",
      "--voiceover-path", "short/default/voiceover",
    ]);

    expect(config.compositionId).toBe("ShortsPlayer");
    expect(config.voiceoverBasePath).toBe("short/default/voiceover");
  });

  it("should handle chunked 4K render - chunk 1", () => {
    const config = parseArgs([
      "--project", "../projects/continual-learning",
      "--output", "./part1.mp4",
      "--width", "3840",
      "--height", "2160",
      "--frames", "0-2500",
      "--concurrency", "1",
      "--gl", "angle",
    ]);

    expect(config.projectDir).toBe("../projects/continual-learning");
    expect(config.outputPath).toBe("./part1.mp4");
    expect(config.width).toBe(3840);
    expect(config.height).toBe(2160);
    expect(config.frameRange).toEqual([0, 2500]);
    expect(config.concurrency).toBe(1);
    expect(config.gl).toBe("angle");
  });

  it("should handle chunked 4K render - final chunk (open-ended)", () => {
    const config = parseArgs([
      "--project", "../projects/continual-learning",
      "--output", "./part4.mp4",
      "--width", "3840",
      "--height", "2160",
      "--frames", "7501-",
      "--concurrency", "1",
      "--gl", "angle",
    ]);

    expect(config.projectDir).toBe("../projects/continual-learning");
    expect(config.outputPath).toBe("./part4.mp4");
    expect(config.frameRange).toEqual([7501, null]);
  });
});
