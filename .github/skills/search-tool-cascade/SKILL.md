---
name: search-tool-cascade
description: "Guide changes to chatbot search tools, reverse-image flows, fallback logic, and auto-trigger behavior. Use when: adding or modifying a search tool, changing fallback order, editing auto-search keyword lists, wiring a new tool button in the UI, changing response formatting for search results, debugging a tool that stopped returning results, or reviewing search cascade behavior."
---

# Search Tool Cascade

## When to use this skill

- Adding, renaming, or removing a search tool function.
- Changing the fallback order for web search or reverse image.
- Editing auto-trigger keyword lists that control when web search fires automatically.
- Wiring a new tool button in the UI or renaming an existing tool ID.
- Changing the response format of search results (markdown shape, keys, injection pattern).
- Debugging a search tool that silently stopped working.
- Reviewing whether a change to one tool breaks the cascade for another.

Scope: core chatbot only. Do not touch image pipeline, Stable Diffusion, or ComfyUI for search tool work.

---

## Request path — how a search tool call flows

```
1. UI TRIGGER
   User clicks tool button (e.g. "Web Search")
     → toolBindings maps button ID to tool string ID
     → tool ID added to activeTools Set (JS)

2. API CALL
   User sends message
     → api-service.js POST /chat/stream
       body: { message, model, tools: ["google-search"], ... }

3. ROUTE HANDLER
   routes/stream.py receives request
     → parses tools from JSON body
     → checks _needs_web_search(message, tools)
     → dispatches to tool-specific handler block

4. TOOL EXECUTION
   Handler calls function from core/tools.py
     → function calls external API (SerpAPI, Google CSE, SauceNAO, etc.)
     → returns formatted markdown string (or structured dict)

5. CONTEXT INJECTION
   Result appended to message:
     "{original_message}\n\n---\n{search_results}\n---\nHãy trả lời..."

6. LLM PROCESSING
   Modified message → ChatbotAgent.chat_stream() → provider API

7. STREAMING
   Response streamed via SSE → UI renders
```

---

## Tool ID registry

These are the **exact string IDs** that flow from UI to backend. A mismatch on either side silently disables the tool.

| UI button | HTML element ID | Tool string ID | Backend handler location | Function called |
|---|---|---|---|---|
| Web Search | `googleSearchBtn` | `google-search` | `stream.py` → `_needs_web_search()` + `_run_web_search()` | `serpapi_web_search()` → CSE fallback |
| Lens | `googleLensBtn` | `serpapi-reverse-image` | `stream.py` → `if 'serpapi-reverse-image' in tools` | `serpapi_reverse_image()` |
| Bing | `serpapiBingBtn` | `serpapi-bing` | `stream.py` → `if 'serpapi-bing' in tools` | `_run_web_search(engine='bing')` |
| Baidu | `serpapiBaiduBtn` | `serpapi-baidu` | `stream.py` → `if 'serpapi-baidu' in tools` | `_run_web_search(engine='baidu')` |
| Img Search | `serpapiImagesBtn` | `serpapi-images` | `stream.py` → `if 'serpapi-images' in tools` | `serpapi_image_search()` |
| SauceNAO | `saucenaoBtn` | `saucenao` | `stream.py` → `if 'saucenao' in tools` | `saucenao_search_tool()` |

JS binding in `templates/index.html`:
```javascript
const toolBindings = [
    { id: 'googleSearchBtn', tool: 'google-search' },
    { id: 'saucenaoBtn', tool: 'saucenao' },
    { id: 'googleLensBtn', tool: 'serpapi-reverse-image' },
    { id: 'serpapiBingBtn', tool: 'serpapi-bing' },
    { id: 'serpapiBaiduBtn', tool: 'serpapi-baidu' },
    { id: 'serpapiImagesBtn', tool: 'serpapi-images' },
];
```

**Critical**: If you rename a tool ID in JS, you must rename it in `stream.py` too. If you rename it in `stream.py`, you must rename it in `index.html` too. There is no central registry — the string must match exactly on both sides.

---

## Fallback reasoning

### Web search fallback chain

