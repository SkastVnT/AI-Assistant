---
name: observability-log-hygiene
description: "Improve diagnostics for the core chatbot and tools without adding noisy or unsafe logging. Use when: adding or reviewing log statements, debugging silent failures, auditing error handling, checking for secret leakage in logs, improving startup or provider failure signals, or deciding what log level to use for a new code path."
---

# Observability & Log Hygiene

## When to use this skill

- Adding a `logger.*()` call to new or existing code.
- Debugging a silent failure (bare `except:`, swallowed error, missing log).
- Reviewing error handling in routes, tools, or provider calls.
- Checking whether logs might expose secrets or sensitive user data.
- Improving startup diagnostics or config-missing warnings.
- Deciding what log level and tag to use for a new code path.
- Assessing whether a logging change affects local debugging, CI, or both.

## Do not use for

- Image pipeline or ComfyUI logging — separate stacks.
- Adding structured logging infrastructure (JSON formatters, log aggregation) — out of scope unless explicitly requested.
- Changing log levels on werkzeug or third-party library loggers without justification.

---

## Why logging changes matter

Poor logging creates three failure modes:

1. **Silent failures** — code catches an exception and swallows it. The feature breaks but no signal reaches the developer. The chatbot returns a degraded response and nobody knows why.
2. **Noisy logs** — every request dumps full payloads, base64 images, or API responses. Useful signals drown in noise. Log storage costs grow. In CI, test output becomes unreadable.
3. **Unsafe logs** — API keys, auth tokens, or full user messages appear in log output. A log file leak becomes a credential leak.

Good logging is **diagnostic** — it tells you what happened, where, and why, without exposing secrets or drowning real signals.

---

## Current logging setup

### Logger initialization (two sites — known duplication)

| File | Line | What it does |
|------|------|-------------|
| `services/chatbot/core/extensions.py` | L13 | `logging.basicConfig(level=INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')` |
| `services/chatbot/chatbot_main.py` | L94 | Identical `logging.basicConfig(...)` call |

Both files also set `werkzeug` logger to INFO. Python's `basicConfig()` only applies on the first call, so whichever module loads first wins. This is fragile but currently harmless because both configs are identical. **Do not add a third `basicConfig()` call.**

### Logger pattern

All modules use `logger = logging.getLogger(__name__)`. This is correct — it gives each module a named logger under the root. **Continue this pattern.**

### Existing sanitizer

`chatbot_main.py` L101 defines `sanitize_for_log(value)` — strips CR/LF to prevent log injection. **Use this for any user-controlled string in log messages.**

### HTTP request/response logging

`core/http_logging.py` provides `setup_http_logging(app)` which logs all requests/responses with truncation (500 chars for bodies). Request bodies are truncated; base64 images are replaced with `[BASE64_IMAGE...]`. This is good — do not weaken these truncation guards.

---

## Log classification

Every log statement should belong to one of these categories. Use the corresponding tag prefix.

### Category 1: Startup / Init — `[Startup]` or `[Init]`

Logged once during service boot. Tells you what loaded, what's missing, what's degraded.

**What to log:**
- Service version / mode (Flask monolith)
- Loaded env file path
- Database connection status (MongoDB enabled/disabled)
- Optional module availability (MCP client, HTTP logging, etc.)
- Missing env vars that cause degraded mode (not the values — just the names)

**Current coverage:** Good in `extensions.py` (10+ startup logs). Adequate in `chatbot_main.py`.

**Gap:** MCP server (`services/mcp-server/server.py`) uses `print()` instead of `logger`. These should be `logger.info()` calls if the server is ever run in a context where stdout is captured.

### Category 2: Route / Request — `[Stream]`, `[Chat]`, `[API]`

Logged per-request. Tells you what came in and what went out.

**What to log:**
- Request received (route, method, request_id)
- Key parameters (model, thinking_mode, tool count — NOT full message text)
- Response status (200, 400, 500)
- Elapsed time for the request

**What to never log:**
- Full user message body (truncate to max 60 chars if needed for debugging)
- Full response body
- Base64 image data
- Session tokens or auth headers

**Current coverage:** `stream.py` logs `[SSE:{request_id}] Incoming stream request` at L228. HTTP logging middleware handles request/response pairs. Good.

**Gap:** No timing log at stream completion — elapsed time is computed for the SSE `complete` event payload but not logged server-side.

### Category 3: Provider / Model — `[Provider]`, `[Vision]`, `[Model]`

Logged when calling an external LLM API. Tells you which provider was called, how long it took, and whether it failed.

**What to log:**
- Provider + model selected for this request
- API call start (DEBUG level — too noisy for INFO in production)
- API call completion with timing
- API errors with status code and error type (NOT full error body from provider)
- Fallback events (model X failed → trying model Y)

