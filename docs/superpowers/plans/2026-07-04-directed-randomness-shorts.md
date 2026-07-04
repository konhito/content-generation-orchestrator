# Directed Randomness Shorts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build planner-driven mixed Shorts scenes where the recurring character, components, memes, captions, camera, and transitions are composed together per beat.

**Architecture:** Add `visual_recipe` to Shorts beats, generate deterministic scene recipes in Python, and render recipes in Remotion through a new `ShortsMixedScene` layer compositor. Keep the existing fullscreen `mode` renderer as fallback for old storyboards.

**Tech Stack:** Python 3.12, Pydantic, pytest, Remotion 4, React 18, TypeScript, Vitest.

---

## File Structure

- Create `src/short/scene_recipe.py`
  - Owns recipe enums, deterministic recipe selection, niche tone profiles, and guardrails.
- Modify `src/short/models.py`
  - Adds serializable `VisualRecipe`, `RecipeCharacterLayer`, `RecipeComponentLayer`, `RecipeMemeLayer`, `RecipeCamera`, and `RecipeTransition`.
- Modify `src/short/first.py`
  - Calls recipe planner after component/meme/character planning and writes `plans/scene_recipe_plan.json`.
- Modify `src/short/generator.py`
  - Serializes and loads `visual_recipe`.
- Modify `src/cli/main.py`
  - Preserves visual recipes when applying component plans and character tracks.
- Create `tests/test_short_scene_recipe.py`
  - Covers deterministic planning, guardrails, serialization, and fallback compatibility.
- Modify `tests/test_short_first.py`
  - Verifies short-first output includes recipe plan artifacts.
- Modify `tests/test_short_character.py`
  - Verifies storyboards preserve recipes alongside character tracks.
- Create `remotion/src/shorts/recipeTypes.ts`
  - TypeScript mirror of the recipe schema.
- Create `remotion/src/shorts/ShortsMixedScene.tsx`
  - Layer compositor for character, component, meme, callout, camera, and transition effects.
- Modify `remotion/src/shorts/ShortsCharacterScene.tsx`
  - Adds layout props so the character can render as foreground, sidecar, or sticker-scale.
- Modify `remotion/src/shorts/ShortsPlayer.tsx`
  - Routes beats with `visual_recipe` to `ShortsMixedScene`; keeps current fallback.
- Modify `remotion/src/shorts/index.ts`
  - Exports mixed scene and recipe types.
- Create `remotion/src/shorts/ShortsMixedScene.test.tsx`
  - Covers layer composition and fallback behavior.
- Modify `remotion/src/shorts/ShortsPlayer.test.tsx`
  - Verifies recipe dispatch wins over legacy mode dispatch.
- Modify `docs/SHORTS.md`
  - Documents mixed recipe generation and debugging artifacts.

---

### Task 1: Python Recipe Schema

**Files:**
- Modify: `src/short/models.py`
- Modify: `src/short/generator.py`
- Test: `tests/test_short_scene_recipe.py`

- [ ] **Step 1: Write failing schema serialization tests**

Create `tests/test_short_scene_recipe.py` with:

```python
from src.short.generator import ShortGenerator
from src.short.models import (
    RecipeCamera,
    RecipeCharacterLayer,
    RecipeComponentLayer,
    RecipeMemeLayer,
    RecipeTransition,
    ShortBeatMode,
    ShortsBeat,
    ShortsScript,
    VisualRecipe,
)


def test_visual_recipe_round_trips_through_short_script(tmp_path):
    script = ShortsScript(
        title="Recipe demo",
        total_duration_seconds=6.0,
        beats=[
            ShortsBeat(
                id="beat_001",
                start_seconds=0.0,
                end_seconds=6.0,
                narration="AI predicts likely text, not truth.",
                visual_description="Token probabilities behind host",
                visual_elements=["host", "probability bars", "confidently wrong sticker"],
                caption_text="AI predicts text, not truth",
                mode=ShortBeatMode.CHARACTER,
                visual_recipe=VisualRecipe(
                    recipe_id="host_foreground_concept_backdrop",
                    layout="character_foreground_visual_backdrop",
                    intent="explain_surprise",
                    attention_strategy="host_demonstrates_concept",
                    character=RecipeCharacterLayer(
                        presence="primary",
                        position="lower_center",
                        scale=0.82,
                        pose_intent="explain",
                        emotion="curious",
                    ),
                    component=RecipeComponentLayer(
                        role="main_explanation",
                        component_type="probability_bars",
                        position="background_stage",
                        emphasis_words=["predicts", "not truth"],
                    ),
                    meme=RecipeMemeLayer(
                        role="accent",
                        style="sticker_pop",
                        timing="after_key_claim",
                        intensity=0.35,
                    ),
                    camera=RecipeCamera(
                        motion="slow_push",
                        punch_zoom_on="not truth",
                    ),
                    transition=RecipeTransition(
                        transition_in="match_cut",
                        transition_out="accent_whip",
                    ),
                ),
            )
        ],
    )

    generator = ShortGenerator(output_dir=tmp_path)
    path = generator.save_script(script, "recipe.json")

    loaded = generator.load_script(path)

    assert loaded.beats[0].visual_recipe is not None
    assert loaded.beats[0].visual_recipe.recipe_id == "host_foreground_concept_backdrop"
    assert loaded.beats[0].visual_recipe.character.position == "lower_center"
    assert loaded.beats[0].visual_recipe.component.emphasis_words == ["predicts", "not truth"]
    assert loaded.beats[0].visual_recipe.meme.intensity == 0.35
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```powershell
New-Item -ItemType Directory -Force .tmp\pytest | Out-Null
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_scene_recipe.py -q
```

Expected: fail because recipe classes and `visual_recipe` do not exist.

- [ ] **Step 3: Add recipe models**

In `src/short/models.py`, add these classes near the existing character models:

```python
class RecipeCharacterLayer(BaseModel):
    presence: str = "primary"
    position: str = "lower_center"
    scale: float = Field(default=0.82, ge=0.2, le=1.4)
    pose_intent: str = "explain"
    emotion: str = "happy"


