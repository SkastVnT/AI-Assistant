# Manual QA Checklist — Vietnamese Image Chat
> Date: ____________________  Tester: ____________________

## Pre-conditions
- [ ] Chatbot is running (`python run.py`)
- [ ] `.env` has `USE_FASTAPI=true`
- [ ] `.env` has `IMAGE_FIRST_MODE=1`
- [ ] `.env` has at least one remote API key (`FAL_API_KEY` or `TOGETHER_API_KEY`)
- [ ] Browser open at `http://localhost:5000`

---

## Test 1: Generate new image (Vietnamese)

**Input:** `vẽ cô gái anime tóc hồng ngồi trên bãi biển lúc hoàng hôn`

| Check | Expected | Pass? |
|-------|----------|-------|
| Image displayed? | Yes, 1 image in chat | [ ] |
| Style correct? | Anime style | [ ] |
| Subject matches? | Girl with pink hair on beach | [ ] |
| Sunset visible? | Golden hour / sunset tones | [ ] |
| Response text present? | Contains image URL or inline display | [ ] |
| Latency? | < 30s | [ ] |
| Provider shown? | `fal`, `comfyui`, or `together` in logs | [ ] |

**Expected log pattern:**
```
[ScenePlanner] classify → GENERATE
[PromptBuilder] built prompt (XX chars)
[ProviderRouter] Routing to ...
[SessionMemory] session-xxx: provider=..., ref=https://...
```

---

## Test 2: Follow-up edit (change hair color)

**Input:** `đổi tóc thành màu trắng`

| Check | Expected | Pass? |
|-------|----------|-------|
| Classified as edit? | Yes, EDIT_FOLLOWUP in logs | [ ] |
| New image displayed? | Yes, updated image | [ ] |
| Hair color = white? | White or silver hair visible | [ ] |
| Background preserved? | Same beach / sunset from Test 1 | [ ] |
| edit_lineage_count? | 1 (visible in debug logs) | [ ] |
| Provider same? | Same as Test 1 (session continuity) | [ ] |

**Expected log pattern:**
```
[ScenePlanner] classify → EDIT_FOLLOWUP
[EditRouting] i2i path — source_image_url from session (lineage=0)
[SessionMemory] session-xxx: lineage=1
```

---

## Test 3: Poster with text overlay

**Input:** `tạo poster quảng cáo với chữ "SALE 50%" màu đỏ nền đen`

| Check | Expected | Pass? |
|-------|----------|-------|
| Image displayed? | Yes, poster-style image | [ ] |
| wants_text_in_image? | True in scene spec | [ ] |
| "SALE 50%" visible? | Text rendered in image (best effort) | [ ] |
| Red color? | Red text or red accent | [ ] |
| Dark background? | Black or dark background | [ ] |
| "text" NOT in negative? | Negative prompt should not suppress text | [ ] |

**Note:** Text rendering quality depends on the model. Some models
(FLUX, SDXL) handle text better than others. The key check is that
the orchestrator does NOT add "text" to the negative prompt.

**Expected log pattern:**
```
[ScenePlanner] classify → GENERATE
  wants_text_in_image=True
[PromptBuilder] text_in_image flag → skipping 'text' in negative
```

---

## Test 4: Consistency request (keep character, change background)

**Pre-condition:** Run Test 1 first (to have a previous image in session).

**Input:** `giữ nhân vật cũ nhưng đổi nền thành thành phố cyberpunk ban đêm`

| Check | Expected | Pass? |
|-------|----------|-------|
| Classified as edit? | EDIT_FOLLOWUP | [ ] |
| Character preserved? | Same anime girl visible | [ ] |
| Background changed? | Cyberpunk city at night | [ ] |
| wants_consistency? | True in scene spec | [ ] |
| Subject attributes? | Should contain original attributes (pink/white hair, blue eyes) | [ ] |
| Neon lighting? | Neon / cyberpunk lighting visible | [ ] |

**Expected log pattern:**
```
[ScenePlanner] classify → EDIT_FOLLOWUP
  wants_consistency_with_previous=True
  edit_ops: [keep(character), change(background)]
[EditRouting] i2i path — source_image_url from session
```

---

## Test 5: Remote fallback test

**Pre-condition:**
- On PC/GPU: Stop ComfyUI service, keep `AUTO_START_COMFYUI=1`
- On laptop: Already uses remote only

**Input:** `vẽ con rồng bay trên núi lửa, chất lượng cao`

| Check | Expected | Pass? |
|-------|----------|-------|
| Image displayed? | Yes (via remote provider) | [ ] |
| Provider in logs? | `fal` or `together` (NOT `comfyui`) | [ ] |
| cost_usd > 0? | Yes (remote has cost) | [ ] |
| Quality correct? | High quality / detailed image | [ ] |
| No error toast? | No error shown to user | [ ] |
| Fallback logged? | "[ProviderRouter] ... healthy=False" or similar | [ ] |

**PC/GPU expected log pattern:**
```
[RuntimeProfile] mode=full
  prefer_local_when_healthy=True
[ProviderRouter] ComfyUI health check → False
[ProviderRouter] Falling back to remote providers
[Provider:fal] Generating image...
```

**Laptop expected log pattern:**
```
[RuntimeProfile] mode=low_resource
  skip_comfyui_provider=True
[ProviderRouter] No local providers registered
[Provider:fal] Generating image...
```

---

## Additional regression checks

| # | Scenario | Input | Expected | Pass? |
|---|----------|-------|----------|-------|
| 6 | English input | "Draw a dragon in a volcano" | Image generated | [ ] |
| 7 | Non-image message | "Hôm nay thời tiết thế nào?" | LLM text response (no image) | [ ] |
| 8 | Second edit in chain | After Test 2: `thêm kính` | Glasses added, lineage=2 | [ ] |
| 9 | Fresh gen after edits | `vẽ phong cảnh mới hoàn toàn` | New image, lineage reset to 0 | [ ] |
| 10 | Long prompt | `tạo ảnh cô gái chiến binh với kiếm rồng áo giáp đen góc thấp chất lượng cao siêu chi tiết 8K` | Detailed warrior image | [ ] |

---

## Environment checklist

### Laptop mode
```
AUTO_START_IMAGE_SERVICES=0
AUTO_START_COMFYUI=0
AUTO_START_STABLE_DIFFUSION=0
IMAGE_FIRST_MODE=1
```

### PC/GPU mode
```
AUTO_START_IMAGE_SERVICES=1
AUTO_START_COMFYUI=1
AUTO_START_STABLE_DIFFUSION=1
IMAGE_FIRST_MODE=1
COMFYUI_URL=http://127.0.0.1:8188
SD_API_URL=http://127.0.0.1:8188
```

---

## Sign-off

| Item | Status |
|------|--------|
| All 5 core tests pass | [ ] |
| All 5 regression tests pass | [ ] |
| No console errors / stack traces | [ ] |
| Logs match expected patterns | [ ] |

Tested by: ________________________  Date: ________________________
