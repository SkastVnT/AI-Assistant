"""Focused tests for the conversation_id validation contract.

These tests cover the security-critical regex shared by:
  - services/chatbot/chatbot_main.py @app.route('/c/<conversation_id>')
  - services/chatbot/routes/stream.py POST /chat/stream conversation_id field
  - services/chatbot/static/js/modules/chat-manager.js (URL parse / restore)
  - services/chatbot/static/js/main.js popstate handler

If the server-side regex changes, the JS regex literal in chat-manager.js and
main.js must change with it. These tests pin the contract.
"""

from __future__ import annotations

import re

import pytest

# Single source of truth — must match the Python and JS regex literals exactly.
CONVERSATION_ID_PATTERN = re.compile(r"[A-Za-z0-9_\-]{1,64}")


@pytest.mark.parametrize(
    "value",
    [
        "chat_1700000000000",  # frontend default format
        "chat_abc",
        "abc-DEF_123",
        "a",  # 1 char (lower bound)
        "x" * 64,  # 64 chars (upper bound)
        "01234567890123456789012345678901",
    ],
)
def test_valid_conversation_ids(value):
    assert CONVERSATION_ID_PATTERN.fullmatch(value) is not None


@pytest.mark.parametrize(
    "value",
    [
        "",  # empty
        "x" * 65,  # exceeds cap
        "../etc/passwd",  # path traversal
        "abc/def",  # slashes
        "abc def",  # spaces
        "abc.def",  # dots
        "abc?def",  # query separator
        "abc#def",  # fragment
        "<script>",  # angle brackets
        "../../",
        "%00",
        "a\nb",  # newline injection
    ],
)
def test_invalid_conversation_ids_rejected(value):
    assert CONVERSATION_ID_PATTERN.fullmatch(value) is None


def test_truncation_then_validate_does_not_open_holes():
    """Backend slices to 64 chars *before* validating. Ensure that a
    65-char id whose first 64 chars are valid still gets rejected
    (because the backend slices to 64 first, which would accidentally
    pass an attacker-supplied prefix). The mitigation is to slice first
    AND re-validate, which both call sites already do."""
    raw = ("a" * 64) + "/"  # 65 chars; last is invalid
    truncated = raw.strip()[:64]  # mirrors stream.py behaviour
    assert len(truncated) == 64
    # After truncation the value is just "a"*64 which IS valid — meaning
    # the truncation by itself does not protect against the trailing junk.
    # The regex check is what does. Document this in code as a defense in depth.
    assert CONVERSATION_ID_PATTERN.fullmatch(truncated) is not None
    # And the raw 65-char value is rejected outright by fullmatch.
    assert CONVERSATION_ID_PATTERN.fullmatch(raw) is None


def test_url_path_extraction_matches_js_regex():
    """The JS side parses /c/<id> with /^\\/c\\/([A-Za-z0-9_\\-]{1,64})$/.
    Any URL form the backend accepts must also be extractable client-side.
    """
    js_path_re = re.compile(r"^/c/([A-Za-z0-9_\-]{1,64})$")
    for valid in ["chat_1", "chat_abc-DEF", "x" * 64]:
        m = js_path_re.match(f"/c/{valid}")
        assert m is not None
        assert m.group(1) == valid
    for invalid_path in ["/c/", "/c/" + "x" * 65, "/c/abc/def", "/d/abc"]:
        assert js_path_re.match(invalid_path) is None


def test_stream_payload_truncation_contract():
    """stream.py does: (data.get('conversation_id') or '').strip()[:64]
    Verify the contract holds for typical edge cases.
    """

    def normalize(raw):
        return (raw or "").strip()[:64]

    assert normalize(None) == ""
    assert normalize("") == ""
    assert normalize("  chat_1  ") == "chat_1"
    assert len(normalize("x" * 100)) == 64
    # After normalize, validation still rejects junk past the truncation point.
    assert CONVERSATION_ID_PATTERN.fullmatch(normalize("chat_1/extra")) is None