class RecipeComponentLayer(BaseModel):
    role: str = "main_explanation"
    component_type: str = "concept_card"
    position: str = "background_stage"
    emphasis_words: list[str] = Field(default_factory=list)


class RecipeMemeLayer(BaseModel):
    role: str = "none"
    style: str = "none"
    timing: str = "none"
    intensity: float = Field(default=0.0, ge=0.0, le=1.0)


class RecipeCamera(BaseModel):
    motion: str = "steady"
    punch_zoom_on: str | None = None


class RecipeTransition(BaseModel):
    transition_in: str = "soft_cut"
    transition_out: str = "soft_cut"


class VisualRecipe(BaseModel):
    recipe_id: str
    layout: str
    intent: str
    attention_strategy: str
    character: RecipeCharacterLayer = Field(default_factory=RecipeCharacterLayer)
    component: RecipeComponentLayer = Field(default_factory=RecipeComponentLayer)
    meme: RecipeMemeLayer = Field(default_factory=RecipeMemeLayer)
    camera: RecipeCamera = Field(default_factory=RecipeCamera)
    transition: RecipeTransition = Field(default_factory=RecipeTransition)
```

Add this field to `ShortsBeat`:

```python
visual_recipe: VisualRecipe | None = None
```

- [ ] **Step 4: Serialize and load the recipe**

In `src/short/generator.py`, update beat serialization to include:

```python
"visual_recipe": beat.visual_recipe.model_dump() if beat.visual_recipe else None,
```

Update beat loading to pass:

```python
visual_recipe=VisualRecipe(**beat_data["visual_recipe"])
if beat_data.get("visual_recipe")
else None,
```

Import `VisualRecipe` from `src.short.models`.

- [ ] **Step 5: Run schema tests**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_scene_recipe.py -q
```

Expected: pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add src\short\models.py src\short\generator.py tests\test_short_scene_recipe.py
git commit -m "feat(shorts): add visual recipe schema"
```

---

### Task 2: Deterministic Scene Recipe Planner

**Files:**
- Create: `src/short/scene_recipe.py`
- Modify: `tests/test_short_scene_recipe.py`

- [ ] **Step 1: Add failing planner tests**

Append to `tests/test_short_scene_recipe.py`:

```python
from src.short.scene_recipe import (
    SceneRecipeInput,
    plan_scene_recipes,
)


def test_scene_recipe_planner_is_seeded_and_deterministic():
    inputs = [
        SceneRecipeInput(
            beat_id="beat_001",
            beat_index=0,
            beat_count=2,
            topic="Why AI hallucinates",
            niche="tech",
            narration="AI predicts likely text, not truth.",
            caption_text="AI predicts text, not truth",
            visual_description="probability bars",
            visual_elements=["tokens", "probability"],
            component_type="probability_bars",
            has_meme=True,
        ),
        SceneRecipeInput(
            beat_id="beat_002",
            beat_index=1,
            beat_count=2,
            topic="Why AI hallucinates",
            niche="tech",
            narration="That is why it can sound confident and still be wrong.",
            caption_text="confident and wrong",
            visual_description="wrong answer sticker",
            visual_elements=["meme", "reaction"],
            component_type="meme_card",
            has_meme=True,
        ),
    ]

    first = plan_scene_recipes(inputs, seed="synctoon-demo:demo")
    second = plan_scene_recipes(inputs, seed="synctoon-demo:demo")

    assert [recipe.model_dump() for recipe in first] == [
        recipe.model_dump() for recipe in second
    ]
    assert first[0].character.presence == "primary"
    assert first[0].component.role in {"main_explanation", "supporting_evidence"}
    assert first[1].meme.intensity > 0


