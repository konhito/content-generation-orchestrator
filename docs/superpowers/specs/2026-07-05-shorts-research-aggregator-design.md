# Shorts Research Aggregator Design

## Goal

Restore live multi-source research for short-first generation using the proven behavior from `D:\youtube-shorts-pipeline`.

## Behavior

When `--research` is enabled, the short pipeline gathers ranked results concurrently from Reddit RSS, configured RSS feeds, DuckDuckGo, scraped top web pages, and optional Google Trends. Results are deduplicated and converted to the existing `ResearchNote` schema, preserving URLs, scores, source names, image URLs, and source metadata.

Local `--source` files remain highest-confidence notes. Live-source failures are logged and non-fatal. If every live source fails, generation continues with local sources or the existing topic fallback. Without `--research`, no network research is attempted.

## Integration

`src/short/research_aggregator.py` owns acquisition, parsing, ranking, and deduplication. `ShortFirstGenerator.build_research_bundle()` invokes it through an injectable aggregator factory, making offline tests deterministic. The resulting `ResearchBundle` already flows into the short script prompt and `research.json`.

## Dependencies

Use the existing `httpx` dependency for HTTP. RSS parsing uses the standard library XML parser, avoiding a mandatory `feedparser` dependency. Pytrends remains optional and is skipped with a clear log when unavailable.

## Verification

Tests cover DuckDuckGo parsing, source ranking/deduplication, metadata preservation, live-research integration, disabled-research behavior, and graceful all-source failure.
