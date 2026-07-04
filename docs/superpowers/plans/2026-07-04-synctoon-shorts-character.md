# SyncToon Shorts Character Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one recurring SyncToon character to the existing short-first flow as a native Remotion beat mode alongside programmatic components and memes.

**Architecture:** Python selects beat modes and creates validated character performance tracks from narration timing. A repeatable importer copies GPLv3 SyncToon assets into a provenance-bearing Remotion public directory and generates a semantic manifest. Remotion dispatches full-frame character, component, and meme beats through one shared style and transition layer.

**Tech Stack:** Python 3.12, Pydantic, pytest, React 18, TypeScript, Remotion 4, Vitest, SyncToon PNG assets and phoneme map.

---

## File Structure

- `src/short/models.py`: beat-mode and character-track contracts.
- `src/short/beat_mode.py`: semantic mode selection and sequence guardrails.
- `src/short/character.py`: cue generation, timing fallback, validation, and track serialization.
- `scripts/import_synctoon_character.py`: repeatable asset/metadata import with provenance.
- `src/short/first.py`: short-first artifact generation integration.
- `src/short/generator.py`: storyboard serialization/loading and timed track integration.
- `src/config.py`, `config.yaml`, `.env.example`: character and aligner settings.
- `remotion/src/shorts/shortsStyle.ts`: shared visual contract.
- `remotion/src/shorts/characterTypes.ts`: manifest and track types/lookups.
- `remotion/src/shorts/ShortsCharacterScene.tsx`: deterministic layered renderer.
- `remotion/src/shorts/ShortsTransition.tsx`: mode-aware visual handoff.
- `remotion/src/shorts/ShortsPlayer.tsx`: mode dispatch and continuous overlays/audio.
- `tests/test_short_character.py`, `tests/test_short_first.py`: Python unit/integration coverage.
- `remotion/src/shorts/ShortsCharacterScene.test.tsx`, `remotion/src/shorts/ShortsPlayer.test.tsx`: renderer and dispatch coverage.
- `remotion/public/characters/synctoon/character_1/`: imported artwork, manifest, and provenance.

### Task 1: Add beat and character contracts

**Files:**
- Modify: `src/short/models.py`
- Create: `tests/test_short_character.py`

- [ ] **Step 1: Write failing model tests**

```python
def test_character_beat_contract():
    beat = ShortsBeat(
        id="beat_001", start_seconds=0, end_seconds=3,
        mode=ShortBeatMode.CHARACTER, character_track="character/beat_001.json",
        visual=ShortsVisual(type=VisualType.TEXT_HIGHLIGHT, primary_text="Why?"),
        caption_text="Why does this happen?",
    )
    assert beat.mode == ShortBeatMode.CHARACTER
    assert beat.character_track.endswith(".json")

def test_character_track_rejects_overlapping_events():
    with pytest.raises(ValueError):
        CharacterTrack(duration_seconds=2, events=[
            CharacterEvent(start=0, end=1.5),
            CharacterEvent(start=1, end=2),
        ])
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `pytest tests/test_short_character.py -q`

Expected: import failure for `ShortBeatMode` and `CharacterTrack`.

- [ ] **Step 3: Add enums and validated models**

Add `ShortBeatMode`, `CharacterEvent`, `MouthCue`, `BlinkCue`, and
`CharacterTrack`; add `mode` and `character_track` defaults to `ShortsBeat`.
Validation sorts/clamps cue arrays and rejects overlapping performance events.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_short_character.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat(shorts): add character track contracts
```

### Task 2: Import SyncToon artwork and metadata

**Files:**
- Create: `scripts/import_synctoon_character.py`
- Create: `tests/test_synctoon_import.py`
- Create: `remotion/public/characters/synctoon/character_1/PROVENANCE.md`
- Create: `remotion/public/characters/synctoon/character_1/character-manifest.json`
- Copy: `D:/synctoon/core/images/characters/character_1/**`
- Copy: `D:/synctoon/LICENSE` to `remotion/public/characters/synctoon/LICENSE`

- [ ] **Step 1: Test safe repeatable import**

```python
def test_import_builds_resolvable_manifest(tmp_path):
    manifest = import_character(SYNCTOON_FIXTURE, tmp_path)
    assert manifest["character_id"] == "character_1"
    assert manifest["fallbacks"]["head"] in manifest["assets"]["head"]
    assert all(".." not in item["path"] for group in manifest["assets"].values() for item in group.values())
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_synctoon_import.py -q`

Expected: importer module missing.

- [ ] **Step 3: Implement importer**