def test_serious_topic_lowers_meme_intensity():
    inputs = [
        SceneRecipeInput(
            beat_id="beat_001",
            beat_index=0,
            beat_count=1,
            topic="Election misinformation during a disaster",
            niche="politics",
            narration="False claims spread during the emergency.",
            caption_text="false claims spread",
            visual_description="timeline of claims",
            visual_elements=["timeline", "evidence"],
            component_type="timeline",
            has_meme=True,
            seriousness_score=0.9,
        )
    ]

    recipes = plan_scene_recipes(inputs, seed="serious")

    assert recipes[0].meme.intensity <= 0.2
    assert recipes[0].attention_strategy in {
        "host_reacts_to_evidence",
        "timeline_walkthrough",
        "rapid_evidence_wall",
    }
```

- [ ] **Step 2: Run planner tests and verify they fail**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_scene_recipe.py -q
```

Expected: fail because `src.short.scene_recipe` does not exist.

- [ ] **Step 3: Implement planner input and helpers**

Create `src/short/scene_recipe.py`:

```python
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from src.short.models import (
    RecipeCamera,
    RecipeCharacterLayer,
    RecipeComponentLayer,
    RecipeMemeLayer,
    RecipeTransition,
    VisualRecipe,
)


@dataclass(frozen=True)
class SceneRecipeInput:
    beat_id: str
    beat_index: int
    beat_count: int
    topic: str
    niche: str
    narration: str
    caption_text: str
    visual_description: str
    visual_elements: list[str] = field(default_factory=list)
    component_type: str = "concept_card"
    has_meme: bool = False
    seriousness_score: float = 0.0


def _rng(seed: str, beat_id: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{beat_id}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def classify_intent(item: SceneRecipeInput) -> str:
    text = f"{item.narration} {item.caption_text}".lower()
    if item.beat_index == 0:
        return "hook"
    if _contains_any(text, ("but", "however", "instead", "not ")):
        return "contrast"
    if _contains_any(text, ("because", "why", "that is why", "so ")):
        return "explain"
    if _contains_any(text, ("watch", "then", "suddenly", "turns into")):
        return "reveal"
    if _contains_any(text, ("wrong", "broke", "absurd", "confident")):
        return "joke"
    if item.beat_index == item.beat_count - 1:
        return "recap"
    return "explain"
```

- [ ] **Step 4: Implement recipe selection**

Append to `src/short/scene_recipe.py`:

```python
NICHE_MEME_BASE = {
    "tech": 0.35,
    "finance": 0.25,
    "politics": 0.18,
    "news": 0.18,
    "gaming": 0.55,
    "science": 0.25,
    "motivation": 0.12,
    "entertainment": 0.5,
    "sports": 0.42,
}


def _attention_strategy(item: SceneRecipeInput, intent: str, chooser: random.Random) -> str:
    if item.seriousness_score >= 0.75:
        return chooser.choice(
            ["host_reacts_to_evidence", "timeline_walkthrough", "rapid_evidence_wall"]
        )
    if intent == "hook":
        return chooser.choice(["visual_metaphor", "host_demonstrates_concept"])
    if intent == "contrast":
        return chooser.choice(["before_after_comparison", "reaction_stack"])
    if intent == "joke" and item.has_meme:
        return "meme_interruption"
    if item.component_type in {"timeline", "scoreboard", "comparison"}:
        return "timeline_walkthrough"
    return chooser.choice(["host_demonstrates_concept", "host_reacts_to_evidence"])


def _recipe_id(strategy: str) -> tuple[str, str]:
    mapping = {
        "host_demonstrates_concept": (
            "host_foreground_concept_backdrop",
            "character_foreground_visual_backdrop",
        ),
        "host_reacts_to_evidence": (
            "host_sidecar_main_diagram",
            "character_sidecar_visual_main",
        ),
        "meme_interruption": (
            "meme_interruption",
            "character_primary_meme_pop",
        ),
        "reaction_stack": (
            "reaction_stack",
            "character_component_meme_stack",
        ),
        "visual_metaphor": (
            "visual_metaphor_stage",
            "character_interacts_with_props",
        ),
        "rapid_evidence_wall": (
            "rapid_evidence_wall",
            "character_anchor_evidence_cards",
        ),
        "timeline_walkthrough": (
            "host_sidecar_main_diagram",
            "character_sidecar_visual_main",
        ),
        "before_after_comparison": (
            "reaction_stack",
            "character_component_meme_stack",
        ),
    }
    return mapping[strategy]


def _meme_intensity(item: SceneRecipeInput, intent: str, strategy: str) -> float:
    if not item.has_meme:
        return 0.0
    base = NICHE_MEME_BASE.get(item.niche.lower(), 0.3)
    if intent == "joke" or strategy == "meme_interruption":
        base += 0.18
    if item.seriousness_score >= 0.75:
        base = min(base, 0.2)
    return round(max(0.0, min(base, 0.75)), 2)
```

