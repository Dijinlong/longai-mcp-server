---
name: longai-gateway
description: Use the LONG AI MCP tools when the user asks which models a gateway or API key serves, wants one chat completion run through an OpenAI-compatible endpoint, or suspects a relay is dropping fields, usage or streaming markers.
---

# LONG AI Gateway

Three tools wrap a plain OpenAI-compatible HTTP endpoint. No SDK, no vendor lock-in: point `LONGAI_BASE_URL` at any `/v1` endpoint and the same tools work.

## When to use

- **`list_models`** — the user is unsure a model id exists on their key, or asks "what can I call with this key". Always run this before `chat` if the model name was guessed.
- **`chat`** — the user wants a single non-streaming completion and needs to see token usage. Pass OpenAI-format `messages`.
- **`check_compatibility`** — the user says a relay "works but something is off": tools calls get dropped, streaming ends without `[DONE]`, an unknown model answers 200 with an `error` body, or billed tokens do not match.

## Rules

- Never invent a model id. If `list_models` does not list it, say so and offer the closest ids.
- Always report the `usage` object returned by `chat`; it is the billing evidence.
- When `check_compatibility` returns FAIL, quote the failing line verbatim and name which of the four checks broke.
- Keys come from the environment (`LONGAI_API_KEY`). Never echo, log or store the key.

## Output shape

`check_compatibility` prints four numbered lines and a PASS/FAIL verdict:

```text
1. GET /models            200  182ms, models=77
2. POST chat (no stream)  200  940ms  usage={'total_tokens': 15}
3. POST chat (stream)     200  310ms  [DONE]=yes
4. POST unknown model     404   96ms  错误形状正常
----------------------------------------------
PASS
```