**Current coverage:** `chatbot_v2.py` logs `[Vision]` routing (L347, L350) and streaming errors (L393). **Critical gap: no log when a provider is selected or when an API call starts/ends.** This makes provider failures hard to diagnose.

### Category 4: Tool / Search — `[GOOGLE SEARCH]`, `[SERPAPI:*]`, `[ReverseImg]`, `[SAUCENAO]`

Logged when a tool function executes. Tells you what was searched, whether it succeeded, and how long it took.

**What to log:**
- Tool invoked (tool name, truncated query — max 80 chars)
- Tool result status (success, no results, error)
- Tool timing (important for search cascade debugging)
- Fallback cascade position (which engine in the cascade, did it try next?)

**Current coverage:** Good in `tools.py` — every tool function logs invocation and errors. Tags are consistent (`[GOOGLE SEARCH]`, `[SERPAPI:ENGINE]`, `[ReverseImg]`).

**Gap:** No timing information logged. No log when auto-search triggers in `stream.py` _why_ it triggered (which keyword matched).

### Category 5: MCP — `[MCP]`

Logged for MCP context injection and tool invocation.

**What to log:**
- MCP context injection (files selected, injection success/failure)
- MCP tool invocation (tool name, success/failure)

**Current coverage:** `stream.py` L303 logs MCP injection errors. **Gap:** MCP server (`server.py`) has zero logging — only `print()` calls for startup banner.

### Category 6: Validation / Config — `[Config]`, `[Validation]`

Logged when input validation fails or configuration is missing.