- [ ] **Step 5: Implement public planner**

Append to `src/short/scene_recipe.py`:

```python
def plan_scene_recipes(items: list[SceneRecipeInput], seed: str) -> list[VisualRecipe]:
    recipes: list[VisualRecipe] = []
    for item in items:
        chooser = _rng(seed, item.beat_id)
        intent = classify_intent(item)
        strategy = _attention_strategy(item, intent, chooser)
        recipe_id, layout = _recipe_id(strategy)
        meme_intensity = _meme_intensity(item, intent, strategy)
        component_role = (
            "supporting_evidence"
            if strategy in {"host_reacts_to_evidence", "rapid_evidence_wall"}
            else "main_explanation"
        )
        character_position = (
            "side_left"
            if layout == "character_sidecar_visual_main"
            else "lower_center"
        )
        character_scale = 0.58 if character_position == "side_left" else 0.82

        recipes.append(
            VisualRecipe(
                recipe_id=recipe_id,
                layout=layout,
                intent=intent,
                attention_strategy=strategy,
                character=RecipeCharacterLayer(
                    presence="primary",
                    position=character_position,
                    scale=character_scale,
                    pose_intent="react" if "reacts" in strategy else "explain",
                    emotion="curious" if intent in {"hook", "explain"} else "happy",
                ),
                component=RecipeComponentLayer(
                    role=component_role,
                    component_type=item.component_type or "concept_card",
                    position=(
                        "main_stage"
                        if layout == "character_sidecar_visual_main"
                        else "background_stage"
                    ),
                    emphasis_words=[
                        word.strip(".,!?").lower()
                        for word in item.caption_text.split()
                        if len(word.strip(".,!?")) > 4
                    ][:3],
                ),
                meme=RecipeMemeLayer(
                    role="accent" if meme_intensity > 0 else "none",
                    style="sticker_pop" if strategy != "meme_interruption" else "interrupt_card",
                    timing="after_key_claim" if meme_intensity > 0 else "none",
                    intensity=meme_intensity,
                ),
                camera=RecipeCamera(
                    motion=chooser.choice(["steady", "slow_push", "micro_parallax"]),
                    punch_zoom_on=None if meme_intensity < 0.45 else "key_claim",
                ),
                transition=RecipeTransition(
                    transition_in="match_cut",
                    transition_out="accent_whip" if meme_intensity >= 0.45 else "soft_cut",
                ),
            )
        )
    return recipes
```

- [ ] **Step 6: Run planner tests**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_scene_recipe.py -q
```

Expected: pass.

- [ ] **Step 7: Commit Task 2**

```powershell
git add src\short\scene_recipe.py tests\test_short_scene_recipe.py
git commit -m "feat(shorts): plan mixed scene recipes"
```

---

### Task 3: Wire Recipes into Short-First Generation

**Files:**
- Modify: `src/short/first.py`
- Modify: `src/cli/main.py`
- Modify: `tests/test_short_first.py`
- Modify: `tests/test_short_character.py`

- [ ] **Step 1: Add failing short-first artifact test**

In `tests/test_short_first.py`, add assertions to the existing short-first generation test after result paths are checked:

```python
assert result.scene_recipe_plan_path is not None
assert result.scene_recipe_plan_path.exists()

scene_recipe_plan = json.loads(result.scene_recipe_plan_path.read_text(encoding="utf-8"))
assert scene_recipe_plan["recipes"]
assert scene_recipe_plan["recipes"][0]["recipe_id"]
assert scene_recipe_plan["recipes"][0]["character"]["presence"] == "primary"
```

If `ShortFirstResult` is asserted directly in the file, add:

```python
assert "scene_recipe_plan_path" in result.model_dump()
```

- [ ] **Step 2: Add failing storyboard preservation test**

In `tests/test_short_character.py`, extend the storyboard loader preservation test:

```python
assert loaded.beats[0].visual_recipe is not None
assert loaded.beats[0].visual_recipe.recipe_id == "host_foreground_concept_backdrop"
```

The fixture beat should include the same `VisualRecipe` object used in Task 1.

- [ ] **Step 3: Run targeted tests and verify failure**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_first.py tests\test_short_character.py -q
```

Expected: fail because short-first does not write recipe plan artifacts yet.

- [ ] **Step 4: Add result path to `ShortFirstResult`**

In `src/short/first.py`, add this field to `ShortFirstResult`:

```python
scene_recipe_plan_path: Path | None = None
```

- [ ] **Step 5: Build planner inputs in short-first**

In `src/short/first.py`, import:

