"""Lightweight smoke checks for chat UI regression-sensitive logic.

These tests avoid browser dependencies and verify that critical logic
still exists in frontend modules after refactors.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESSAGE_RENDERER = ROOT / "static" / "js" / "modules" / "message-renderer.js"
MAIN_JS = ROOT / "static" / "js" / "main.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_token_gauge_render_logic_exists():
    src = _read(MESSAGE_RENDERER)
    assert "addResponseStats(contentDiv, stats = {})" in src
    assert "if (tokens && maxTokens)" in src
    assert "token-gauge" in src
    assert "tokens/maxTokens" not in src  # sanity: should be template-based, not hardcoded typo


def test_stream_complete_maps_max_tokens_to_renderer_stats():
    src = _read(MAIN_JS)
    assert "streamCompleteData.max_tokens" in src
    assert "maxTokens: _maxTokens" in src
    assert "this.messageRenderer.addResponseStats" in src


def test_thinking_reasoning_collapsible_logic_exists():
    src = _read(MESSAGE_RENDERER)
    assert "thinking-step--collapsed" in src
    assert "thinking-step--expanded" in src
    assert "thinking-reasoning__header" in src
    assert "header.addEventListener('click'" in src


def test_thinking_no_forced_auto_collapse_timeout():
    src = _read(MESSAGE_RENDERER)
    # Regression guard: previous logic hid entire thinking section after 1.5s.
    assert "setTimeout(() => {" not in src or "thinking-content--collapsed" not in src.split("setTimeout(() => {")[-1][:250]