**What to log:**
- Missing API keys at startup (key name only, never the value)
- Invalid request parameters (what field, what's wrong — not the full payload)
- Rate limit hits
- Quota exceeded events

**Current coverage:** `config.py` logs missing keys at import time via `extensions.py`. `stream.py` validates images (L269–278) silently — invalid images are dropped without logging.

### Category 7: Thinking — `[Thinking]`

Logged during thinking mode processing.

**What to log:**
- Thinking mode activated (which mode, for which request)
- Thinking step count generated
- Multi-thinking round count
- Thinking duration

**Current coverage:** **None.** `thinking_generator.py` defines a logger (L14) but never calls it. This is the biggest diagnostic gap in the thinking pipeline.

---

## What must NEVER be logged

| Data type | Risk | Mitigation |
|-----------|------|-----------|
| API keys / tokens | Credential leak | Read from env, never log. Check that `config.py` values don't appear in any log call. |
| Full user messages | Privacy | Truncate to 60 chars max. Use `message[:60]` or `sanitize_for_log()`. |
| Base64 image data | Log size explosion + privacy | Replace with `[BASE64_IMAGE len={n}]` in logs. |
| Session IDs / auth tokens | Session hijack | Log request_id (UUID[:12]) instead. |
| Full API response bodies | Size + potential PII | Log status code and error type only. |
| Passwords / credentials | Credential leak | Never log request bodies for auth routes. |
| Exception tracebacks at INFO | Noise | Use `logger.debug(traceback.format_exc())` for full traces, `logger.error(f"...")` for the summary. |

---

## Log level guide

| Level | When to use | Example |
|-------|-------------|---------|
| `DEBUG` | Detailed diagnostic info, too noisy for production | Full traceback, API response parsing details, chunk-by-chunk streaming |
| `INFO` | Normal operations worth noting | Request received, tool invoked, provider selected, startup complete |
| `WARNING` | Something unexpected but recoverable | Missing optional config, search fallback triggered, deprecated code path |
| `ERROR` | Something failed and affected the user | API call failed, tool returned error, database write failed |
| `CRITICAL` | Currently unused — reserve for service-down scenarios | (not used in codebase) |

**Rule:** `logger.exception()` is preferred over `logger.error()` inside `except` blocks when you want the traceback. Currently the codebase never uses `logger.exception()` — it always uses `logger.error(f"...")` plus a separate `logger.debug(traceback.format_exc())`. Both patterns are acceptable; pick one per file and be consistent.

---

## Tag prefix conventions

Use the existing tag style: `[TAG]` at the start of the message.

### Established tags (do not change)

| Tag | Used in | Covers |
|-----|---------|--------|
| `[SSE:{request_id}]` | `stream.py` | Stream lifecycle |
| `[Stream]` | `stream.py` | Tool dispatch within streaming |
| `[STREAM]` | `stream.py` | Image attachment info |
| `[WebSearch]`, `[WebSearch:SerpAPI]` | `stream.py` | Auto web search |
| `[GOOGLE SEARCH]` | `tools.py` | Google CSE tool |
| `[GITHUB SEARCH]` | `tools.py` | GitHub search tool |
| `[SAUCENAO]` | `tools.py` | SauceNAO tool |
| `[SERPAPI:ENGINE]` | `tools.py` | SerpAPI tools (GOOGLE_LENS, YANDEX, etc.) |
| `[ReverseImg]` | `tools.py` | Reverse image search |
| `[Vision]` | `chatbot_v2.py` | Vision model routing |
| `[MCP]` | `stream.py` | MCP context injection |
| `[Auth]` | `auth.py` | Authentication |
| `[image_gen]` | `image_gen.py` | Image generation |
| `[API Error]` | `error_handler.py` | Unhandled API errors |
| `[HTTP Logging]` | `http_logging.py` | Request/response logging errors |
| `[HTTPTracker]` | `http_logging.py` | External call tracking |
| `[Retry]` | various | Retry logic |

### Tag for new code

When adding logging to a new area, follow this pattern:
```python
logger.info(f"[NewTag] Brief description: {safe_value}")
```

Capitalize the tag. Keep descriptions under 120 chars total. Truncate user data.

---

## Known gaps (current state)

| Area | File | Issue | Impact |
|------|------|-------|--------|
| Provider selection | `chatbot_v2.py` | No log when model/provider is selected for a request | Can't trace which provider handled a given request |
| Thinking mode | `thinking_generator.py` | Logger defined (L14) but never used | Can't diagnose thinking step generation failures |
| MCP server | `mcp-server/server.py` | Uses `print()` only, no `logger` | Startup messages not captured in logging infrastructure |
| Silent DB writes | `routes/main.py` | Background DB saves logged at DEBUG only | Production DB failures invisible at default INFO level |
| Bare `except:` blocks | `main.py` L136,142,147,152; `stream.py` L241; `images.py` L405 | No exception type, no log in some cases | Failures swallowed silently |
| Stream completion timing | `stream.py` | Elapsed time computed but not logged server-side | Can't correlate server timing with client-reported latency |
| Auto-search trigger reason | `stream.py` | Logs that auto-search triggered but not _why_ (which keyword matched) | Hard to debug false-positive/negative auto-search |
| Image validation drops | `stream.py` L269–278 | Invalid images silently dropped | User sends broken image, gets no feedback about why it was ignored |

---

## Error handling patterns

### Preferred pattern

```python
try:
    result = external_api_call(...)
except SpecificException as e:
    logger.error(f"[Tag] Brief description: {type(e).__name__}: {e}")
    logger.debug(traceback.format_exc())
    # Return error to caller or emit SSE error event
```

### Anti-patterns to avoid

```python
# ❌ Bare except — hides the exception type
except:
    pass

# ❌ Logging full payload
logger.error(f"API failed: {full_response_body}")

# ❌ Logging user message verbatim
logger.info(f"User asked: {message}")

# ❌ Logging at wrong level
logger.info(f"Error: {e}")  # Errors should use logger.error()

# ❌ Swallowing exception without any log
except Exception:
    return default_value
```

### When fixing bare `except:` blocks

Replace with:
```python
except Exception as e:
    logger.warning(f"[Tag] Non-critical failure: {type(e).__name__}: {e}")
```

Or if the failure is critical to the request:
```python
except Exception as e:
    logger.error(f"[Tag] Critical failure: {type(e).__name__}: {e}")
    raise  # or return error response
```

---

## Monitor section

When reviewing or adding logging, check these signal paths:

### Startup signals

| Signal | Where | Current State |
|--------|-------|---------------|
| Service mode (Flask monolith) | `run.py`, `chatbot_main.py` | ✅ Logged |
| Env file loaded | `shared_env.py` | ✅ Logged |
| MongoDB connected | `extensions.py` | ✅ Logged |
| Missing API keys | `extensions.py`, `config.py` | ✅ Logged (key names only) |
| HTTP logging enabled | `chatbot_main.py` | ✅ Logged |
| MCP server ready | `mcp-server/server.py` | ⚠️ `print()` only |

### Per-request signals

| Signal | Where | Current State |
|--------|-------|---------------|
| Request received | `stream.py` L228 | ✅ Logged with request_id |
| Model/provider selected | `chatbot_v2.py` | ❌ Not logged |
| Tool dispatched | `stream.py` L347+ | ✅ Logged per tool |
| Auto-search triggered | `stream.py` L342 | ⚠️ Logged but no reason |
| Thinking mode activated | `thinking_generator.py` | ❌ Not logged |
| Stream completed | `stream.py` | ⚠️ No server-side timing log |
| Error returned | `stream.py`, `error_handler.py` | ✅ Logged |

### Failure signals

| Signal | Where | Current State |
|--------|-------|---------------|
| Provider API error | `chatbot_v2.py` L393 | ✅ Logged |
| Tool function error | `tools.py` (all functions) | ✅ Logged with tags |
| MCP injection error | `stream.py` L303 | ✅ Logged |
| DB write failure | `routes/main.py` | ⚠️ DEBUG only |
| Image validation failure | `stream.py` L269–278 | ❌ Silent drop |
| Rate limit hit | `image_gen.py` | ✅ Logged |

---

## Local vs CI debugging impact

When adding or changing logging, note which environment it affects:

| Change Type | Local Impact | CI Impact | Note |
|-------------|-------------|-----------|------|
| Add `logger.info()` | Visible in terminal | Visible in pytest `-v` output | Keep messages concise — CI logs are truncated |
| Add `logger.debug()` | Not visible by default (INFO level) | Not visible in CI (INFO level) | Only useful if developer sets `--log-level=DEBUG` |
| Add `logger.error()` | Visible in terminal | Visible in CI, may cause test failure if assertions check stderr | Prefer raising or returning error over just logging |
| Add `print()` | Visible in terminal | Captured by pytest but mixed with test output | **Do not use `print()` in chatbot service code** — use `logger` |
| Change log format | Breaks any log-parsing scripts | May break CI grep patterns | Avoid unless explicitly requested |
| Add log file output | Creates file in `logs/` | No effect (CI has no `logs/` dir persistence) | Guard with `os.path.exists()` |

**Rule:** If a logging change is only useful for local debugging, use `DEBUG` level. If it's useful for diagnosing CI failures, use `INFO` or `WARNING`.

---

## Safe-logging checklist

Before merging any logging change:

- [ ] **No secrets in log output** — API keys, tokens, passwords never appear in any `logger.*()` call
- [ ] **User messages truncated** — max 60 chars in log, use `message[:60]` or `sanitize_for_log()`
- [ ] **Base64 data replaced** — never log raw base64; use `[BASE64_IMAGE len={n}]`
- [ ] **Correct log level** — errors use `error()`, normal ops use `info()`, verbose detail uses `debug()`
- [ ] **Tag prefix present** — every log message starts with `[Tag]` matching the established conventions
- [ ] **No bare `except:`** — all exception handlers specify the exception type and log before swallowing
- [ ] **`sanitize_for_log()` used for user input** — prevents log injection via CR/LF in user strings
- [ ] **No `print()` in service code** — use `logger.*()` instead (MCP server is the one known exception pending migration)
- [ ] **Timing logged where useful** — provider calls, tool invocations, stream duration
- [ ] **Local vs CI impact noted** — comment in PR whether the change helps local debugging, CI debugging, or both

---

## File reference

| File | Purpose | Logging Status |
|------|---------|----------------|
| `services/chatbot/core/extensions.py` | Logger setup, startup logs | ✅ Primary `basicConfig` |
| `services/chatbot/chatbot_main.py` | Flask entry, duplicate `basicConfig`, `sanitize_for_log()` | ✅ Duplicate setup (harmless) |
| `services/chatbot/core/http_logging.py` | Request/response logging middleware | ✅ Truncation, emoji prefixes |
| `services/chatbot/core/error_handler.py` | Centralized error handling | ✅ `[API Error]` tag, `classify_error()` |
| `services/chatbot/core/tools.py` | Tool function logging | ✅ All tools have tags |
| `services/chatbot/core/chatbot_v2.py` | Model routing, streaming | ⚠️ Minimal — no provider selection log |
| `services/chatbot/core/thinking_generator.py` | Thinking step generation | ❌ Logger defined, never used |
| `services/chatbot/routes/stream.py` | SSE streaming, tool dispatch | ✅ Good coverage, minor gaps |
| `services/chatbot/routes/main.py` | Legacy routes | ⚠️ Bare `except:` blocks (L136–152) |
| `services/chatbot/routes/conversations.py` | Conversation CRUD | ⚠️ Generic error messages |
| `services/chatbot/routes/image_gen.py` | Image generation | ✅ `[image_gen]` tag |
| `services/chatbot/routes/memory.py` | Memory CRUD | ⚠️ Minimal logging |
| `services/chatbot/routes/images.py` | Image storage | ⚠️ Bare `except:` at L405 |
| `services/mcp-server/server.py` | MCP tool server | ❌ `print()` only, no logger |
| `services/chatbot/core/config.py` | Config constants | ✅ Reads from env (no logging itself) |
| `.github/workflows/tests.yml` | CI test runner | Plain `pytest -v` output |
| `.github/workflows/security-scan.yml` | Security scanning | Bandit JSON report as artifact |

---

## Related skills

- **shared-env-contract** — missing env vars that should produce warnings
- **tool-response-contract** — error shapes that logging should capture
- **provider-env-matrix** — provider failures and fallback chains
- **service-health-check-audit** — startup signals and health endpoints
- **test-impact-mapper** — which tests to run after logging changes
