# Short Step-by-Step Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Shorts pipeline run as a clear stage-by-stage flow like the long-form pipeline, while keeping the short-first generator, voiceover, storyboard, and render outputs fully resumable.

**Architecture:** Keep `short generate` as the main entrypoint, but split it into explicit persisted stages: research, script, beats, memes, components, scenes, voiceover, storyboard, timing, and render. Each stage should write its artifact into `short/<variant>/...`, print its output path, and allow the next stage to resume from that artifact rather than recomputing everything. The long-form pipeline already shows this pattern; the Shorts path should adopt the same operational clarity without changing the underlying recipe and rendering logic.

**Tech Stack:** Python CLI, existing `src/short/*` generators, existing voiceover and storyboard serializers, Remotion render pipeline, pytest, Vitest.

---

### Task 1: Add explicit step orchestration helpers for shorts

**Files:**
- Modify: `src/cli/main.py`
- Modify: `src/short/first.py`
- Modify: `src/short/generator.py`
- Test: `tests/test_short_first_cli.py`
- Test: `tests/test_short_first.py`

- [ ] **Step 1: Write the failing test**

```python
def test_short_generate_reports_step_artifacts(tmp_path, capsys):
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)

    result = run_short_generate(
        project="demo",
        topic="Claude fable mode",
        niche="entertainment",
        variant="demo",
        duration=30,
        mock=True,
        projects_dir=tmp_path / "projects",
    )

    assert result == 0
    out = capsys.readouterr().out
    assert "Step 1/9: research" in out
    assert "Step 2/9: script" in out
    assert "Step 3/9: beats" in out
    assert "Step 4/9: memes" in out
    assert "Step 5/9: components" in out
    assert "Step 6/9: scenes" in out
    assert "Step 7/9: voiceover" in out
    assert "Step 8/9: storyboard" in out
    assert "Step 9/9: render" in out
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
pytest tests/test_short_first_cli.py -q
```

Expected: fail because `short generate` still prints one collapsed block instead of explicit step-by-step progress.

- [ ] **Step 3: Write minimal implementation**

```python
def run_short_pipeline(args, project, short_first_result):
    steps = [
        ("research", short_first_result.research_path),
        ("script", short_first_result.short_script_path),
        ("beats", short_first_result.script_beats_path),
        ("memes", short_first_result.meme_plan_path),
        ("components", short_first_result.component_plan_path),
        ("scenes", project.short_dir / args.variant / "scenes"),
        ("voiceover", project.short_dir / args.variant / "voiceover" / "short_voiceover.mp3"),
        ("storyboard", project.short_dir / args.variant / "storyboard" / "shorts_storyboard.json"),
        ("timing", project.short_dir / args.variant / "scenes" / "timing.ts"),
        ("render", project.short_dir / args.variant / "output" / "short.mp4"),
    ]
    for index, (name, artifact_path) in enumerate(steps, start=1):
        print(f"Step {index}/{len(steps)}: {name}")
        print(f"  Artifact: {artifact_path}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
pytest tests/test_short_first_cli.py -q
```

Expected: pass with explicit step output.

- [ ] **Step 5: Commit**

```powershell
git add src/cli/main.py src/short/first.py src/short/generator.py tests/test_short_first_cli.py tests/test_short_first.py
git commit -m "feat(shorts): expose step-by-step pipeline"
```

### Task 2: Add resumable stage commands for shorts

**Files:**
- Modify: `src/cli/main.py`
- Modify: `src/short/first.py`
- Test: `tests/test_short_first_cli.py`

- [ ] **Step 1: Write the failing test**

```python
def test_short_stage_commands_create_expected_artifacts(tmp_path):
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)

    run_short_command("research", project="demo", variant="demo", topic="Claude fable mode", niche="entertainment")
    run_short_command("script", project="demo", variant="demo", mock=True, topic="Claude fable mode", niche="entertainment")
    run_short_command("beats", project="demo", variant="demo", niche="entertainment")
    run_short_command("memes", project="demo", variant="demo", niche="entertainment")
    run_short_command("components", project="demo", variant="demo", niche="entertainment")
    run_short_command("scenes", project="demo", variant="demo")
    run_short_command("voiceover", project="demo", variant="demo", mock=True)
    run_short_command("storyboard", project="demo", variant="demo", mock=True)

    assert (project_dir / "short" / "demo" / "research" / "research.json").exists()
    assert (project_dir / "short" / "demo" / "short_script.json").exists()
    assert (project_dir / "short" / "demo" / "beats" / "script_beats.json").exists()
    assert (project_dir / "short" / "demo" / "memes" / "meme_plan.json").exists()
    assert (project_dir / "short" / "demo" / "components" / "component_plan.json").exists()
    assert (project_dir / "short" / "demo" / "voiceover" / "short_voiceover_manifest.json").exists()
    assert (project_dir / "short" / "demo" / "storyboard" / "shorts_storyboard.json").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
pytest tests/test_short_first_cli.py -q
```

