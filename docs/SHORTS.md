# Shorts Generation

Generate vertical shorts (1080x1920) optimized for YouTube Shorts, Instagram Reels, and TikTok.

## Character, component, and meme flow

Short-first generation now plans a mixed scene recipe per narration beat. Each
recipe decides how the recurring SyncToon host character, component
visualization, meme accent, callout, camera motion, and transition share the
same frame. The character remains the main charm; components and memes support
what the character is saying instead of replacing the full screen. Legacy
`mode` values (`character`, `component`, `meme`) remain as fallback for older
storyboards without `visual_recipe`.

Generation writes `plans/scene_recipe_plan.json` and embeds the matching
`visual_recipe` on each beat in `storyboard/shorts_storyboard.json`.
Captions, progress, narration, music, design tokens, and mode transitions stay
at the shared player level so mixed scenes stay coupled between beats.

Import or refresh the character source with:

```powershell
python scripts/import_synctoon_character.py --source D:\synctoon --destination remotion\public\characters\synctoon
```

The short-first command writes `plans/beat_mode_plan.json`,
`plans/character_plan.json`, character tracks, and a validation report inside
the selected variant. Required character assets are installed into the project
public tree automatically before rendering.

When a Gentle-compatible service is available at
`http://localhost:49153/transcriptions?async=false`, its phone durations drive
mouth shapes. If it is unavailable, existing word timestamps provide
conservative mouth movement. Pose, expression, head direction, and
deterministic blinking remain active in either case.

The imported SyncToon checkout contains a GPLv3 `LICENSE` despite claiming MIT
in its README. Imported code and artwork are treated as GPLv3 and include
provenance plus a copied license file.

## Overview

Shorts are condensed versions of your explainer video designed for mobile-first platforms. Two generation modes are available:

**Hook Mode** (default): Deep dive into 1-3 compelling scenes, ending with a cliffhanger
**Summary Mode**: Rapid-fire sweep through ALL scenes, creating intrigue through breadth

**Features:**
- Single-word captions (72px bold, uppercase, glow effect)
- Dark gradient theme optimized for mobile
- Phase-based animations synced with voiceover
- Custom React scene generation for each beat
- Automatic hook selection (hook mode) or full-video sweep (summary mode)

## Quick Start

**Prerequisites:** Run `script` and `narration` commands first for your full video.

```bash
# Generate everything end-to-end, then render the short
python -m src.cli short generate <project> --render

# Generate a summary short (sweeps all scenes)
python -m src.cli short generate <project> --mode summary --variant summary

# Render the short
python -m src.cli render <project> --short
```

Example:

```powershell
.\.venv\Scripts\python.exe -m src.cli render test-1 --short
```

Output: `projects/<project>/short/default/` (or `short/summary/` for summary mode)

## Generation Modes

### Hook Mode (Default)

Selects 1-3 compelling scenes and creates a deep-dive short that ends with a cliffhanger.

```bash
python -m src.cli short generate <project>
# or explicitly:
python -m src.cli short generate <project> --mode hook
```

**Characteristics:**
- Duration: 45 seconds (default)
- Selects most intriguing scenes via LLM analysis
- Deep dive into specific content
- Ends with "How did they solve this?" style hook
- CTA: "Full breakdown in description"

**Best for:** Technical deep-dives, surprising reveals, problem-solution teasers

### Summary Mode

Rapid-fire sweep through ALL scenes, creating intrigue through the breadth of content.

```bash
python -m src.cli short generate <project> --mode summary --variant summary
```

**Characteristics:**
- Duration: 60 seconds (default, max)
- Covers every scene with brief teaser phrases
- Builds momentum through accumulation
- Emphasizes scale ("19 layers!", "billions of parameters")
- CTA: "See the complete journey"

**Best for:** Journey-style videos, multi-layer explanations, "overview" teasers

### Mode Comparison

| Aspect | Hook Mode | Summary Mode |
|--------|-----------|--------------|
| Default duration | 45s | 60s |
| Scenes covered | 1-3 selected | ALL scenes |
| Narrative style | Deep dive | Rapid-fire sweep |
| Intrigue mechanism | Unanswered question | Overwhelming breadth |
| CTA tone | "How did they solve this?" | "See the complete journey" |

## Full Workflow

### Step-by-Step Generation

```bash
# 1. Generate the short-first package (research, script, beats, memes, components, recipes)
python -m src.cli short generate <project>

# 2. Generate vertical scene components
python -m src.cli short scenes <project>

# 3. Generate voiceover (TTS)
python -m src.cli short voiceover <project>

# 4. Create storyboard with beat timing
python -m src.cli short storyboard <project>

# 5. Render the short
python -m src.cli short generate <project> --render
```

### Manual Voiceover Workflow

If you want to use your own voice recording:

```bash
# Export recording script for voice actor
python -m src.cli short voiceover <project> --export-script

# After recording, process with Whisper for word timestamps
python -m src.cli short voiceover <project> --audio recording.mp3

# Continue with storyboard and render
python -m src.cli short storyboard <project>
python -m src.cli render <project> --short
```

## Timing Sync

When you re-record or modify the voiceover, scene animations need to sync with the new timing.

