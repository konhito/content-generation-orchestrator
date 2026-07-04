/**
 * TypeScript AST Animation Extractor
 *
 * Parses TSX scene files using Babel parser to extract animation timings
 * with proper expression evaluation. This overcomes the limitations of
 * regex-based analysis by:
 *
 * 1. Building a symbol table of all const declarations
 * 2. Evaluating expressions like Math.round(durationInFrames * 0.10)
 * 3. Resolving variable references in interpolate() calls
 * 4. Extracting component context for semantic sound mapping
 *
 * Usage: npx ts-node extract-animations.ts <scene-path> <duration-frames>
 * Output: JSON with resolved animations and frame timings
 */

import * as parser from '@babel/parser';
import _traverse from '@babel/traverse';
import * as t from '@babel/types';

// Handle both ESM and CJS module formats for @babel/traverse
const traverse = ((_traverse as any).default || _traverse) as typeof _traverse;
import * as fs from 'fs';
import * as path from 'path';

// Types for our output
interface AnimationContext {
  componentHint: string;
  variableName?: string;
  lineNumber: number;
  nearbyText?: string;
  propertyPath?: string;
}

interface Animation {
  type: 'interpolate' | 'spring' | 'counter' | 'opacity' | 'width' | 'height' | 'scale' | 'transform';
  property: string;
  frameStart: number;
  frameEnd: number | null;
  fromValue: number | null;
  toValue: number | null;
  context: AnimationContext;
}

interface ExtractionResult {
  sceneId: string;
  durationFrames: number;
  animations: Animation[];
  phases: Record<string, number>;
  errors: string[];
}

// Symbol table for const declarations
type SymbolTable = Map<string, number | string | null>;

/**
 * Evaluate a numeric expression given a symbol table
 */
function evaluateExpression(
  node: t.Node | null | undefined,
  symbols: SymbolTable,
  durationInFrames: number
): number | null {
  if (!node) return null;

  // Numeric literal
  if (t.isNumericLiteral(node)) {
    return node.value;
  }

  // String literal (return null for non-numeric)
  if (t.isStringLiteral(node)) {
    return null;
  }

  // Identifier - look up in symbol table
  if (t.isIdentifier(node)) {
    const name = node.name;

    // Special built-in: durationInFrames, fps, etc.
    if (name === 'durationInFrames') {
      return durationInFrames;
    }
    if (name === 'fps') {
      return 30; // Standard fps
    }

    const value = symbols.get(name);
    if (typeof value === 'number') {
      return value;
    }
    // Try to evaluate if it's a stored expression string
    return null;
  }

  // Binary expression: a + b, a * b, etc.
  if (t.isBinaryExpression(node)) {
    const left = evaluateExpression(node.left, symbols, durationInFrames);
    const right = evaluateExpression(node.right, symbols, durationInFrames);

    if (left === null || right === null) return null;

    switch (node.operator) {
      case '+': return left + right;
      case '-': return left - right;
      case '*': return left * right;
      case '/': return right !== 0 ? left / right : null;
      case '%': return right !== 0 ? left % right : null;
      default: return null;
    }
  }

  // Unary expression: -x, +x
  if (t.isUnaryExpression(node)) {
    const arg = evaluateExpression(node.argument, symbols, durationInFrames);
    if (arg === null) return null;

    switch (node.operator) {
      case '-': return -arg;
      case '+': return arg;
      default: return null;
    }
  }

  // Call expression: Math.round(...), Math.floor(...), etc.
  if (t.isCallExpression(node)) {
    // Check for Math.* functions
    if (t.isMemberExpression(node.callee) &&
        t.isIdentifier(node.callee.object) &&
        node.callee.object.name === 'Math' &&
        t.isIdentifier(node.callee.property)) {

      const method = node.callee.property.name;
      const arg = node.arguments[0] ? evaluateExpression(node.arguments[0], symbols, durationInFrames) : null;

      if (arg === null) return null;

      switch (method) {
        case 'round': return Math.round(arg);
        case 'floor': return Math.floor(arg);
        case 'ceil': return Math.ceil(arg);
        case 'abs': return Math.abs(arg);
        case 'min': {
          const args = node.arguments.map(a => evaluateExpression(a, symbols, durationInFrames));
          if (args.some(a => a === null)) return null;
          return Math.min(...(args as number[]));
        }
        case 'max': {
          const args = node.arguments.map(a => evaluateExpression(a, symbols, durationInFrames));
          if (args.some(a => a === null)) return null;
          return Math.max(...(args as number[]));
        }
        default: return null;
      }
    }

    // Check for parseInt, parseFloat
    if (t.isIdentifier(node.callee)) {
      const func = node.callee.name;
      const arg = node.arguments[0] ? evaluateExpression(node.arguments[0], symbols, durationInFrames) : null;

      if (arg === null) return null;

      if (func === 'parseInt') return Math.floor(arg);
      if (func === 'parseFloat') return arg;
    }
  }

  // Member expression: obj.prop
  if (t.isMemberExpression(node) &&
      t.isIdentifier(node.object) &&
      t.isIdentifier(node.property)) {
    const objName = node.object.name;
    const propName = node.property.name;

    // Handle COLORS.something, etc. - return null as they're not numeric
    return null;
  }

  // Conditional expression: cond ? a : b
  if (t.isConditionalExpression(node)) {
    // For animations, we often want the "true" branch for positive frame values
    const consequent = evaluateExpression(node.consequent, symbols, durationInFrames);
    const alternate = evaluateExpression(node.alternate, symbols, durationInFrames);

    // Return the larger value (usually the active animation)
    if (consequent !== null && alternate !== null) {
      return Math.max(consequent, alternate);
    }
    return consequent ?? alternate;
  }

  // Parenthesized expression
  if (t.isParenthesizedExpression(node)) {
    return evaluateExpression(node.expression, symbols, durationInFrames);
  }

  return null;
}