Expected: fail because only the full `short generate` path exists end-to-end.

- [ ] **Step 3: Write minimal implementation**

```python
def cmd_short_research(args):
    ...

def cmd_short_script(args):
    ...

def cmd_short_beats(args):
    ...

def cmd_short_memes(args):
    ...

def cmd_short_components(args):
    ...

def cmd_short_scenes(args):
    ...

def cmd_short_voiceover(args):
    ...

def cmd_short_storyboard(args):
    ...

def cmd_short_timing(args):
    ...

def cmd_short_render(args):
    ...
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
pytest tests/test_short_first_cli.py -q
```

Expected: pass and create the stage artifacts in order.

- [ ] **Step 5: Commit**

```powershell
git add src/cli/main.py tests/test_short_first_cli.py
git commit -m "feat(shorts): add resumable stage commands"
```

### Task 3: Update docs so Shorts reads like the long-form pipeline

**Files:**
- Modify: `docs/SHORTS.md`
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

```python
def test_docs_describe_stepwise_short_pipeline():
    text = Path("docs/SHORTS.md").read_text(encoding="utf-8")
    assert "Step-by-Step Generation" in text
    assert "research" in text
    assert "beats" in text
    assert "memes" in text
    assert "components" in text
    assert "voiceover" in text
    assert "storyboard" in text
    assert "render" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
pytest tests/test_short_first.py -q
```

Expected: fail until docs are updated.

- [ ] **Step 3: Write minimal implementation**

```markdown
### Step-by-Step Short Generation

1. research
2. script
3. beats
4. memes
5. components
6. scenes
7. voiceover
8. storyboard
9. timing
10. render
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
pytest tests/test_short_first.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add docs/SHORTS.md README.md
git commit -m "docs(shorts): document stepwise pipeline"
```

### Task 4: Verify the full end-to-end demo

**Files:**
- No code changes expected

- [ ] **Step 1: Run the full stage flow**

Run:

```powershell
python -m src.cli short research claude-fable --topic "Claude fable mode" --variant demo --niche entertainment
python -m src.cli short script claude-fable --variant demo --mock
python -m src.cli short beats claude-fable --variant demo --niche entertainment
python -m src.cli short memes claude-fable --variant demo --niche entertainment
python -m src.cli short components claude-fable --variant demo --niche entertainment
python -m src.cli short scenes claude-fable --variant demo
python -m src.cli short voiceover claude-fable --variant demo
python -m src.cli short storyboard claude-fable --variant demo
python -m src.cli short timing claude-fable --variant demo
python -m src.cli render claude-fable --short --variant demo
```

- [ ] **Step 2: Confirm artifacts exist**

Expected:

- `short/demo/research/research.json`
- `short/demo/short_script.json`
- `short/demo/beats/script_beats.json`
- `short/demo/memes/meme_plan.json`
- `short/demo/components/component_plan.json`
- `short/demo/scenes/styles.ts`
- `short/demo/voiceover/short_voiceover.mp3`
- `short/demo/storyboard/shorts_storyboard.json`
- `short/demo/scenes/timing.ts`
- `short/demo/output/short.mp4`

- [ ] **Step 3: Commit**

```powershell
git add src/cli/main.py src/short/first.py src/short/generator.py docs/SHORTS.md README.md tests/test_short_first_cli.py tests/test_short_first.py
git commit -m "feat(shorts): make pipeline fully stepwise"
```

### Task 5: Final verification

**Files:**
- No code changes expected

- [ ] **Step 1: Run targeted unit tests**

Run:

```powershell
pytest tests/test_short_first.py tests/test_short_first_cli.py tests/test_short_scene_recipe.py tests/test_short_character.py -q
```

- [ ] **Step 2: Run Remotion tests**

Run:

```powershell
cd remotion
npm.cmd test
```

- [ ] **Step 3: Render a demo**

Run:

```powershell
python -m src.cli render claude-fable --short --variant demo
```

- [ ] **Step 4: Inspect the output**

Expected: final MP4 exists under `projects/claude-fable/short/demo/output/short.mp4` and plays with the stepwise-generated voiceover, storyboard, and mixed scenes.