```bash
# 1. Process new voiceover (generates word timestamps)
python -m src.cli short voiceover <project> --audio new_recording.mp3

# 2. Regenerate storyboard (updates beat timing)
python -m src.cli short storyboard <project> --skip-custom-scenes

# 3. Regenerate timing.ts (syncs scene animations to new word timestamps)
python -m src.cli short timing <project>

# 4. Preview - animations are now synced!
cd remotion && npm run dev
```

### How Timing Sync Works

1. **Phase markers** in storyboard link animation phases to spoken words:
   ```json
   "phase_markers": [
     {"id": "gptAppear", "end_word": "GPT,", "description": "GPT logo appears"},
     {"id": "phase1End", "end_word": "insight.", "description": "End of intro"}
   ]
   ```

2. **Timing generator** finds word timestamps and calculates frame numbers:
   ```bash
   python -m src.cli short timing <project>
   # Generates: projects/<project>/short/default/scenes/timing.ts
   ```

3. **Scene components** import timing constants instead of hardcoded values:
   ```typescript
   import { TIMING } from "./timing";
   const gptSpring = spring({ frame: localFrame - TIMING.beat_1.gptAppear, ... });
   ```

This eliminates manual scene file updates when voiceover timing changes.

## CLI Options

### Generate Options

```bash
python -m src.cli short generate <project> [options]
```

| Option | Description |
|--------|-------------|
| `--mode` | Generation mode: `hook` (default) or `summary` |
| `--duration` | Target duration in seconds (default: 45 for hook, 60 for summary, max: 60) |
| `--variant` | Variant name for multiple shorts from same project |
| `--scenes` | Override scene selection (comma-separated scene IDs, hook mode only) |
| `--skip-voiceover` | Skip voiceover generation |
| `--skip-custom-scenes` | Use generic visuals instead of custom components |
| `--force` | Force regenerate even if files exist |
| `--mock` | Use mock LLM for testing |
| `--render` | Render the short after generation |

### Script Options

```bash
python -m src.cli short script <project> [options]
```

| Option | Description |
|--------|-------------|
| `--mode` | Generation mode: `hook` (default) or `summary` |
| `--duration` | Target duration in seconds (default: 45 for hook, 60 for summary, max: 60) |
| `--variant` | Variant name for multiple shorts from same project |
| `--scenes` | Override scene selection (comma-separated scene IDs, hook mode only) |
| `--force` | Force regenerate even if files exist |
| `--mock` | Use mock LLM for testing |
| `--whisper-model` | Whisper model for automatic caption transcription on generated voiceover |

### Voiceover Options

```bash
python -m src.cli short voiceover <project> [options]
```

| Option | Description |
|--------|-------------|
| `--provider` | TTS provider: `elevenlabs`, `edge`, `mock` (default: edge) |
| `--export-script` | Export recording script for manual voiceover |
| `--audio` | Process manually recorded audio with Whisper |
| `--whisper-model` | Whisper model: `tiny`, `base`, `small`, `medium`, `large` (used for automatic and manual transcription) |

### Render Options

```bash
python -m src.cli render <project> --short [options]
```

| Option | Description |
|--------|-------------|
| `-r, --resolution` | Resolution: `4k`, `1440p`, `1080p` (default), `720p`, `480p` |
| `--variant` | Render specific variant |
| `--fast` | Faster encoding (lower quality) |
| `--concurrency N` | Thread count for rendering |

### Resolution Presets (Vertical)

| Preset | Resolution |
|--------|------------|
| 4k | 2160x3840 |
| 1440p | 1440x2560 |
| 1080p | 1080x1920 |
| 720p | 720x1280 |
| 480p | 480x854 |

## Project Structure

```
projects/<project>/short/
└── <variant>/                    # default, teaser, etc.
    ├── short_script.json         # Condensed script
    ├── scenes/                   # Custom React components
    │   ├── index.ts
    │   ├── styles.ts
    │   ├── timing.ts             # Generated timing constants
    │   └── *Scene.tsx
    ├── voiceover/                # Short voiceover audio
    │   ├── manifest.json
    │   └── short.mp3
    ├── storyboard/               # Shorts storyboard
    │   └── shorts_storyboard.json
    └── output/                   # Rendered shorts
        └── short.mp4
```

## Multiple Variants

Create multiple shorts from the same project:

```bash
# Create a hook-style teaser (default mode)
python -m src.cli short generate <project> --variant teaser --duration 30

# Create a summary variant (sweep all scenes)
python -m src.cli short generate <project> --mode summary --variant summary

# Create a deep-dive variant (specific scenes)
python -m src.cli short generate <project> --variant deep-dive --scenes scene1,scene2,scene3

# Render specific variant
python -m src.cli render <project> --short --variant summary
```

### Example: Abstractions Project

```bash
# Hook mode - deep dive into one layer (e.g., TLS encryption)
python -m src.cli short generate abstractions --variant tls-hook

# Summary mode - rapid sweep through all 19 layers
python -m src.cli short generate abstractions --mode summary --variant summary
# Output: "You press a key. 300 milliseconds. 19 layers of technology..."
```