/**
 * Extract array elements as numbers
 */
function extractArrayValues(
  node: t.Node | null | undefined,
  symbols: SymbolTable,
  durationInFrames: number
): (number | null)[] {
  if (!node || !t.isArrayExpression(node)) return [];

  return node.elements.map(el => {
    if (!el || t.isSpreadElement(el)) return null;
    return evaluateExpression(el, symbols, durationInFrames);
  });
}

/**
 * Extract context hints from nearby code
 */
function extractContextHints(
  path: any,
  code: string
): { componentHint: string; nearbyText?: string; propertyPath?: string } {
  const hints: { componentHint: string; nearbyText?: string; propertyPath?: string } = {
    componentHint: 'unknown'
  };

  // Look for variable name being assigned
  if (path.parentPath?.isVariableDeclarator()) {
    const id = path.parentPath.node.id;
    if (t.isIdentifier(id)) {
      hints.componentHint = id.name;
    }
  }

  // Look for property name in object
  if (path.parentPath?.isObjectProperty()) {
    const key = path.parentPath.node.key;
    if (t.isIdentifier(key)) {
      hints.propertyPath = key.name;
    }
  }

  // Look for JSX context
  let current = path;
  while (current) {
    if (current.isJSXElement()) {
      const opening = current.node.openingElement;
      if (t.isJSXIdentifier(opening.name)) {
        hints.componentHint = opening.name.name;
        break;
      }
    }
    if (current.isJSXAttribute()) {
      const name = current.node.name;
      if (t.isJSXIdentifier(name)) {
        hints.propertyPath = name.name;
      }
    }
    current = current.parentPath;
  }

  // Extract nearby text from code for additional context
  const start = path.node.loc?.start;
  if (start) {
    const lines = code.split('\n');
    const lineIndex = start.line - 1;

    // Get surrounding lines
    const contextLines = lines.slice(Math.max(0, lineIndex - 2), lineIndex + 3);
    const contextText = contextLines.join(' ');

    // Look for common keywords
    const keywords = ['title', 'prompt', 'response', 'bar', 'chart', 'counter', 'speed',
                      'reveal', 'badge', 'token', 'text', 'opacity', 'scale', 'glow',
                      'slow', 'fast', 'burst', 'particle', 'sparkle', 'transition'];

    for (const kw of keywords) {
      if (contextText.toLowerCase().includes(kw)) {
        if (hints.componentHint === 'unknown') {
          hints.componentHint = kw;
        }
        hints.nearbyText = kw;
        break;
      }
    }
  }

  return hints;
}