The script accepts `--source D:/synctoon --destination remotion/public/characters/synctoon`, copies character artwork and the GPLv3 license, reads metadata and `mouth_image.json`, emits normalized POSIX-style asset paths, verifies fallback assets, and writes source commit/provenance.

- [ ] **Step 4: Import and validate real assets**

Run: `python scripts/import_synctoon_character.py --source D:/synctoon --destination remotion/public/characters/synctoon`

Expected: manifest validation succeeds and all referenced files exist.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_synctoon_import.py -q`

Commit: `feat(shorts): import SyncToon character assets`

### Task 3: Select beat modes with guardrails

**Files:**
- Create: `src/short/beat_mode.py`
- Modify: `src/short/component_plan.py`
- Modify: `tests/test_short_character.py`

- [ ] **Step 1: Add failing selection tests**

```python
def test_mode_plan_limits_character_runs_and_memes():
    beats = [{"intent": "hook", "script_text": "Look at this"}] * 5
    plan = build_beat_mode_plan(beats, meme_slots={2})
    modes = [item["mode"] for item in plan]
    assert "meme" in modes
    assert all(modes[i:i + 3] != ["character"] * 3 for i in range(len(modes) - 2))
    assert "meme,meme" not in ",".join(modes)
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_short_character.py -q`

- [ ] **Step 3: Implement semantic selection**

Select `component` for mechanisms, code, comparisons, numbers, and diagrams;
`character` for hooks, direct explanation, bridges, reactions, and conclusions;
and `meme` only for supplied punchline slots. Apply deterministic sequence
guardrails and return one full-frame item per original beat.

- [ ] **Step 4: Update component plan**

Make `build_component_plan()` consume the selected mode plan rather than
inserting overlapping meme sub-beats. Every output item includes `mode`.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_short_character.py tests/test_short_first.py -q`

Commit: `feat(shorts): plan character component meme beats`

### Task 4: Generate deterministic character tracks

**Files:**
- Create: `src/short/character.py`
- Modify: `tests/test_short_character.py`

- [ ] **Step 1: Add failing cue and fallback tests**

```python
def test_word_timing_fallback_emits_bounded_mouth_cues():
    cues = mouth_cues_from_words([{"word": "Hello", "start_seconds": 0.2, "end_seconds": 0.8}], "happy", 1.0)
    assert cues
    assert all(0 <= cue.start < cue.end <= 1.0 for cue in cues)

def test_track_uses_neutral_defaults_for_unknown_keys(manifest):
    track, warnings = build_character_track("Hello", [], {"pose": "missing"}, manifest, 2.0)
    assert track.events[0].pose == manifest["fallbacks"]["body"]
    assert warnings
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_short_character.py -q`

- [ ] **Step 3: Port and adapt phoneme mapping**

Load the imported SyncToon phoneme map without import-time downloads. Normalize
Gentle phone output when available; otherwise distribute mapped mouth changes
inside existing word timestamps. Generate deterministic blinks from beat ID and
duration.

- [ ] **Step 4: Implement cue planning and validation**

Use a small semantic cue map for the first recurring character. Unknown model
output resolves through manifest fallbacks and records warnings; it never emits
raw paths.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_short_character.py -q`

Commit: `feat(shorts): generate character performance tracks`

### Task 5: Integrate character artifacts into short-first output

**Files:**
- Modify: `src/short/first.py`
- Modify: `src/short/generator.py`
- Modify: `src/config.py`
- Modify: `config.yaml`
- Modify: `.env.example`
- Modify: `tests/test_short_first.py`

- [ ] **Step 1: Add failing integration assertion**

Extend `test_generates_short_script_and_meme_plan` to assert that
`beat_mode_plan.json` exists, includes all three supported modes across a
representative fixture, and that character beats reference existing track JSON.

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_short_first.py -q`

- [ ] **Step 3: Write pipeline artifacts**

Generate `plans/beat_mode_plan.json`, `plans/character_plan.json`,
`character/tracks/<beat-id>.json`, and `character/validation.json`. Preserve
component/meme outputs and expose paths in `ShortFirstResult`.

- [ ] **Step 4: Preserve mode/track during storyboard round-trip**

Add `mode` and `character_track` to save/load serialization and populate tracks
after word timestamps become available. Character failure rewrites that beat to
component mode with a validation reason.

- [ ] **Step 5: Add optional configuration**

Defaults: character enabled for short-first, `character_1`, imported manifest
path, aligner URL `http://localhost:49153/transcriptions?async=false`, five-second
timeout, and word-timing fallback enabled.

