# SyncToon Character Integration for Shorts

**Date:** 2026-07-04

## Decision

Integrate SyncToon's layered 2D character system into the existing short-first
pipeline. Character scenes render natively inside Remotion rather than as
pre-rendered SyncToon video clips.

The integration is limited to vertical Shorts. Long-form storyboard and render
paths remain unchanged.

The first release supports one recurring character and three full-frame beat
types:

- `character`: layered character explanation with lip-sync and performance cues.
- `component`: an existing or generated programmatic explainer component.
- `meme`: a structured meme card used as a reaction or punchline.

Each beat owns the complete vertical visual area. The character does not remain
as a persistent corner overlay during component or meme beats.

The three modes must feel like one authored visual language. Character,
component, and meme beats share typography, palette, spacing, motion curves,
caption treatment, texture, and audio transition rules. Mode changes provide
rhythmic contrast without looking like clips from separate products.

## Licensing and Provenance

The checked-out `D:\synctoon` repository has conflicting license signals: its
README says MIT while its `LICENSE` file contains GPLv3. This design treats the
copied implementation and artwork as GPLv3.

The user has accepted GPLv3 compatibility for the integrated project. Copied
source and assets must retain copyright and license notices. A provenance file
must identify the source repository, source revision, copied paths, adaptation
date, and material modifications. The project must include the GPLv3 license
text before distributing the combined work.

## Scope

### Included

- One recurring layered 2D character.
- SyncToon body, head, eye, blink, mouth, and related character artwork.
- Character asset metadata and deterministic asset resolution.
- Body pose, eye expression, head direction, gaze, blink, and emotion cues.
- Phoneme-driven mouth shapes synchronized to the generated narration.
- Semantic selection among character, component, and meme beats.
- Native Remotion composition at the existing Shorts resolution and frame rate.
- Graceful fallback when alignment, cues, or individual assets are unavailable.
- Python contract tests, TypeScript renderer tests, pipeline integration tests,
  and one representative draft render.

### Excluded

- Multi-character conversations.
- Character rendering in long-form videos.
- A persistent character overlay during component or meme beats.
- SyncToon's PNG-per-frame renderer and final FFmpeg video compiler as runtime
  stages.
- SyncToon's separate story CLI as a user-facing entry point.
- A universal character-plugin framework.
- New character artwork or an asset marketplace.

## Architecture

The integration preserves the useful SyncToon concepts while using the current
project's pipeline and renderer:

```text
Short narration and semantic beats
        |
        v
Beat-mode planner
  character | component | meme
        |
        +-------------------- component plan / meme plan
        |
        v
Character cue planner
  pose, emotion, head, gaze, blink intent
        |
        v
Narration voiceover + forced alignment
  words, phonemes, timestamps
        |
        v
CharacterTrack JSON
        |
        v
Remotion ShortsPlayer
  CharacterScene | existing component | meme card
        |
        v
Single vertical render
```

Python owns semantic planning, alignment normalization, validation, and artifact
generation. TypeScript owns deterministic frame-time selection and layered
visual composition.

## Beat-Mode Planning

`ShortsBeat` gains an explicit mode rather than inferring behavior from a loose
visual description:

```text
ShortsBeat.mode = character | component | meme
```

The planner assigns the mode from each beat's cognitive purpose:

- Use `character` to introduce a question, explain a simple point directly,
  react, bridge concepts, or conclude.
- Use `component` for mechanisms, comparisons, timelines, transformations,
  diagrams, code, numbers, and demonstrations.
- Use `meme` only when a reaction or punchline reinforces the explanation.

Planner guardrails:

- No more than two consecutive character beats.
- A meme cannot be the only explanation of a factual claim.
- Memes cannot be consecutive.
- The opening beat may be character-led only when the character delivers the
  hook; otherwise it remains a purpose-built component.
- If a selected mode cannot be produced, fall back to `component`.

The component and meme paths continue using the existing component plan and
meme provider. The integration adds a peer character plan instead of replacing
those systems.

## Unified Art Direction

A Shorts style contract is the single source of truth for all three beat modes.
It defines:

- Color roles for background, surface, primary accent, secondary accent,
  warning, success, text, and muted text.
