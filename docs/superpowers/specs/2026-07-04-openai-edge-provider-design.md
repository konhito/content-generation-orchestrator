# OpenAI and Edge TTS Provider Design

## Goal

Run the existing video generation pipeline with the OpenAI Responses API for text/JSON generation and Edge TTS for narration.

## Design

- Add an `OpenAILLMProvider` implementing the existing `LLMProvider` interface.
- Construct the official `OpenAI` client lazily from `OPENAI_API_KEY`.
- Send system instructions separately from the user prompt through `responses.create`.
- Return `response.output_text` for text generation.
- Request JSON output, parse it, and produce a clear error for invalid or empty JSON.
- Preserve the mock and Claude Code implementations.
- Set the repository configuration to `openai` with `gpt-5.4`, and TTS to `edge`.
- Add the OpenAI SDK as a declared project dependency.

## Errors and testing

Missing credentials and SDK/API errors propagate with useful context. Unit tests inject a fake client and never make network calls. Existing provider and audio tests remain green.
