# Short-First Pipeline Design

## Goal

Add a Shorts-first path to `video-explainer` that can create a 45-55 second vertical short from either a topic/research bundle or local source documents, while keeping the existing long-video `generate` pipeline unchanged.

## Architecture

The existing long flow remains `video-explainer generate <project>`. Shorts uses the existing `video-explainer short ...` command family and adds a short-first intake path when the user passes `--topic`, `--source`, or `--research`.

The new short-first layer lives under `src/short/` and writes only to `projects/<project>/short/<variant>/`. It reuses the existing OpenAI LLM provider, Edge TTS voiceover, short storyboard model, and Remotion `ShortsPlayer` renderer.

## Flow

1. Intake accepts a project id, optional topic, optional source files, niche, variant, and target duration.
2. Research bundle generation normalizes topic/source material into structured research notes.
3. Niche profile loading applies tone, hook, pacing, caption, and meme-density guidance.
4. Script generation asks the LLM for a 45-55 second short script with a hook, beats, CTA, and structured meme moments.
5. Script and meme-plan files are written under the short variant directory.
6. Existing short voiceover, storyboard, scene, and render steps consume the generated `short_script.json`.

## Data boundaries

Short-first files:

- `short/<variant>/research/research.json`
- `short/<variant>/short_script.json`
- `short/<variant>/short_script.md`
- `short/<variant>/memes/meme_plan.json`
- `short/<variant>/storyboard/shorts_storyboard.json`
- `short/<variant>/voiceover/`
- `short/<variant>/output/`

Long-video files such as `plan/`, `script/`, `narration/`, `scenes/`, `storyboard/`, and `output/final.mp4` are not modified by the short-first path.

## Niche and meme system

Niche profiles are small YAML files or built-in defaults. They control tone, hook style, pacing, caption style, CTA style, and meme density.

The meme system produces structured JSON. It does not directly produce JSX. Remotion generation can later translate meme moments into known visual patterns.

## Testing

Tests cover:

- research bundle creation from topic and source files;
- niche default/fallback behavior;
- LLM output conversion into `ShortScript` plus `meme_plan.json`;
- CLI parser support for `short generate --topic/--source/--niche/--research`;
- confirmation that the long `generate` command is not used or modified by short-first behavior.