- Primary, display, and monospace typography.
- Caption-safe bounds, content margins, corner radii, shadows, and stroke widths.
- Standard entrance, emphasis, transition, and exit timing curves.
- Background texture and depth treatment.
- Sound-effect categories and transition timing.

SyncToon artwork is adapted to this system through its surrounding stage,
lighting treatment, scale, and accent elements; the imported PNG artwork is not
recolored destructively. Component scenes use the same framing and accents.
Meme cards use the same type scale, borders, and surfaces instead of switching
to an unrelated template aesthetic.

Captions, progress treatment, music, and narration remain continuous above
beat-mode dispatch. They do not unmount or visibly reset when the visual mode
changes.

### Transition grammar

Transitions communicate the relationship between adjacent beats:

- `character -> component`: the character gestures toward an accent element;
  that element expands or match-cuts into the component's focal visual.
- `component -> character`: the component's focal element contracts into the
  character stage as the character reacts or summarizes.
- `character/component -> meme`: a short emphasis cut, punch-in, or card snap
  creates comedic punctuation without interrupting narration.
- `meme -> character/component`: a fast return using the same focal color or
  shape restores explanatory continuity.

Transitions must be short enough to preserve Shorts pacing and cannot obscure
spoken content. Hard cuts remain valid when they improve a punchline, but the
palette, captions, and audio bed still preserve continuity.

## Character Data Contract

Each character beat references a `CharacterTrack` artifact. Times are seconds
relative to the start of that beat so Remotion can render the same track at any
supported frame rate.

```json
{
  "version": 1,
  "character_id": "character_1",
  "duration_seconds": 4.2,
  "base_pose": "thinking",
  "base_emotion": "content",
  "events": [
    {"start": 0.0, "end": 1.4, "pose": "thinking", "emotion": "content", "head": "M"},
    {"start": 1.4, "end": 4.2, "pose": "you", "emotion": "worried", "head": "R"}
  ],
  "mouth_cues": [
    {"start": 0.10, "end": 0.18, "shape": "m_b_close"},
    {"start": 0.18, "end": 0.31, "shape": "a_e"}
  ],
  "blink_cues": [
    {"start": 1.82, "end": 1.96}
  ]
}
```

Required normalized values:

- Head direction: `L`, `M`, or `R`.
- Mouth shape: a value present in the imported SyncToon mouth mapping.
- Pose and emotion: manifest keys, never direct arbitrary file paths.
- Events: sorted, non-overlapping, clamped to the beat duration.
- Mouth and blink cues: sorted and clamped to the beat duration.

The storyboard stores the relative path to the track. It does not duplicate the
entire timeline inside every beat.

## Character Planning and Alignment

The existing short-first narration remains the source of spoken text. A
character cue planner converts only `character` beats into structured pose,
emotion, head-direction, and gaze intervals. The planner returns manifest keys
and cannot emit JSX or filesystem paths.

After voiceover generation, the alignment stage produces phoneme intervals for
character beats. SyncToon's Gentle integration and phoneme-to-mouth mapping are
adapted behind the current pipeline interface. Alignment results are normalized
into `CharacterTrack.mouth_cues`.

Fallback behavior is deterministic:

1. If forced alignment succeeds, use phoneme mouth shapes.
2. If phonemes are incomplete but word timing exists, generate conservative
   mouth changes within word boundaries using the imported mouth map.
3. If no timing is available, use the closed mouth shape and retain pose,
   expression, head movement, and blinking.

The alignment service is invoked only when the storyboard contains character
beats. Component-only and meme-only Shorts do not acquire the dependency.

## Asset Import and Manifest

SyncToon character artwork is copied into the Remotion public asset tree under
a dedicated provenance-bearing directory. A generated manifest maps semantic
keys to public asset paths and placement metadata.

```text
remotion/public/characters/synctoon/character_1/
  body/
  head/
  eyes/
  mouth/
  backgrounds/
  character-manifest.json
  PROVENANCE.md
```

The import process must be repeatable and validate:

- Referenced files exist.
- Asset keys are unique.
- Placement values are numeric.
- All required neutral fallback assets exist.
- Mouth-map entries resolve to actual images.
- Paths are relative and remain inside the character asset root.

Backgrounds may be imported for completeness and attribution, but normal Shorts
character scenes use the established Shorts visual system unless a beat
explicitly selects an imported background key.

