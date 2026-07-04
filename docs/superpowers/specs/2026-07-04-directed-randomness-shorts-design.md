# Directed Randomness Shorts Design

## Goal

Replace single-mode Shorts visuals with a directed edit system that composes
character, components, memes, captions, camera motion, and transitions together
per beat.

The recurring character remains the channel identity and emotional anchor. The
component and meme layers become supporting visual language: diagrams explain
the idea, memes release tension or make the absurdity memorable, and editing
motion keeps attention without hiding the lesson.

The system must survive many niches and topics, not optimize for one channel
style. It should help viewers understand current topics, laugh enough to stay,
and remember the explanation.

## Design Principles

1. Character is the host, not a scene type.
   - The character can appear full, half-body, picture-in-picture, sticker-size,
     or briefly off-screen, but is treated as a persistent identity layer.
   - Character emotion, pose, head direction, mouth movement, blink, and gesture
     should react to what the beat is saying.

2. Components and memes are props, evidence, or reactions.
   - Components explain structure, cause/effect, comparison, timeline, score,
     probability, flow, or data.
   - Memes express confusion, irony, disbelief, relief, or punchline energy.
   - Neither layer should replace the host by default.

3. Randomness is directed.
   - The planner chooses from strong scene recipes instead of making arbitrary
     layout choices.
   - Choices are seeded by project, variant, beat id, niche, and topic so renders
     are stable.
   - Variety is managed with budgets, not chaos.

4. Education wins over noise.
   - Every beat must have one primary viewer takeaway.
   - Supporting meme/component layers must clarify or increase retention.
   - If the beat is serious, meme intensity drops automatically.

## Data Model

Keep the existing `mode` field temporarily for backward compatibility, but add a
new `visual_recipe` object on each Shorts beat.

```json
{
  "id": "beat_003",
  "intent": "explain_surprise",
  "niche": "tech",
  "attention_strategy": "host_demonstrates_concept",
  "visual_recipe": {
    "recipe_id": "host_foreground_concept_backdrop",
    "layout": "character_foreground_visual_backdrop",
    "character": {
      "presence": "primary",
      "position": "lower_center",
      "scale": 0.82,
      "pose_intent": "explain",
      "emotion": "curious"
    },
    "component": {
      "role": "main_explanation",
      "component_type": "probability_bars",
      "position": "background_stage",
      "emphasis_words": ["predicts", "not truth"]
    },
    "meme": {
      "role": "accent",
      "style": "sticker_pop",
      "timing": "after_key_claim",
      "intensity": 0.35
    },
    "camera": {
      "motion": "slow_push",
      "punch_zoom_on": "not truth"
    },
    "transition": {
      "in": "match_cut",
      "out": "accent_whip"
    }
  }
}
```

## Planner

Add a `SceneRecipePlanner` after beat mode planning. It receives:

- topic
- niche
- beat text
- visual description
- component plan item
- meme candidate
- character track
- beat position
- seriousness/sensitivity score
- novelty history from previous beats

It outputs a `visual_recipe` for each beat.

Planner responsibilities:

- classify beat intent:
  - hook
  - explain
  - contrast
  - proof
  - reveal
  - warning
  - joke
  - recap
  - CTA
- choose an attention strategy:
  - host demonstrates concept
  - host reacts to evidence
  - meme interruption
  - visual metaphor
  - timeline walkthrough
  - before/after comparison
  - escalating stack
  - absurdity reveal
- assign layers:
  - character role
  - component role
  - meme role
  - callout role
  - camera role
- enforce budgets:
  - meme intensity
  - cuts per 10 seconds
  - full-frame meme count
  - component density
  - character absence duration

## Recipe Library

The first implementation should include a small but strong recipe set.

### 1. Host Foreground, Concept Backdrop

Character is front and center. Component runs behind as a readable stage.

Use for: explanation, proof, comparison, cause/effect.

### 2. Host Sidecar, Main Diagram

Character sits left or right and points/reacts while the component owns most of
the frame.