- [ ] **Step 6: Run tests and commit**

Run: `pytest tests/test_short_first.py tests/test_short.py tests/test_shorts_generator.py -q`

Commit: `feat(shorts): integrate character track generation`

### Task 6: Add shared style, track lookup, and character renderer

**Files:**
- Create: `remotion/src/shorts/shortsStyle.ts`
- Create: `remotion/src/shorts/characterTypes.ts`
- Create: `remotion/src/shorts/ShortsCharacterScene.tsx`
- Create: `remotion/src/shorts/ShortsCharacterScene.test.tsx`
- Modify: `remotion/src/shorts/AnimatedCaptions.tsx`
- Modify: `remotion/src/shorts/ShortsSceneComponents.tsx`

- [ ] **Step 1: Add failing frame-state tests**

```tsx
it("selects performance, mouth, and blink state at boundaries", () => {
  expect(resolveCharacterState(track, 1.9)).toMatchObject({head: "R", blinking: true});
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `npm.cmd test -- ShortsCharacterScene.test.tsx` from `remotion/`.

- [ ] **Step 3: Implement shared design tokens and lookup**

Move palette, typography, spacing, surfaces, and motion constants into
`shortsStyle.ts`. Implement pure interval lookup helpers in `characterTypes.ts`.

- [ ] **Step 4: Implement layered renderer**

Render background, body, head, eyes, and mouth with Remotion `Img` and
`staticFile`. Use manifest placement metadata, neutral fallbacks, frame-driven
entry motion, and the existing caption-safe area.

- [ ] **Step 5: Apply shared tokens to existing modes**

Update captions and generic components to import the same tokens without
changing their semantics.

- [ ] **Step 6: Run tests and commit**

Run: `npm.cmd test -- ShortsCharacterScene.test.tsx` from `remotion/`.

Commit: `feat(shorts): render layered SyncToon character`

### Task 7: Dispatch cohesive full-frame modes and transitions

**Files:**
- Create: `remotion/src/shorts/ShortsTransition.tsx`
- Create: `remotion/src/shorts/ShortsPlayer.test.tsx`
- Modify: `remotion/src/shorts/ShortsPlayer.tsx`
- Modify: `remotion/src/shorts/index.ts`

- [ ] **Step 1: Add failing dispatch tests**

Test `character`, `component`, and `meme` mode selection plus previous/next mode
transition selection. Assert captions and audio remain outside the mode renderer.

- [ ] **Step 2: Run and confirm failure**

Run: `npm.cmd test -- ShortsPlayer.test.tsx` from `remotion/`.

- [ ] **Step 3: Implement mode dispatch**

Character beats use `ShortsCharacterScene`; component and meme beats continue
through existing custom/generic renderers. Pass neighboring modes into a shared
transition wrapper while keeping captions, progress, voiceover, and music
mounted once at player level.

- [ ] **Step 4: Implement transition grammar**

Use short frame-driven accent-shape handoffs for character/component boundaries,
punch cuts for meme boundaries, and deterministic hard cuts when no transition
is appropriate. Do not use generic crossfades.

- [ ] **Step 5: Run tests, typecheck, and commit**

Run from `remotion/`:

```text
npm.cmd test
npx.cmd tsc --noEmit
```

Commit: `feat(shorts): unify beat mode transitions`

### Task 8: End-to-end verification and documentation

**Files:**
- Modify: `docs/SHORTS.md`
- Modify: `README.md`
- Create: representative generated artifacts under a temporary test project only.

- [ ] **Step 1: Run Python regression suite**

Run: `pytest tests/test_short_character.py tests/test_synctoon_import.py tests/test_short_first.py tests/test_short.py tests/test_shorts_generator.py tests/test_short_verticals.py -q`

Expected: all pass.

- [ ] **Step 2: Run Remotion verification**

Run from `remotion/`:

```text
npm.cmd test
npx.cmd tsc --noEmit
npm.cmd run build
```

Expected: all pass.

- [ ] **Step 3: Generate and inspect a representative draft**

Generate a mock Short with character, component, and meme beats; render boundary
frames and a low-resolution draft. Verify no blank frame, caption reset, audio
gap, layout jump, palette shift, or broken asset reference.

- [ ] **Step 4: Document setup and GPL provenance**

Document the optional Gentle service, fallback behavior, asset re-import command,
generated artifacts, and the GPLv3 status of the integrated SyncToon material.

- [ ] **Step 5: Final commit**

Commit: `docs(shorts): document character workflow`
