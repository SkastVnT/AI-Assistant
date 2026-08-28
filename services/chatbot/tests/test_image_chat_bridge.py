"""
test_image_chat_bridge.py — Phase 1a / PR1

Verifies the "Thinking with Images" bridge in routes/stream.py:
  - When IMAGE_PIPELINE_CHAT_BRIDGE=true and the message is an image intent,
    /chat/stream forwards the anime pipeline's ap_* SSE frames VERBATIM, then
    streams a short LLM caption + a real `complete` event (so the chat turn is
    finalized/saved).
  - On a cancelled pipeline, no LLM caption is generated; a short cancel
    message + complete{has_image:false} is emitted instead.
  - With the flag OFF, image prompts fall back to the normal LLM chat path
    (no ap_* frames) — the rollback guarantee.

The bridge is exercised end-to-end through the Flask test client; the GPU
pipeline (`anime_pipeline_service.stream_pipeline`) and the caption LLM
(`chatbot.chat_stream`) are stubbed so the test is fast and offline.
"""

import routes.stream as stream_mod

import core.anime_pipeline_service as aps


class _FakeChatbot:
    """Minimal chatbot stub. Records caption-stream invocations."""

    def __init__(self):
        self.caption_calls = 0
        self.registry = None

    def chat_stream(self, **kwargs):  # noqa: D401 — generator stub
        self.caption_calls += 1
        yield "Một bức tranh anime waifu xinh đẹp."


def _fake_stream_success(_req):
    yield aps._sse_line(
        "ap_status",
        {"job_id": "job-test-1", "message": "started", "stages": []},
    )
    yield aps._sse_line("ap_preview", {"job_id": "job-test-1", "layer_num": 1})
    yield aps._sse_line(
        "ap_result",
        {"job_id": "job-test-1", "status": "completed", "has_image": True},
    )
    yield aps._sse_line("ap_done", {"job_id": "job-test-1"})


def _fake_stream_cancelled(_req):
    yield aps._sse_line(
        "ap_status",
        {"job_id": "job-test-2", "message": "started", "stages": []},
    )
    yield aps._sse_line(
        "ap_cancelled",
        {"job_id": "job-test-2", "message": "cancelled", "has_image": False},
    )


def _post_stream(client, message, **extra):
    body = {"message": message, "model": "grok"}
    body.update(extra)
    return client.post(
        "/chat/stream",
        json=body,
        headers={"Accept": "text/event-stream"},
    )


class TestImageChatBridge:
    def test_forwards_ap_frames_and_caption_complete(self, client, monkeypatch):
        fake = _FakeChatbot()
        monkeypatch.setenv("IMAGE_PIPELINE_CHAT_BRIDGE", "true")
        monkeypatch.setattr(stream_mod, "get_chatbot", lambda *_a, **_k: fake)
        monkeypatch.setattr(
            "core.anime_pipeline_service.stream_pipeline", _fake_stream_success
        )

        r = _post_stream(client, "vẽ anime waifu")
        assert r.status_code == 200
        body = r.get_data(as_text=True)

        # ap_* frames forwarded VERBATIM (not renamed to image_*).
        assert "event: ap_status" in body
        assert "event: ap_result" in body
        assert "event: ap_done" in body
        assert "event: image_" not in body  # no gratuitous namespace rename

        # Caption streamed as chunk(s) + a real complete that finalizes the turn.
        assert "event: chunk" in body
        assert "anime waifu" in body
        assert "event: complete" in body
        assert '"has_image": true' in body

        # LLM caption ran exactly once on success.
        assert fake.caption_calls == 1

    def test_cancel_skips_llm_caption(self, client, monkeypatch):
        fake = _FakeChatbot()
        monkeypatch.setenv("IMAGE_PIPELINE_CHAT_BRIDGE", "true")
        monkeypatch.setattr(stream_mod, "get_chatbot", lambda *_a, **_k: fake)
        monkeypatch.setattr(
            "core.anime_pipeline_service.stream_pipeline", _fake_stream_cancelled
        )

        r = _post_stream(client, "vẽ anime waifu")
        assert r.status_code == 200
        body = r.get_data(as_text=True)

        assert "event: ap_cancelled" in body
        assert "Đã hủy tạo ảnh." in body
        assert "event: complete" in body
        assert '"has_image": false' in body
        # No LLM caption on a cancelled turn.
        assert fake.caption_calls == 0

    def test_force_image_bridge_engages_without_keyword(self, client, monkeypatch):
        # A prompt with NO image keyword still bridges when the frontend
        # sends force_image_bridge=true (mismatch-proof explicit signal).
        fake = _FakeChatbot()
        monkeypatch.setenv("IMAGE_PIPELINE_CHAT_BRIDGE", "true")
        monkeypatch.setattr(stream_mod, "get_chatbot", lambda *_a, **_k: fake)
        monkeypatch.setattr(
            "core.anime_pipeline_service.stream_pipeline", _fake_stream_success
        )

        r = _post_stream(client, "xin chào bạn", force_image_bridge=True)
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "event: ap_status" in body
        assert "event: complete" in body

    def test_no_keyword_no_force_no_bridge(self, client, monkeypatch):
        # Flag on, but neither image keyword nor force → normal chat path.
        fake = _FakeChatbot()
        monkeypatch.setenv("IMAGE_PIPELINE_CHAT_BRIDGE", "true")
        monkeypatch.setattr(stream_mod, "get_chatbot", lambda *_a, **_k: fake)

        def _boom(_req):
            raise AssertionError("stream_pipeline must not run for a non-image prompt")
            yield  # pragma: no cover

        monkeypatch.setattr("core.anime_pipeline_service.stream_pipeline", _boom)

        r = _post_stream(client, "xin chào bạn")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "event: ap_status" not in body

    def test_flag_off_falls_back_to_chat(self, client, monkeypatch):
        fake = _FakeChatbot()
        monkeypatch.setenv("IMAGE_PIPELINE_CHAT_BRIDGE", "false")
        monkeypatch.setattr(stream_mod, "get_chatbot", lambda *_a, **_k: fake)

        # If the bridge wrongly engaged it would call this and raise.
        def _boom(_req):
            raise AssertionError("stream_pipeline must not run when flag is off")
            yield  # pragma: no cover

        monkeypatch.setattr("core.anime_pipeline_service.stream_pipeline", _boom)

        r = _post_stream(client, "vẽ anime waifu")
        assert r.status_code == 200
        body = r.get_data(as_text=True)

        # Normal chat path — no anime pipeline frames.
        assert "event: ap_status" not in body
        assert "event: complete" in body