```
_run_web_search(query, engine="google")
  │
  ├─ Step 1: SerpAPI
  │    API: https://serpapi.com/search.json
  │    Key: SERPAPI_API_KEY
  │    Engines: google (default), bing, baidu
  │    Timeout: 20s
  │    → Success? Return formatted markdown
  │    → Fail/timeout/no key? Fall through
  │
  └─ Step 2: Google Custom Search Engine (CSE)
       API: https://www.googleapis.com/customsearch/v1
       Keys: GOOGLE_SEARCH_API_KEY_1, then GOOGLE_SEARCH_API_KEY_2
       CSE ID: GOOGLE_CSE_ID
       Timeout: 15s, retry: 2x with 0.5s backoff
       → HTTP 429/403? Try next key
       → Both keys fail? Return ""
```

**Why this order matters**: SerpAPI is more reliable and supports multiple engines. CSE is free-tier with quota limits. Reversing this order would exhaust CSE quota on routine searches.

### Reverse image fallback chain

```
serpapi_reverse_image(image_url)
  │
  ├─ Step 1: Google Lens
  │    Engine: google_lens
  │    Param: url=image_url
  │    Reads: visual_matches[]
  │    Timeout: 25s
  │    → Has matches? Return formatted
  │    → No matches or error? Fall through
  │
  ├─ Step 2: Google Reverse Image
  │    Engine: google_reverse_image
  │    Param: image_url=image_url
  │    Reads: knowledge_graph{} + image_results[] / inline_images[]
  │    Timeout: 25s
  │    → Has results? Return formatted
  │    → Fail? Fall through
  │
  └─ Step 3: Yandex Images
       Engine: yandex_images
       Param: url=image_url
       Reads: images_results[]
       Timeout: 25s
       → Has results? Return formatted
       → All fail? Return "No results" message
```

**Why this order matters**: Lens gives the best visual matches for real-world objects. Google Reverse adds knowledge graph context. Yandex covers non-English sources. Moving Yandex first would miss knowledge graph data.

### Multi-source reverse image (structured)

```
reverse_image_search(image_data_url, image_url)
  │
  ├─ Resolve URL (upload to ImgBB if only base64 data)
  ├─ SauceNAO        → sources[] (anime/art, with similarity %)
  ├─ Google Lens      → sources[] (real-world) + knowledge graph
  ├─ Google Reverse   → similar[] (only if sources < 3)
  └─ Yandex           → similar[] (only if sources < 3)
```

This function runs engines **additively** (not sequential fallback). Later engines are skipped only when enough sources already exist.

---

## Auto-trigger logic

Web search fires automatically when the user's message matches realtime patterns, even without an explicit tool button click.

**Decision function**: `_needs_web_search(message, tools)` in `routes/stream.py`

```
1. Is "google-search" or "deep-research" in tools?  → YES, search
2. Does message contain a _SEARCH_KEYWORDS pattern? → YES, search
3. Does message contain a _REALTIME_PATTERNS pattern? → YES, search
4. None match? → NO search
```

**Keyword lists** (Vietnamese + English):

- `_SEARCH_KEYWORDS`: tìm, search, tra cứu, look up, google, find, check…
- `_REALTIME_PATTERNS_VI`: giá, tỷ giá, thời tiết, tin tức, hôm nay, bitcoin, vàng, chứng khoán…
- `_REALTIME_PATTERNS_EN`: price, weather, news, latest, today, stock, bitcoin, crypto, gold price…

**Auto reverse-image trigger** (separate from web search):

When images are attached AND message matches `_IMAGE_SEARCH_PATTERNS` (tìm nguồn, reverse image, find source, where is this…), `reverse_image_search()` is called automatically without any tool button.

---

## Response shapes

### String-returning functions (injected into message context)

| Function | Format |
|---|---|
| `_run_web_search()` | `🔍 **{engine} Search — Kết quả thực tế:**\n\n**Title**\nSnippet\n🔗 Link` |
| `serpapi_reverse_image()` | `🔍 **Google Lens — Visual Matches** (N kết quả):\n**#1** ...` |
| `saucenao_search_tool()` | `**#1** — 95.2% tương đồng\n📌 **Title**\n🎨 Tác giả: Author` |
| `serpapi_image_search()` | `🖼️ **google_images_light — 'query'** (N):\n**#1** Title (source)` |
| `google_search_tool()` | `📌 **Title**\nSnippet\n🔗 Link` (CSE standalone) |

All string results are injected the same way:
```python
message = f"{message}\n\n---\n{search_results}\n---\nHãy trả lời dựa trên dữ liệu..."
```

### Dict-returning function