```python
from src.short.scene_recipe import SceneRecipeInput, plan_scene_recipes
```

After component and character planning, build inputs:

```python
recipe_inputs = [
    SceneRecipeInput(
        beat_id=beat.id,
        beat_index=index,
        beat_count=len(short_script.beats),
        topic=topic,
        niche=niche_name,
        narration=beat.narration,
        caption_text=beat.caption_text,
        visual_description=beat.visual_description,
        visual_elements=beat.visual_elements,
        component_type=component_plan.items[index].component_type
        if index < len(component_plan.items)
        else "concept_card",
        has_meme=beat.id in _meme_slots(meme_plan),
        seriousness_score=0.0,
    )
    for index, beat in enumerate(short_script.beats)
]
recipes = plan_scene_recipes(
    recipe_inputs,
    seed=f"{project_id}:{variant}:{topic}:{niche_name}",
)
for beat, recipe in zip(short_script.beats, recipes, strict=False):
    beat.visual_recipe = recipe
```

- [ ] **Step 6: Write recipe plan artifact**

In `src/short/first.py`, write:

```python
scene_recipe_plan_path = plans_dir / "scene_recipe_plan.json"
scene_recipe_plan_path.write_text(
    json.dumps(
        {
            "project_id": project_id,
            "variant": variant,
            "recipes": [recipe.model_dump() for recipe in recipes],
        },
        indent=2,
    ),
    encoding="utf-8",
)
```

Return it through `ShortFirstResult(scene_recipe_plan_path=scene_recipe_plan_path, ...)`.

- [ ] **Step 7: Preserve recipe through CLI storyboard application**

In `src/cli/main.py`, when `_apply_component_plan_to_storyboard` copies beat fields, ensure this assignment remains on the storyboard beat:

```python
storyboard_beat.visual_recipe = short_beat.visual_recipe
```

If the function rebuilds `ShortsBeat` objects from dictionaries, pass:

```python
visual_recipe=short_beat.visual_recipe
```

- [ ] **Step 8: Run targeted tests**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_first.py tests\test_short_character.py tests\test_short_scene_recipe.py -q
```

Expected: pass.

- [ ] **Step 9: Commit Task 3**

```powershell
git add src\short\first.py src\cli\main.py tests\test_short_first.py tests\test_short_character.py tests\test_short_scene_recipe.py
git commit -m "feat(shorts): attach scene recipes"
```

---

### Task 4: Remotion Recipe Types and Mixed Scene Renderer

**Files:**
- Create: `remotion/src/shorts/recipeTypes.ts`
- Create: `remotion/src/shorts/ShortsMixedScene.tsx`
- Modify: `remotion/src/shorts/ShortsCharacterScene.tsx`
- Modify: `remotion/src/shorts/index.ts`
- Test: `remotion/src/shorts/ShortsMixedScene.test.tsx`

- [ ] **Step 1: Add failing mixed scene tests**

Create `remotion/src/shorts/ShortsMixedScene.test.tsx`:

```typescript
import {describe, expect, it} from "vitest";
import React from "react";

import {ShortsMixedScene, recipeLayerPlan} from "./ShortsMixedScene";
import type {VisualRecipe} from "./recipeTypes";

const recipe: VisualRecipe = {
  recipe_id: "host_foreground_concept_backdrop",
  layout: "character_foreground_visual_backdrop",
  intent: "explain",
  attention_strategy: "host_demonstrates_concept",
  character: {
    presence: "primary",
    position: "lower_center",
    scale: 0.82,
    pose_intent: "explain",
    emotion: "curious",
  },
  component: {
    role: "main_explanation",
    component_type: "concept_card",
    position: "background_stage",
    emphasis_words: ["predicts", "truth"],
  },
  meme: {
    role: "accent",
    style: "sticker_pop",
    timing: "after_key_claim",
    intensity: 0.35,
  },
  camera: {
    motion: "slow_push",
    punch_zoom_on: null,
  },
  transition: {
    transition_in: "match_cut",
    transition_out: "soft_cut",
  },
};

describe("recipeLayerPlan", () => {
  it("keeps component behind the host for foreground recipes", () => {
    const plan = recipeLayerPlan(recipe);
    expect(plan.characterPosition).toBe("lower_center");
    expect(plan.componentPosition).toBe("background_stage");
    expect(plan.memeVisible).toBe(true);
  });

  it("moves host to sidecar for diagram recipes", () => {
    const plan = recipeLayerPlan({
      ...recipe,
      layout: "character_sidecar_visual_main",
      character: {...recipe.character, position: "side_left", scale: 0.58},
      component: {...recipe.component, position: "main_stage"},
    });

    expect(plan.characterPosition).toBe("side_left");
    expect(plan.componentPosition).toBe("main_stage");
  });
});