## Remotion Rendering

`ShortsPlayer` dispatches full-frame beats by mode. Character beats render a
new `ShortsCharacterScene` that:

1. Loads the character manifest and referenced track.
2. Converts the current frame to beat-relative time.
3. Selects the active performance event, mouth cue, and blink cue.
4. Resolves semantic keys through the manifest.
5. Renders layers in deterministic order: background, body, head, eyes, mouth.
6. Preserves the existing caption-safe area and Shorts progress treatment.

All images use Remotion's asset APIs. Motion is driven by `useCurrentFrame()`,
`interpolate()`, and `spring()`; CSS transitions and wall-clock animation are
not used. Entry and exit movement is subtle so lip-sync and expression changes
remain readable.

Character beats may use programmatic labels, arrows, or emphasis shapes as
supporting elements, but they do not embed a full component scene. When a visual
mechanism is necessary, the planner selects a component beat instead.

The player receives neighboring beat modes so it can choose the appropriate
transition grammar. Transitions are part of the shared player layer rather than
implemented independently inside character, component, and meme renderers.

## Failure Handling

- Unknown pose, emotion, head, or mouth keys resolve to manifest-defined neutral
  assets and emit a validation warning.
- Missing non-neutral artwork uses the neutral equivalent.
- Missing neutral artwork fails asset validation before render.
- Invalid or overlapping track intervals fail artifact validation and prevent a
  misleading render.
- Alignment timeout uses the word-timing fallback.
- Complete character-track generation failure changes the beat to `component`
  and records the reason in the generated plan.
- Component and meme behavior remains available when the character subsystem is
  disabled or unavailable.

## Configuration and CLI Behavior

Character integration is enabled only for the short-first flow. Configuration
defines:

- Whether character beats are enabled.
- The single active character ID.
- Character asset root and manifest path.
- Forced-alignment service URL and timeout.
- Whether word-timing fallback is allowed.

The existing Shorts generation command remains the entry point. It gains
character-related options only where a configuration override is necessary;
there is no second SyncToon-specific production command.

Generated artifacts remain inside the selected short variant directory and
include the beat-mode plan, character plan, normalized tracks, and validation
report.

## Testing and Acceptance

### Python tests

- Beat planner selects character, component, and meme modes under the stated
  semantic rules.
- Guardrails prevent consecutive memes and more than two character beats.
- Character cue parsing accepts manifest keys and rejects paths or unknown keys.
- Alignment normalization creates sorted, clamped mouth cues.
- Missing alignment uses word-timing fallback.
- Character failure converts the affected beat to component mode.
- The long-form pipeline does not invoke character planning or alignment.

### TypeScript tests

- Track lookup returns the expected pose, emotion, head, mouth, and blink state
  at boundary frames.
- Unknown optional keys resolve to neutral assets.
- Full-frame mode dispatch selects the correct renderer for all three beat
  types.
- Layer order and caption-safe layout remain stable.

### Integration verification

- Generate a representative Short containing at least one character beat, one
  component beat, and one meme beat.
- Validate all generated JSON artifacts.
- Render representative frames from the start, middle, and end of each beat.
- Render a low-resolution vertical draft and verify narration synchronization,
  mouth changes, blinking, pose changes, transitions, captions, and meme timing.
- Confirm captions, progress, narration, and music remain continuous across
  every mode boundary.
- Confirm character, component, and meme frames use the same palette,
  typography, content bounds, surface treatment, and motion language.
- Inspect every mode transition for a meaningful visual handoff or an
  intentionally timed hard cut; reject generic crossfades used without purpose.
- Confirm no mode boundary produces a blank frame, layout jump, caption reset,
  audio gap, or abrupt change in perceived visual quality.
- Run the existing Shorts and long-form regression tests.

The feature is complete when the short-first command produces one coherent
vertical video that alternates full-frame character explanations, programmatic
components, and selective memes without routing through SyncToon's standalone
frame-to-video pipeline.

## Implementation Boundary

The integration copies and adapts only the SyncToon implementation and assets
needed for character planning, alignment, asset mapping, and performance. Its
legacy frame compositor and video compiler may be retained as attributed source
reference if required by the chosen import layout, but they are not connected
to production execution. Remotion remains the sole final renderer.