`reverse_image_search()` returns:
```python
{
    "sources": [{"title", "author", "url", "thumbnail", "similarity", "source_engine"}, ...],
    "similar": [{"title", "author", "url", "thumbnail", "similarity", "source_engine"}, ...],
    "knowledge": str | None,
    "summary": str  # Markdown formatted
}
```

The `summary` field is what gets injected into the message context.

---

## Touch map

### Files that implement search logic

| File | What it owns |
|---|---|
| `services/chatbot/core/tools.py` | All tool functions: google_search_tool, serpapi_web_search, serpapi_reverse_image, serpapi_image_search, saucenao_search_tool, reverse_image_search, github_search_tool |
| `services/chatbot/routes/stream.py` | `_needs_web_search()`, `_run_web_search()`, keyword lists, tool dispatch blocks, context injection |
| `services/chatbot/core/config.py` | API key references: SERPAPI_API_KEY, GOOGLE_SEARCH_API_KEY_1/2, GOOGLE_CSE_ID, SAUCENAO_API_KEY, GITHUB_TOKEN |

### Files that wire tools to the UI

| File | What it owns |
|---|---|
| `services/chatbot/templates/index.html` | Tool button HTML, `toolBindings` array mapping button IDs to tool string IDs, `activeTools` Set |
| `services/chatbot/static/js/modules/api-service.js` | `sendStreamMessage()` — includes `tools` array in POST body |
| `services/chatbot/static/js/main.js` | `getActiveTools()` helper, message send flow |

### Files that document search behavior

| File | What it owns |
|---|---|
| `README.md` | Search tools table, search cascade description |
| `.github/copilot-instructions.md` | Search tool cascade summary |
| `.claude/skills/repo-guidelines/AGENTS.md` | Search tool cascade in operational rules |

---

## Verification map

After any search-tool change, verify each layer that could be affected:

| Layer | What to verify | How |
|---|---|---|
| **UI trigger** | Tool button exists, has correct HTML ID | Inspect `templates/index.html` for the button element |
| **Tool binding** | `toolBindings` maps button ID to correct tool string ID | Check JS in `index.html` |
| **API transport** | `api-service.js` includes `tools` in POST body | Read `sendStreamMessage()` in `api-service.js` |
| **Route dispatch** | `stream.py` has a handler block for the tool string ID | Search `if 'tool-id' in tools` in `stream.py` |
| **Auto-trigger** | Keyword lists match expected triggers, `_needs_web_search()` returns correct boolean | Review patterns in `stream.py` |
| **Tool function** | Function exists in `core/tools.py`, accepts expected params, returns expected shape | Call function directly in Python REPL |
| **API key** | Key is defined in `core/config.py`, read from env | Check `os.getenv()` call |
| **Fallback** | Fallback chain still fires when primary fails | Remove primary API key, verify fallback runs |
| **Context injection** | Result is appended to message with `---` separator | Check the injection line in `stream.py` |
| **Response rendering** | Frontend can render the response (markdown is valid, no broken links) | Send a test message with the tool active |

---

## Required output after each change

When modifying any search tool, document which layer you changed:

1. **Layer changed** — UI trigger / tool binding / route dispatch / auto-trigger / tool function / API key / fallback / context injection / response format.
2. **Tool IDs affected** — which tool string IDs were added, renamed, or removed.
3. **Fallback impact** — did the fallback order change? Are all fallbacks still reachable?
4. **Response shape impact** — did the return type or markdown format change? Will the LLM prompt injection pattern still work?
5. **UI sync** — does `index.html` still match `stream.py`?
6. **Docs sync** — does `README.md` search tools table still match?

---

## Regression checklist

Before marking a search-tool change as complete:

- [ ] Every tool string ID in `index.html` `toolBindings` has a matching handler in `stream.py`.
- [ ] Every handler in `stream.py` calls a function that exists in `core/tools.py`.
- [ ] Every API key used is read from `core/config.py` via `os.getenv()`, not hardcoded.
- [ ] `_needs_web_search()` still correctly recognizes explicit tool selection AND auto-trigger keywords.
- [ ] The web search fallback chain (SerpAPI → CSE) has not been reversed or broken.
- [ ] The reverse image cascade (Lens → Reverse → Yandex) has not been reordered without justification.
- [ ] All search result strings are injected with the `---` separator pattern.
- [ ] `README.md` search tools table matches current tool IDs and button labels.
- [ ] `pytest services/chatbot/tests/ -v` passes.
- [ ] No image-pipeline or ComfyUI files were modified.
