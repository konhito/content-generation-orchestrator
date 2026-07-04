# Video Explainer Channel Market-Test Strategy

## Decision

For the first market test, `video_explainer` remains the production foundation.

We will use it to launch and validate one focused channel before expanding the system into a broader multi-format content engine. The immediate goal is not to merge every useful repository or build a universal video generator. The goal is to prove that one repeatable content format can attract and retain an audience.

If the channel demonstrates demand, we can scale production volume, add scene plugins, introduce more characters and visual formats, and eventually launch additional channels.

## Why `video_explainer` Is the Foundation

`video_explainer` transforms source material into narrated, programmatically rendered videos:

```text
Source material
-> research and understanding
-> script and narration
-> timed beats
-> storyboard
-> custom React/Remotion scenes
-> voiceover, music, and sound effects
-> final video
```

It provides the most creative freedom of the projects reviewed:

- React and Remotion rendering.
- Three.js, React Three Fiber, Drei, and GLB support.
- Custom generated TSX scenes.
- Programmatic diagrams, typography, transitions, and effects.
- Long-form and vertical Shorts compositions.
- Word-level voiceover synchronization.
- Sound effects, music, captions, review, and refinement.
- A production style already demonstrated by [The Commit Log](https://www.youtube.com/@thecommitlog).

The repository is less constrained than template-only systems. It can eventually support a common scene vocabulary such as:

```text
remotion | threejs | glb-character | manim | 2d-character | meme | footage
```

## Product Thesis

The channel should not depend on generic B-roll or a newly generated full-frame image for every sentence. Each visual should communicate the current idea.

The intended format combines:

- Clean programmatic explanations.
- A consistent visual identity.
- Reusable scene components.
- Optional recurring characters.
- Topic-specific diagrams and demonstrations.
- Selective memes or real footage when they improve the explanation.

A useful scene-selection rule is:

```text
Does real footage provide evidence or necessary context?
|-- Yes: use reviewed footage.
`-- No: use a purpose-built programmatic scene.
```

## Market-Test Scope

The first version should remain deliberately narrow.

### In scope

- One channel.
- One audience and recognizable editorial promise.
- One visual system and color language.
- A small reusable scene library.
- A repeatable research-to-render workflow.
- A limited publishing cadence that preserves quality.
- Shorts or small experiments to test hooks and topics.
- Measurement of topic demand, retention, and production effort.

### Out of scope for the first test

- Building a universal plugin framework.
- Supporting every niche.
- Fully automatic publishing at high volume.
- Integrating every external repository immediately.
- Generating a unique character or asset for every beat.
- Complex realistic character lip-sync.
- Launching multiple channels before one format is validated.

## Content and Visual Direction

The strongest differentiated direction discussed is visual explanation: concepts are shown through transformations, relationships, comparisons, timelines, mechanisms, and demonstrations rather than illustrated with loosely related media.

Possible content domains include:

- AI and computer science.
- Psychology and habits.
- Everyday science.
- Personal-finance behaviour.
- Business and workplace systems.
- Fitness and body mechanics.
- History through maps and timelines.

No niche is guaranteed to perform. The market test should select one clear promise, publish enough work to measure it, and use audience evidence rather than assumptions to decide whether to continue or pivot.

## Character Strategy

A recurring character is possible in either 2D or 3D.

### 2D character

Use layered, reusable assets for body poses, heads, eyes, mouths, and expressions. This is fast, predictable, and suitable for character-led Shorts.

### 3D character

Use one rigged GLB model with reusable skeletal animations, expressions, cameras, lighting, and materials. A useful starter animation library would include:

- Idle.
- Talking.
- Pointing left and right.
- Thinking.
- Demonstrating.
- Celebrating.
- Entering and exiting.

A static GLB is not sufficient. It needs a rig and animation clips. Basic audio-driven mouth movement can precede phoneme-level viseme lip-sync.

Character scenes should support the explanation rather than replace it. A strong pattern is:

```text
Character introduces the question
-> programmatic visual explains the mechanism
-> character simplifies or reacts
-> diagram, example, or selective meme reinforces the point
-> concise conclusion
```

## Asset Strategy

The system should avoid generating a complete new image for every beat because that increases cost and creates visual inconsistency.

Target asset mix:

```text
80% reusable components and assets
15% programmatic text, shapes, charts, and diagrams
5% newly generated or sourced assets
```

The reusable library can include characters, poses, muscle diagrams, maps, charts, icons, arrows, equipment, backgrounds, labels, warnings, transitions, and layout templates. Most videos should require only a few genuinely new assets.

## Repositories and References Reviewed

### Primary foundation

- [`video_explainer`](https://github.com/search?q=video_explainer&type=repositories) — current local foundation. Python content pipeline plus React/Remotion, Three.js, narration, audio, refinement, Shorts, and custom scene generation. The local README does not identify a canonical remote URL, so the link is a GitHub search rather than an asserted upstream repository.
- [The Commit Log](https://www.youtube.com/@thecommitlog) — reference channel built with the `video_explainer` approach.

### Explanatory animation

- [3Blue1Brown Manim](https://github.com/3b1b/manim) — precise programmatic animation engine created for explanatory mathematics.
- [3Blue1Brown video scene source](https://github.com/3b1b/videos) — source code for many Manim-generated 3Blue1Brown scenes. Its scene-content license differs from Manim's engine license and must be respected.
- [ChalkTalk](https://github.com/ahkamboh/chalktalk) — agent skill that generates and verifies Manim-based STEM explainer scenes. Useful as an optional mathematical scene renderer, not as the central pipeline.

### Structured Remotion explanation

- [Docent](https://github.com/benelser/docent) — deterministic Remotion framework with a film JSON specification, 29 canonical scene types, plugin protocols, TTS adapters, depth checks, render checks, and golden-frame regression.

Docent is the strongest architectural reference. We should borrow its reusable scene grammar, validation, caching, and visual QA concepts while retaining the broader creative freedom and Three.js capabilities of `video_explainer`.

### Character animation

- [SyncToon](https://github.com/Automate-Animation/synctoon) — Python pipeline for layered 2D characters, Gemini-selected animation cues, Gentle audio alignment, phoneme-driven mouth shapes, and frame compositing.

SyncToon is useful as a reference for character-state data and lip-sync. Its renderer does not need to become the central renderer because the same layered approach can be implemented in Remotion. Its repository presents inconsistent license signals between the README and GitHub metadata, so its actual license must be reviewed before copying code.

### Topical Shorts and internet media

- [YouTube Shorts Pipeline / Verticals](https://github.com/rushindrasinha/youtube-shorts-pipeline) — research, topic discovery, scripting, voiceover, captions, footage harvesting, asset inspection, semantic matching, memes, FFmpeg assembly, and publishing.

This pipeline is strong at topical relevance but relies heavily on internet media. Later, selected capabilities can feed `video_explainer` rather than replacing its renderer:

- Research and source discovery.
- Timed semantic beats.
- Reviewed footage.
- Asset relevance scoring.
- Imgflip meme generation.
- Distribution and publishing.

### Meme generation

- [Imgflip API](https://imgflip.com/api) — meme-template discovery and caption generation. Memes should be used as timed reactions or punchlines, not as arbitrary filler.

### Workflow automation reference

- [n8n](https://github.com/n8n-io/n8n) — workflow automation platform used in the reviewed Blotato export.
- [Blotato](https://blotato.com/) — hosted visual-template and social-publishing service. It uses predefined style templates, prompt expansion, selectable image models, optional image-to-video animation, voiceover, captions, and publishing.

Blotato demonstrates rapid template-driven production, but it does not provide the same deterministic, programmatic scene control as `video_explainer`.

## Lessons to Borrow Without Integrating Everything

### From Docent

- A finite vocabulary of reusable scene types.
- Clear JSON contracts for scene inputs.
- Scene selection based on the cognitive purpose of a beat.
- Plugin-like scene registration.
- Cached TTS and rendering.
- Low-resolution render checks.
- Golden-frame visual regression.
- Automated checks that narrated scenes actually evolve visually.

### From ChalkTalk and Manim

- Programmatic mathematical scenes.
- Graphs, equations, vectors, geometry, and transformations.
- Draft-render and frame-inspection workflow.

### From SyncToon

- Character state expressed as structured data.
- Emotion, pose, gaze, head direction, and camera cues.
- Phoneme or viseme mouth-shape timelines.
- Reusable layered character assets.

### From the Shorts pipeline

- Current-topic research.
- Beat-specific search queries.
- Technical and semantic asset review.
- Real-footage support where evidence matters.
- Imgflip reactions.
- Publishing automation.

### From Blotato

- Style presets as reusable prompt and layout contracts.
- Fast aspect-ratio variants.
- Simple configuration for captions, voices, and transitions.
- Separation between content input and visual-template selection.

## Proposed First-Channel Workflow

```text
1. Select a topic that fits the channel promise.
2. Research and verify the core claims.
3. Write a strong narrative with a clear question and takeaway.
4. Split narration into semantic beats.
5. Assign every beat a cognitive purpose.
6. Select a reusable scene type or justify a custom scene.
7. Generate narration and word timing.
8. Render a low-resolution draft.
9. Inspect representative frames and pacing.
10. Refine weak or decorative scenes.
11. Render the final video.
12. Publish and record performance and production metrics.
```

## Market-Test Metrics

The test should evaluate both audience response and production economics.

### Audience signals

- Click-through rate by topic and packaging.
- Retention during the opening hook.
- Average percentage viewed.
- Retention drops at scene boundaries.
- Rewatches and shares.
- Comments that indicate understanding or confusion.
- Subscriber conversion.
- Performance of evergreen topics over time.

### Production signals

- Research time.
- Script and fact-check time.
- Number of custom scenes required.
- Render and refinement time.
- Cost per completed video.
- Reusable-scene ratio.
- Number and severity of manual corrections.
- Whether the workflow becomes faster without lowering quality.

The test succeeds when the channel shows repeatable audience demand and the production process becomes increasingly reusable. A single viral upload is not enough evidence.

## Scaling Path

Scaling should occur in stages.

### Stage 1: Prove one format

- One channel.
- One niche or editorial promise.
- One visual identity.
- Manual quality control.
- Small reusable scene library.

### Stage 2: Systematize production

- Formal scene registry and schemas.
- Automated scene recommendations.
- Reusable character and 3D animation libraries.
- Cached generation and rendering.
- Automated render checks and visual regression.
- Selective Manim, meme, and footage scenes.

### Stage 3: Increase throughput

- Parallel research, scripting, rendering, and review.
- Topic experiments through Shorts.
- Automated analytics feedback into topic selection.
- Multiple visual presets built on the same engine.

### Stage 4: Expand channels

- Launch a new channel only when the first format is operationally repeatable.
- Reuse infrastructure while giving each channel a distinct audience, voice, character, and visual identity.
- Treat each new channel as a separate product test rather than a clone.

The intended exponential growth comes from reusable systems and validated formats—not from publishing large quantities of unvalidated content.

## Current Commitment

For now:

1. Keep `video_explainer` as the core project.
2. Choose and validate one channel concept.
3. Build only the scene components required for that channel.
4. Publish, measure, and refine.
5. Borrow proven architectural ideas selectively.
6. Delay broad integrations until real audience evidence justifies them.

