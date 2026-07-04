# Short-First Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Shorts-first path that generates 45-55 second short scripts, research bundles, niche guidance, and meme plans without changing the long-video pipeline.

**Architecture:** Add focused modules under `src/short/` and extend the existing `short generate` CLI parser. The new path writes only into `projects/<project>/short/<variant>/` and reuses existing short voiceover/storyboard/render code after producing `short_script.json`.

**Tech Stack:** Python, argparse, Pydantic models, existing `LLMProvider`, existing Edge TTS/short pipeline, pytest.

---

### Task 1: Short-first models and builder

**Files:**
- Create: `src/short/first.py`
- Modify: `src/short/__init__.py`
- Test: `tests/test_short_first.py`

- [ ] Add tests for research bundle creation, niche fallback, and conversion to `ShortScript`.
- [ ] Run `pytest tests/test_short_first.py -v` and verify the tests fail because `src.short.first` does not exist.
- [ ] Implement `ResearchNote`, `NicheProfile`, `MemeMoment`, `ShortFirstResult`, and `ShortFirstGenerator`.
- [ ] Run `pytest tests/test_short_first.py -v` and verify the tests pass.

### Task 2: CLI integration

**Files:**
- Modify: `src/cli/main.py`
- Test: `tests/test_short_first_cli.py`

- [ ] Add parser tests showing `short generate` accepts `--topic`, `--source`, `--niche`, and `--research`.
- [ ] Run `pytest tests/test_short_first_cli.py -v` and verify the tests fail because the parser args do not exist.
- [ ] Extend `short generate` and `short script` parser options.
- [ ] Route topic/source/research calls into `ShortFirstGenerator` before existing short voiceover/storyboard flow.
- [ ] Run `pytest tests/test_short_first_cli.py tests/test_short_first.py -v` and verify both pass.

### Task 3: Targeted regression

**Files:**
- Test: `tests/test_cli.py`
- Test: `tests/test_short.py`

- [ ] Run existing CLI and short tests.
- [ ] Fix only regressions caused by the new short-first path.
- [ ] Confirm `video-explainer generate <project>` remains wired to `cmd_generate`.