Use for: dense diagrams, timelines, lists, maps, scoreboards.

### 3. Meme Interruption

Character starts explaining, meme pops in for a short interruption, then the
visual returns to the explanation.

Use for: jokes, absurd claims, contradiction, viewer-relief moments.

### 4. Reaction Stack

Component card appears, character reacts, meme sticker lands, then a callout
summarizes the lesson.

Use for: news, politics, finance, tech controversy, sports drama.

### 5. Visual Metaphor Stage

Character interacts with symbolic props rather than a literal chart.

Use for: abstract concepts, philosophy, AI, science, motivation.

### 6. Rapid Evidence Wall

Multiple small evidence cards slide through while the character anchors the
frame and captions highlight the one key point.

Use for: current events, explainers, trend summaries, "what changed" topics.

## Niche Adaptation

The planner should adjust visual tone by niche rather than maintain separate
hardcoded pipelines.

Examples:

- Tech: diagrams, token streams, probability bars, UI metaphors, medium meme
  intensity.
- Finance: charts, red/green movement, risk badges, low-to-medium meme
  intensity.
- Politics/current events: timelines, actor cards, claim/evidence separation,
  low meme intensity unless the beat is explicitly absurd.
- Gaming: HUDs, stats, achievement cards, higher punch zooms, higher meme
  intensity.
- Science: visual metaphors, labels, simplified mechanisms, controlled humor.
- Motivation: character-led, metaphor props, fewer memes, warmer motion.
- Entertainment: reaction stack, meme interruption, stronger pacing.

## Rendering Architecture

Add a new Remotion renderer:

```text
ShortsMixedScene
  ├─ RecipeStage
  ├─ CharacterLayer
  ├─ ComponentLayer
  ├─ MemeLayer
  ├─ CalloutLayer
  ├─ CameraFrame
  └─ BeatTransition
```

`ShortsPlayer` should use `ShortsMixedScene` when `beat.visual_recipe` exists.
The existing mode dispatch remains as fallback for old storyboards.

Layer behavior:

- Character layer resolves the existing character track and supports recipe
  position/scale/crop.
- Component layer reuses existing `ShortsVisualArea` and component configs but
  renders into a bounded stage instead of owning the whole screen.
- Meme layer reuses meme card/copy logic and renders stickers, pop cards, or
  quick cutaways based on recipe timing.
- Camera layer applies beat-level push, shake, snap, or parallax to the grouped
  scene.
- Captions and progress remain global in `ShortsPlayer`.

## Attention Guardrails

The planner must avoid both boring repetition and incoherent overload.

Rules:

- Do not hide captions.
- Do not place important visual text in the bottom caption zone.
- Do not let memes cover the primary component longer than the configured
  interruption duration.
- Do not keep the character absent for more than two consecutive beats unless
  the recipe is an intentional evidence montage.
- Do not use high meme intensity for sensitive topics unless the joke targets
  confusion, not victims or harm.
- Do not use more than one primary takeaway per beat.
- Use stable seeded randomness so rerenders do not change unexpectedly.

## Testing and Verification

Python:

- planner produces a recipe for each beat
- seeded recipe choices are deterministic
- serious-topic guardrails lower meme intensity
- visual recipe serializes into storyboard JSON
- old storyboards without recipes still load

Remotion:

- `ShortsMixedScene` renders with character + component + meme layers
- layer bounds avoid caption area
- fallback renderer still works
- recipes with missing meme/component assets degrade gracefully

Render smoke test:

- generate a mock short
- confirm storyboard includes `visual_recipe`
- render representative frames
- inspect at least one explain beat, one meme accent beat, and one character-led
  beat

## Out of Scope for First Pass

- Fully AI-generated bespoke Remotion scenes for every beat.
- Multiple recurring characters.
- Automatic asset search from the web.
- Legal/licensing cleanup beyond preserving existing provenance.
- Perfect niche-specific style packs for every niche.

The first pass should create the architecture and a strong default recipe
library. More recipes and niche-specific polish can be added incrementally.