describe("ShortsMixedScene", () => {
  it("exports a React component", () => {
    expect(typeof ShortsMixedScene).toBe("function");
    expect(React.isValidElement(<ShortsMixedScene beat={{} as any} frame={0} fps={30} scale={1} />)).toBe(true);
  });
});
```

- [ ] **Step 2: Run Remotion test and verify failure**

Run:

```powershell
Set-Location remotion
npm.cmd test -- ShortsMixedScene.test.tsx
Set-Location ..
```

Expected: fail because recipe types and mixed scene do not exist.

- [ ] **Step 3: Add TypeScript recipe types**

Create `remotion/src/shorts/recipeTypes.ts`:

```typescript
export interface RecipeCharacterLayer {
  presence: string;
  position: string;
  scale: number;
  pose_intent: string;
  emotion: string;
}

export interface RecipeComponentLayer {
  role: string;
  component_type: string;
  position: string;
  emphasis_words: string[];
}

export interface RecipeMemeLayer {
  role: string;
  style: string;
  timing: string;
  intensity: number;
}

export interface RecipeCamera {
  motion: string;
  punch_zoom_on?: string | null;
}

export interface RecipeTransition {
  transition_in: string;
  transition_out: string;
}

export interface VisualRecipe {
  recipe_id: string;
  layout: string;
  intent: string;
  attention_strategy: string;
  character: RecipeCharacterLayer;
  component: RecipeComponentLayer;
  meme: RecipeMemeLayer;
  camera: RecipeCamera;
  transition: RecipeTransition;
}
```

- [ ] **Step 4: Add character layout props**

In `remotion/src/shorts/ShortsCharacterScene.tsx`, extend props:

```typescript
  position?: string;
  characterScale?: number;
  showStage?: boolean;
```

Default them in the component:

```typescript
  position = "lower_center",
  characterScale = 1,
  showStage = true,
```

Replace the hardcoded character container transform with:

```typescript
const positionOffset = position === "side_left"
  ? {left: 0, top: 190, width: 620, height: 980}
  : {left: 70, top: 170, width: 940, height: 1040};
```

Use `positionOffset` for the inner container:

```tsx
left: positionOffset.left * scale,
top: positionOffset.top * scale,
width: positionOffset.width * scale,
height: positionOffset.height * scale,
transform: `translateY(${drift * scale}px) scale(${characterScale * (0.94 + entrance * 0.06)})`,
```

Wrap the existing stage card with:

```tsx
{showStage && (
  <div style={...existingStageStyle} />
)}
```

- [ ] **Step 5: Implement mixed scene**

Create `remotion/src/shorts/ShortsMixedScene.tsx`:

```typescript
import React from "react";
import {interpolate, spring} from "remotion";

import {ShortsCharacterScene, type ShortsBeat} from "./ShortsPlayer";
import {ShortsVisualArea} from "./ShortsVisualArea";
import type {VisualRecipe} from "./recipeTypes";
import {SHORTS_COLORS, SHORTS_FONTS, SHORTS_MOTION} from "./shortsStyle";

export const recipeLayerPlan = (recipe: VisualRecipe) => ({
  characterPosition: recipe.character.position,
  componentPosition: recipe.component.position,
  memeVisible: recipe.meme.role !== "none" && recipe.meme.intensity > 0,
});

