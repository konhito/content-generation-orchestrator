# Shorts Research Aggregator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore live ranked research to short-first generation when `--research` is enabled.

**Architecture:** Add a focused aggregator module modeled on the reference repository but adapted to this project's `httpx`, niche YAML, and `ResearchNote` model. Inject the aggregator into `ShortFirstGenerator` for deterministic tests and preserve local/topic fallback behavior.

**Tech Stack:** Python 3.12, `httpx`, standard-library RSS/XML parsing, pytest

---

### Task 1: Aggregator Core

**Files:**
- Create: `src/short/research_aggregator.py`
- Create: `tests/test_short_research_aggregator.py`

- [ ] Write failing tests for DDG parsing, deduplication, ranking, and graceful source failures.
- [ ] Run `python -m pytest tests/test_short_research_aggregator.py -q` and confirm failures are caused by the missing module.
- [ ] Implement `ResearchAggregator`, `ResearchItem`, DDG parsing, Reddit/RSS acquisition, web-page scraping, optional pytrends, ranking, and logging callbacks.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Short-First Integration

**Files:**
- Modify: `src/short/first.py`
- Modify: `tests/test_short_first.py`

- [ ] Write a failing test proving `research=True` invokes the aggregator and preserves URL/image metadata as `ResearchNote` values.
- [ ] Write a test proving `research=False` performs no live aggregation.
- [ ] Run the focused tests and confirm the live integration test fails for the current placeholder behavior.
- [ ] Add an injectable aggregator factory and merge ranked live notes after local source notes.
- [ ] Add source-count and failure logging through the existing generation logger.
- [ ] Re-run short-first and aggregator tests.

### Task 3: Dependencies and End-to-End Verification

**Files:**
- Modify: `README.md` only if the current command documentation omits `--research` behavior.

- [ ] Run all targeted short tests.
- [ ] Run `short research` with mocked acquisition to verify serialized `research.json` structure.
- [ ] Run a live `short research` command when network access is available; verify at least one real URL or report the exact external blocker.
- [ ] Inspect the final diff for unrelated changes.
