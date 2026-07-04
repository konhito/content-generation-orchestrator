/**
 * SafeEffectComposer - A wrapper for @react-three/postprocessing EffectComposer
 * that handles WebGL context issues during Remotion headless rendering.
 *
 * The issue: During long Remotion renders, WebGL contexts can become null or invalid.
 * When this happens, EffectComposer.addPass() fails with:
 * "Cannot read properties of null (reading 'alpha')"
 *
 * This wrapper performs multiple checks:
 * 1. Verifies the WebGL renderer (gl) exists
 * 2. Verifies the underlying WebGL context is accessible via gl.getContext()
 * 3. Verifies context attributes are readable (the actual source of the 'alpha' error)
 *
 * If any check fails, it returns null to skip post-processing for that frame.
 */

import React from "react";
import { useThree } from "@react-three/fiber";
import { EffectComposer } from "@react-three/postprocessing";

export interface SafeEffectComposerProps {
  children: React.ReactElement | React.ReactElement[];
}

/**
 * A safe wrapper for EffectComposer that prevents crashes when WebGL context is null.
 * Use this instead of importing EffectComposer directly from @react-three/postprocessing.
 *
 * @example
 * ```tsx
 * import { SafeEffectComposer } from "@remotion-components/three";
 *
 * const PostProcessing = () => (
 *   <SafeEffectComposer>
 *     <Bloom intensity={1.0} />
 *     <Vignette darkness={0.5} />
 *   </SafeEffectComposer>
 * );
 * ```
 */
export const SafeEffectComposer: React.FC<SafeEffectComposerProps> = ({ children }) => {
  const { gl } = useThree();

  // If the WebGL renderer is not available, don't render EffectComposer
  // This prevents "Cannot read properties of null (reading 'alpha')" errors
  if (!gl) {
    return null;
  }

  // Check if the WebGL context is still valid
  // The renderer exists but the underlying context may be lost or null
  try {
    const context = gl.getContext();
    if (!context) {
      return null;
    }
    // Check if context attributes are accessible (this is what fails in the error)
    const attributes = context.getContextAttributes();
    if (!attributes) {
      return null;
    }
  } catch {
    // If any error occurs during context check, skip rendering post-processing
    return null;
  }

  return <EffectComposer>{children}</EffectComposer>;
};

export default SafeEffectComposer;
