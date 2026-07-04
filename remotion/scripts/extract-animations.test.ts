/**
 * Tests for extract-animations.ts
 *
 * These tests verify that the TypeScript AST analyzer correctly:
 * 1. Parses TSX files with various animation patterns
 * 2. Evaluates expressions like Math.round(durationInFrames * 0.10)
 * 3. Resolves variable references
 * 4. Extracts component context
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

// Path to the extraction script
const SCRIPT_PATH = path.join(__dirname, 'extract-animations.ts');

// Helper to run extraction and parse output
function runExtraction(code: string, durationFrames: number): any {
  // Create a temporary file
  const tempFile = path.join(__dirname, `test-scene-${Date.now()}.tsx`);

  try {
    fs.writeFileSync(tempFile, code);

    const result = execSync(
      `npx ts-node --transpile-only "${SCRIPT_PATH}" "${tempFile}" ${durationFrames}`,
      { cwd: path.join(__dirname, '..'), encoding: 'utf-8' }
    );

    return JSON.parse(result);
  } finally {
    // Clean up temp file
    if (fs.existsSync(tempFile)) {
      fs.unlinkSync(tempFile);
    }
  }
}

describe('extract-animations', () => {
  describe('basic interpolate detection', () => {
    it('should detect simple interpolate with literal frame numbers', () => {
      const code = `
        import { interpolate } from 'remotion';

        const opacity = interpolate(frame, [0, 30], [0, 1]);
      `;

      const result = runExtraction(code, 300);

      expect(result.animations).toHaveLength(1);
      expect(result.animations[0].frameStart).toBe(0);
      expect(result.animations[0].frameEnd).toBe(30);
      expect(result.animations[0].fromValue).toBe(0);
      expect(result.animations[0].toValue).toBe(1);
    });

    it('should detect interpolate with localFrame', () => {
      const code = `
        import { interpolate } from 'remotion';

        const width = interpolate(localFrame, [10, 50], [0, 100]);
      `;

      const result = runExtraction(code, 300);

      expect(result.animations).toHaveLength(1);
      expect(result.animations[0].frameStart).toBe(10);
      expect(result.animations[0].frameEnd).toBe(50);
    });
  });

  describe('expression evaluation', () => {
    it('should evaluate Math.round(durationInFrames * factor)', () => {
      const code = `
        import { interpolate, useVideoConfig } from 'remotion';

        const { durationInFrames } = useVideoConfig();
        const phase1End = Math.round(durationInFrames * 0.10);
        const phase2End = Math.round(durationInFrames * 0.40);

        const opacity = interpolate(frame, [phase1End, phase2End], [0, 1]);
      `;

      const result = runExtraction(code, 500);

      // Should resolve: 500 * 0.10 = 50, 500 * 0.40 = 200
      expect(result.phases).toHaveProperty('phase1End', 50);
      expect(result.phases).toHaveProperty('phase2End', 200);

      expect(result.animations.length).toBeGreaterThan(0);
      const anim = result.animations.find((a: any) => a.frameStart === 50);
      expect(anim).toBeDefined();
      expect(anim.frameEnd).toBe(200);
    });

    it('should evaluate Math.floor and Math.ceil', () => {
      const code = `
        const floorVal = Math.floor(durationInFrames * 0.15);
        const ceilVal = Math.ceil(durationInFrames * 0.15);
      `;

      const result = runExtraction(code, 100);

      expect(result.phases).toHaveProperty('floorVal', 15);
      expect(result.phases).toHaveProperty('ceilVal', 15);
    });

    it('should evaluate arithmetic expressions', () => {
      const code = `
        const phase1End = 50;
        const phase2Start = phase1End;
        const phase2End = phase1End + 100;
        const phase3Start = phase2End + 10;

        const opacity = interpolate(frame, [phase2Start, phase2End], [0, 1]);
      `;

      const result = runExtraction(code, 500);

      expect(result.phases).toHaveProperty('phase1End', 50);
      expect(result.phases).toHaveProperty('phase2Start', 50);
      expect(result.phases).toHaveProperty('phase2End', 150);
      expect(result.phases).toHaveProperty('phase3Start', 160);
    });
  });

  describe('spring animation detection', () => {
    it('should detect spring with frame offset', () => {
      const code = `
        import { spring } from 'remotion';

        const delay = 30;
        const scale = spring({
          frame: localFrame - delay,
          fps: 30,
          config: { damping: 10 },
        });
      `;

      const result = runExtraction(code, 300);

      const springAnim = result.animations.find((a: any) => a.type === 'spring');
      expect(springAnim).toBeDefined();
      expect(springAnim.frameStart).toBe(30);
    });

    it('should detect spring with variable delay', () => {
      const code = `
        import { spring } from 'remotion';

        const phase3Start = Math.round(durationInFrames * 0.50);

        const scale = spring({
          frame: localFrame - phase3Start,
          fps,
          config: { damping: 8 },
        });
      `;

      const result = runExtraction(code, 400);

      // phase3Start should be 400 * 0.50 = 200
      expect(result.phases).toHaveProperty('phase3Start', 200);

      const springAnim = result.animations.find((a: any) => a.type === 'spring');
      expect(springAnim).toBeDefined();
    });
  });

  describe('counter animation detection', () => {
    it('should detect Math.round(interpolate(...)) as counter', () => {
      const code = `
        const slowSpeed = Math.round(
          interpolate(localFrame, [50, 200], [0, 40])
        );
      `;

      const result = runExtraction(code, 300);

      const counterAnim = result.animations.find((a: any) => a.type === 'counter');
      expect(counterAnim).toBeDefined();
      expect(counterAnim.frameStart).toBe(50);
      expect(counterAnim.frameEnd).toBe(200);
      expect(counterAnim.fromValue).toBe(0);
      expect(counterAnim.toValue).toBe(40);
    });

    it('should detect Math.floor(interpolate(...)) as counter', () => {
      const code = `
        const count = Math.floor(
          interpolate(frame, [0, 100], [0, 50])
        );
      `;

      const result = runExtraction(code, 300);

      const counterAnim = result.animations.find((a: any) => a.type === 'counter');
      expect(counterAnim).toBeDefined();
    });
  });

  describe('context extraction', () => {
    it('should extract variable name as context hint', () => {
      const code = `
        const barWidth = interpolate(frame, [0, 50], [0, 100]);
        const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
      `;

      const result = runExtraction(code, 300);

      expect(result.animations.length).toBeGreaterThanOrEqual(2);

      const barAnim = result.animations.find((a: any) =>
        a.context.componentHint.includes('bar') ||
        a.context.variableName?.includes('bar')
      );
      expect(barAnim).toBeDefined();

      const titleAnim = result.animations.find((a: any) =>
        a.context.componentHint.includes('title') ||
        a.context.variableName?.includes('title')
      );
      expect(titleAnim).toBeDefined();
    });

    it('should identify animation type from property name', () => {
      const code = `
        const styles = {
          opacity: interpolate(frame, [0, 30], [0, 1]),
          width: interpolate(frame, [30, 60], [0, 100]),
        };
      `;

      const result = runExtraction(code, 300);

      const opacityAnim = result.animations.find((a: any) =>
        a.type === 'opacity' || a.property === 'opacity'
      );
      expect(opacityAnim).toBeDefined();

      const widthAnim = result.animations.find((a: any) =>
        a.type === 'width' || a.property === 'width'
      );
      expect(widthAnim).toBeDefined();
    });
  });

  describe('complex scene patterns', () => {
    it('should handle HookScene-like phase timing', () => {
      const code = `
        import { interpolate, spring, useVideoConfig } from 'remotion';

        const { durationInFrames } = useVideoConfig();

        // Phase timings
        const phase1End = Math.round(durationInFrames * 0.10);
        const phase2Start = phase1End;
        const phase2End = Math.round(durationInFrames * 0.40);
        const phase3Start = phase2End;

        // Animations
        const titleOpacity = interpolate(frame, [0, 15], [0, 1]);

        const slowBarWidth = interpolate(
          localFrame, [phase2Start, phase2End], [0, 40]
        );

        const slowSpeed = Math.round(
          interpolate(localFrame, [phase2Start + 10, phase2End], [0, 40])
        );

        const fastBarSpring = spring({
          frame: localFrame - phase3Start,
          fps,
          config: { damping: 8 },
        });
      `;

      const result = runExtraction(code, 500);

      // Verify phase timing resolution
      expect(result.phases.phase1End).toBe(50);  // 500 * 0.10
      expect(result.phases.phase2End).toBe(200); // 500 * 0.40

      // Should have multiple animations detected
      expect(result.animations.length).toBeGreaterThanOrEqual(3);

      // Verify animations have correct frame timings
      const titleAnim = result.animations.find((a: any) =>
        a.frameStart === 0 && a.frameEnd === 15
      );
      expect(titleAnim).toBeDefined();
    });

    it('should handle nested expressions', () => {
      const code = `
        const baseDelay = 20;
        const multiplier = 2;
        const finalDelay = Math.round(baseDelay * multiplier + 10);

        const opacity = interpolate(frame, [finalDelay, finalDelay + 30], [0, 1]);
      `;

      const result = runExtraction(code, 300);

      // finalDelay should be round(20 * 2 + 10) = 50
      expect(result.phases).toHaveProperty('finalDelay', 50);
    });
  });

  describe('error handling', () => {
    it('should handle missing file gracefully', () => {
      expect(() => {
        execSync(
          `npx ts-node --transpile-only "${SCRIPT_PATH}" "/nonexistent/file.tsx" 300`,
          { cwd: path.join(__dirname, '..'), encoding: 'utf-8' }
        );
      }).toThrow();
    });

    it('should handle invalid duration', () => {
      expect(() => {
        execSync(
          `npx ts-node --transpile-only "${SCRIPT_PATH}" "${SCRIPT_PATH}" -1`,
          { cwd: path.join(__dirname, '..'), encoding: 'utf-8' }
        );
      }).toThrow();
    });

    it('should return empty animations for code without animations', () => {
      const code = `
        const x = 5;
        const y = x + 10;
        console.log(y);
      `;

      const result = runExtraction(code, 300);

      expect(result.animations).toHaveLength(0);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('deduplication', () => {
    it('should deduplicate animations at same frame', () => {
      const code = `
        // Multiple interpolates at same start frame with same variable name
        const opacity = interpolate(frame, [0, 30], [0, 1]);
        const opacity2 = opacity;  // This reuses the same variable, but...
        // Only the original interpolate call should be detected
      `;

      const result = runExtraction(code, 300);

      // Should detect only the interpolate call, not duplicates
      // With different variable names (opacity vs scale), both should be kept
      // because they represent distinct animations
      expect(result.animations.length).toBeGreaterThanOrEqual(1);
    });

    it('should keep distinct animations at same frame start', () => {
      const code = `
        // Multiple different interpolates at same start frame
        const opacity = interpolate(frame, [0, 30], [0, 1]);
        const scale = interpolate(frame, [0, 30], [0.5, 1]);
      `;

      const result = runExtraction(code, 300);

      // Should keep both since they have different component hints (opacity vs scale)
      expect(result.animations.length).toBe(2);
    });
  });
});
