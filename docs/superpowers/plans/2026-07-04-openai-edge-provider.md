# OpenAI and Edge TTS Implementation Plan

1. Add failing provider tests for factory selection, text generation, system instructions, JSON parsing, and malformed JSON.
2. Implement `OpenAILLMProvider` minimally against the official Responses API.
3. Declare the OpenAI SDK dependency and export the provider.
4. Change global configuration to `openai` / `gpt-5.4-mini` and `edge`.
5. Run focused tests, then the complete Python test suite and dependency check.