/**
 * Main extraction function
 */
function extractAnimations(scenePath: string, durationFrames: number): ExtractionResult {
  const result: ExtractionResult = {
    sceneId: path.basename(scenePath, '.tsx'),
    durationFrames,
    animations: [],
    phases: {},
    errors: []
  };

  // Read the file
  let code: string;
  try {
    code = fs.readFileSync(scenePath, 'utf-8');
  } catch (err) {
    result.errors.push(`Failed to read file: ${err}`);
    return result;
  }

  // Parse with Babel
  let ast: t.File;
  try {
    ast = parser.parse(code, {
      sourceType: 'module',
      plugins: ['typescript', 'jsx'],
    });
  } catch (err) {
    result.errors.push(`Failed to parse file: ${err}`);
    return result;
  }

  // Build symbol table from const declarations
  const symbols: SymbolTable = new Map();

  // First pass: collect all const declarations
  traverse(ast, {
    VariableDeclarator(path) {
      if (path.parentPath?.isVariableDeclaration() &&
          (path.parentPath.node as t.VariableDeclaration).kind === 'const') {
        const id = path.node.id;
        if (t.isIdentifier(id)) {
          const init = path.node.init;
          const value = evaluateExpression(init, symbols, durationFrames);
          if (value !== null) {
            symbols.set(id.name, value);

            // Track phase timings and timing-related variables
            const name = id.name.toLowerCase();
            if (name.includes('phase') || name.includes('start') || name.includes('end') ||
                name.includes('delay') || name.includes('duration') || name.includes('offset') ||
                name.includes('frame') || name.includes('val') || name.includes('time') ||
                name.includes('multiplier') || name.includes('base')) {
              result.phases[id.name] = value;
            }
          }
        }
      }
    }
  });

  // Second pass: find interpolate() and spring() calls
  traverse(ast, {
    CallExpression(path) {
      const callee = path.node.callee;

      // Handle interpolate() calls
      if (t.isIdentifier(callee) && callee.name === 'interpolate') {
        const args = path.node.arguments;
        if (args.length >= 3) {
          // interpolate(frame, [start, end], [from, to], options?)
          const inputRange = extractArrayValues(args[1], symbols, durationFrames);
          const outputRange = extractArrayValues(args[2], symbols, durationFrames);

          if (inputRange.length >= 2 && outputRange.length >= 2) {
            const frameStart = inputRange[0];
            const frameEnd = inputRange[inputRange.length - 1];
            const fromValue = outputRange[0];
            const toValue = outputRange[outputRange.length - 1];

            if (frameStart !== null) {
              const contextHints = extractContextHints(path, code);

              // Determine animation type from context
              let animType: Animation['type'] = 'interpolate';
              let property = contextHints.propertyPath || 'unknown';

              if (property === 'opacity' || contextHints.componentHint.includes('opacity')) {
                animType = 'opacity';
              } else if (property === 'width' || contextHints.componentHint.includes('width') ||
                         contextHints.componentHint.includes('bar')) {
                animType = 'width';
              } else if (property === 'height') {
                animType = 'height';
              } else if (property === 'scale' || contextHints.componentHint.includes('scale')) {
                animType = 'scale';
              } else if (contextHints.componentHint.includes('speed') ||
                         contextHints.componentHint.includes('counter') ||
                         contextHints.componentHint.includes('Count')) {
                animType = 'counter';
              }

              result.animations.push({
                type: animType,
                property,
                frameStart,
                frameEnd,
                fromValue,
                toValue,
                context: {
                  componentHint: contextHints.componentHint,
                  variableName: contextHints.componentHint,
                  lineNumber: path.node.loc?.start.line || 0,
                  nearbyText: contextHints.nearbyText,
                  propertyPath: contextHints.propertyPath
                }
              });
            }
          }
        }
      }

      // Handle spring() calls
      if (t.isIdentifier(callee) && callee.name === 'spring') {
        const args = path.node.arguments;
        if (args.length >= 1 && t.isObjectExpression(args[0])) {
          const obj = args[0];
          let frameValue: number | null = null;

          // Look for frame property
          for (const prop of obj.properties) {
            if (t.isObjectProperty(prop) &&
                t.isIdentifier(prop.key) &&
                prop.key.name === 'frame') {
              // Handle frame: localFrame - delay patterns
              if (t.isBinaryExpression(prop.value) && prop.value.operator === '-') {
                const right = evaluateExpression(prop.value.right, symbols, durationFrames);
                if (right !== null) {
                  frameValue = right; // The delay/start frame
                }
              } else {
                frameValue = evaluateExpression(prop.value, symbols, durationFrames);
              }
            }
          }

          const contextHints = extractContextHints(path, code);

          result.animations.push({
            type: 'spring',
            property: contextHints.propertyPath || 'spring',
            frameStart: frameValue ?? 0,
            frameEnd: null,
            fromValue: 0,
            toValue: 1,
            context: {
              componentHint: contextHints.componentHint,
              variableName: contextHints.componentHint,
              lineNumber: path.node.loc?.start.line || 0,
              nearbyText: contextHints.nearbyText,
              propertyPath: contextHints.propertyPath
            }
          });
        }
      }

      // Handle Math.round/floor/ceil(interpolate(...)) patterns (counters)
      if (t.isMemberExpression(callee) &&
          t.isIdentifier(callee.object) &&
          callee.object.name === 'Math' &&
          t.isIdentifier(callee.property) &&
          ['round', 'floor', 'ceil'].includes(callee.property.name)) {

        const innerArg = path.node.arguments[0];
        if (t.isCallExpression(innerArg) &&
            t.isIdentifier(innerArg.callee) &&
            innerArg.callee.name === 'interpolate') {

          const args = innerArg.arguments;
          if (args.length >= 3) {
            const inputRange = extractArrayValues(args[1], symbols, durationFrames);
            const outputRange = extractArrayValues(args[2], symbols, durationFrames);

            if (inputRange.length >= 2 && outputRange.length >= 2) {
              const frameStart = inputRange[0];
              const frameEnd = inputRange[inputRange.length - 1];
              const fromValue = outputRange[0];
              const toValue = outputRange[outputRange.length - 1];

              if (frameStart !== null) {
                const contextHints = extractContextHints(path, code);

                result.animations.push({
                  type: 'counter',
                  property: contextHints.componentHint || 'counter',
                  frameStart,
                  frameEnd,
                  fromValue,
                  toValue,
                  context: {
                    componentHint: contextHints.componentHint,
                    variableName: contextHints.componentHint,
                    lineNumber: path.node.loc?.start.line || 0,
                    nearbyText: contextHints.nearbyText,
                    propertyPath: contextHints.propertyPath
                  }
                });
              }
            }
          }
        }
      }
    }
  });

  // Deduplicate animations by (frameStart + componentHint) - keep distinct animations at same frame
  const seen = new Map<string, Animation>();
  for (const anim of result.animations) {
    // Use composite key: frameStart + componentHint to allow multiple animations at same frame
    const key = `${anim.frameStart}:${anim.context.componentHint}`;
    const existing = seen.get(key);

    if (!existing ||
        (anim.type !== 'interpolate' && existing.type === 'interpolate') ||
        (anim.context.componentHint !== 'unknown' && existing.context.componentHint === 'unknown')) {
      seen.set(key, anim);
    }
  }

  result.animations = Array.from(seen.values()).sort((a, b) => a.frameStart - b.frameStart);

  return result;
}

// CLI interface
function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('Usage: npx ts-node extract-animations.ts <scene-path> <duration-frames>');
    process.exit(1);
  }

  const scenePath = args[0];
  const durationFrames = parseInt(args[1], 10);

  if (isNaN(durationFrames) || durationFrames <= 0) {
    console.error('Invalid duration-frames: must be a positive integer');
    process.exit(1);
  }

  if (!fs.existsSync(scenePath)) {
    console.error(`Scene file not found: ${scenePath}`);
    process.exit(1);
  }

  const result = extractAnimations(scenePath, durationFrames);
  console.log(JSON.stringify(result, null, 2));
}

main();