export const ShortsMixedScene: React.FC<{
  beat: ShortsBeat;
  frame: number;
  fps: number;
  scale: number;
}> = ({beat, frame, fps, scale}) => {
  const recipe = beat.visual_recipe;
  if (!recipe || !beat.character_data) {
    return <ShortsVisualArea beat={beat} frame={frame} fps={fps} scale={scale} />;
  }

  const entrance = spring({frame, fps, config: SHORTS_MOTION.smoothSpring});
  const push = recipe.camera.motion === "slow_push"
    ? interpolate(frame, [0, 120], [0.97, 1.02], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const memePop = spring({
    frame: Math.max(0, frame - Math.round((beat.end_seconds - beat.start_seconds) * fps * 0.45)),
    fps,
    config: SHORTS_MOTION.snappySpring,
  });

  return (
    <div style={{position: "relative", width: 1080 * scale, height: 1500 * scale, overflow: "hidden"}}>
      <div
        style={{
          position: "absolute",
          inset: `${120 * scale}px ${80 * scale}px ${170 * scale}px`,
          borderRadius: 48 * scale,
          border: `${2 * scale}px solid ${SHORTS_COLORS.primary}44`,
          background: `radial-gradient(circle at 50% 35%, ${SHORTS_COLORS.primary}1f, ${SHORTS_COLORS.surface}e8 65%)`,
          boxShadow: `0 30px 100px ${SHORTS_COLORS.primary}18`,
          transform: `scale(${push})`,
          opacity: entrance,
        }}
      />

      <div
        style={{
          position: "absolute",
          left: recipe.component.position === "main_stage" ? 360 * scale : 130 * scale,
          top: recipe.component.position === "main_stage" ? 260 * scale : 190 * scale,
          width: recipe.component.position === "main_stage" ? 600 * scale : 820 * scale,
          height: recipe.component.position === "main_stage" ? 760 * scale : 850 * scale,
          opacity: 0.82,
          transform: `scale(${push})`,
        }}
      >
        <ShortsVisualArea beat={beat} frame={frame} fps={fps} scale={scale * 0.78} />
      </div>

      <ShortsCharacterScene
        track={beat.character_data}
        frame={frame}
        fps={fps}
        scale={scale}
        emphasis={beat.visual.primary_text}
        position={recipe.character.position}
        characterScale={recipe.character.scale}
        showStage={false}
      />

      {recipe.meme.role !== "none" && recipe.meme.intensity > 0 && (
        <div
          style={{
            position: "absolute",
            right: 100 * scale,
            top: 230 * scale,
            padding: `${18 * scale}px ${24 * scale}px`,
            borderRadius: 28 * scale,
            background: "#fff",
            color: "#050509",
            fontFamily: SHORTS_FONTS.primary,
            fontWeight: 900,
            fontSize: 34 * scale,
            textTransform: "uppercase",
            boxShadow: `0 18px 60px ${SHORTS_COLORS.primary}55`,
            transform: `rotate(-3deg) scale(${0.2 + memePop * 0.8})`,
            opacity: Math.min(1, memePop) * recipe.meme.intensity * 1.4,
          }}
        >
          {recipe.meme.style === "interrupt_card" ? "WAIT, WHAT?" : "MEME CUT"}
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 6: Export mixed scene**

In `remotion/src/shorts/index.ts`, add:

```typescript
export {ShortsMixedScene} from "./ShortsMixedScene";
export type {VisualRecipe} from "./recipeTypes";
```

- [ ] **Step 7: Run mixed scene tests**

Run:

```powershell
Set-Location remotion
npm.cmd test -- ShortsMixedScene.test.tsx
Set-Location ..
```

Expected: pass.

- [ ] **Step 8: Commit Task 4**

```powershell
git add remotion\src\shorts\recipeTypes.ts remotion\src\shorts\ShortsMixedScene.tsx remotion\src\shorts\ShortsMixedScene.test.tsx remotion\src\shorts\ShortsCharacterScene.tsx remotion\src\shorts\index.ts
git commit -m "feat(shorts): render mixed scene recipes"
```

---

### Task 5: Dispatch Recipes from ShortsPlayer

**Files:**
- Modify: `remotion/src/shorts/ShortsPlayer.tsx`
- Modify: `remotion/src/shorts/ShortsPlayer.test.tsx`

- [ ] **Step 1: Add failing dispatch test**

In `remotion/src/shorts/ShortsPlayer.test.tsx`, add:

```typescript
import {rendererForBeat} from "./ShortsPlayer";

it("uses mixed renderer when a visual recipe exists", () => {
  expect(rendererForBeat({visual_recipe: {recipe_id: "x"}} as any)).toBe("mixed");
});

it("keeps legacy character renderer without visual recipe", () => {
  expect(rendererForBeat({mode: "character", character_data: {}} as any)).toBe("character");
});
```

- [ ] **Step 2: Run dispatch test and verify failure**

Run:

```powershell
Set-Location remotion
npm.cmd test -- ShortsPlayer.test.tsx
Set-Location ..
```

Expected: fail because `rendererForBeat` is not exported.

- [ ] **Step 3: Add recipe type to `ShortsBeat`**

In `remotion/src/shorts/ShortsPlayer.tsx`, import:

```typescript
import {ShortsMixedScene} from "./ShortsMixedScene";
import type {VisualRecipe} from "./recipeTypes";
```

Add field to `ShortsBeat`:

```typescript
visual_recipe?: VisualRecipe;
```

- [ ] **Step 4: Add renderer selector**

In `remotion/src/shorts/ShortsPlayer.tsx`, export:

```typescript
export const rendererForBeat = (beat: Partial<ShortsBeat>): "mixed" | "character" | "visual" => {
  if (beat.visual_recipe) return "mixed";
  if (rendererForMode(beat.mode) === "character" && beat.character_data) return "character";
  return "visual";
};
```

- [ ] **Step 5: Route mixed scenes first**

In `VisualRenderer`, add before the character branch:

```tsx
  if (rendererForBeat(beat) === "mixed") {
    return (
      <ShortsMixedScene
        beat={beat}
        frame={Math.max(0, frame - Math.round(beat.start_seconds * fps))}
        fps={fps}
        scale={scale}
      />
    );
  }
```

- [ ] **Step 6: Run Remotion tests**

Run:

```powershell
Set-Location remotion
npm.cmd test -- ShortsPlayer.test.tsx ShortsMixedScene.test.tsx ShortsCharacterScene.test.tsx
Set-Location ..
```

Expected: pass.

- [ ] **Step 7: Commit Task 5**

```powershell
git add remotion\src\shorts\ShortsPlayer.tsx remotion\src\shorts\ShortsPlayer.test.tsx
git commit -m "feat(shorts): dispatch visual recipes"
```

---

### Task 6: End-to-End Generation and Render Verification

**Files:**
- Modify: `docs/SHORTS.md`
- Test through CLI and Remotion render scripts.

- [ ] **Step 1: Update docs**

In `docs/SHORTS.md`, add under "Character, component, and meme flow":

```markdown
The current mixed-scene system writes `plans/scene_recipe_plan.json` and embeds
`visual_recipe` on each storyboard beat. A recipe decides how the recurring host
character, component visualization, meme accent, callout, camera motion, and
transition work together in the same frame. Legacy `mode` remains as fallback
for older storyboards.
```

- [ ] **Step 2: Run focused Python tests**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_scene_recipe.py tests\test_short_character.py tests\test_short_first.py tests\test_short_first_cli.py tests\test_short.py tests\test_shorts_generator.py tests\test_short_verticals.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run Remotion tests**

Run:

```powershell
Set-Location remotion
npm.cmd test
Set-Location ..
```

Expected: all Remotion tests pass.

- [ ] **Step 4: Generate a mock mixed-scene short**

Run:

```powershell
.\.venv\Scripts\python.exe -m src.cli --projects-dir .tmp\integration-projects short generate mixed-demo --topic "Why AI hallucinates" --niche tech --variant demo --duration 30 --mock --skip-voiceover --skip-custom-scenes --force
```

Expected:

- `.tmp\integration-projects\mixed-demo\short\demo\plans\scene_recipe_plan.json` exists
- `.tmp\integration-projects\mixed-demo\short\demo\storyboard\shorts_storyboard.json` contains `"visual_recipe"`

- [ ] **Step 5: Render representative frames**

Run:

```powershell
node remotion\scripts\render.mjs --composition ShortsPlayer --storyboard .tmp\integration-projects\mixed-demo\short\demo\storyboard\shorts_storyboard.json --output .tmp\mixed-scene-check.mp4 --width 540 --height 960 --frames 0-180 --fast --concurrency 2
```

Expected: render exits 0 and `.tmp\mixed-scene-check.mp4` exists.

- [ ] **Step 6: Extract and inspect frames**

Run:

```powershell
$ffmpeg='D:\video_explainer\remotion\node_modules\@remotion\compositor-win32-x64-msvc\ffmpeg.exe'
New-Item -ItemType Directory -Force .tmp\mixed-scene-frames | Out-Null
& $ffmpeg -y -ss 2 -i .tmp\mixed-scene-check.mp4 -frames:v 1 .tmp\mixed-scene-frames\frame_002s.png
& $ffmpeg -y -ss 5 -i .tmp\mixed-scene-check.mp4 -frames:v 1 .tmp\mixed-scene-frames\frame_005s.png
& $ffmpeg -y -ss 8 -i .tmp\mixed-scene-check.mp4 -frames:v 1 .tmp\mixed-scene-frames\frame_008s.png
```

Inspect with the image viewer. Expected:

- character visible as host
- component visible as supporting visual in the same frame
- meme accent appears only as supporting layer
- captions and progress remain unobstructed

- [ ] **Step 7: Commit Task 6**

```powershell
git add docs\SHORTS.md
git commit -m "docs(shorts): document mixed recipes"
```

---

### Task 7: Final Full Verification and Handoff

**Files:**
- No code files unless verification finds a defect.

- [ ] **Step 1: Run Python focused suite**

Run:

```powershell
$env:TMP=(Resolve-Path .tmp\pytest).Path
$env:TEMP=$env:TMP
$env:PYTEST_DEBUG_TEMPROOT=$env:TMP
.\.venv\Scripts\python.exe -m pytest tests\test_short_scene_recipe.py tests\test_synctoon_import.py tests\test_short_character.py tests\test_short_first.py tests\test_short_first_cli.py tests\test_short.py tests\test_shorts_generator.py tests\test_short_verticals.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run Remotion full test suite**

Run:

```powershell
Set-Location remotion
npm.cmd test
Set-Location ..
```

Expected: all Remotion tests pass.

- [ ] **Step 3: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output and exit 0.

- [ ] **Step 4: Confirm commit state**

Run:

```powershell
git status --short
git log --oneline -n 8
```

Expected: only ignored generated files remain unstaged, and new feature commits appear on top.

- [ ] **Step 5: Handoff summary**

Report:

- commit hashes created
- tests run and pass counts
- render artifact path
- visual inspection result
- any remaining known limitations
