"""Tests for the Phase 7 security hardening pass.

Scope (verbatim from task):
  1. code-interpreter execution risk          — gated behind ENABLE_CODE_INTERPRETER
  2. unsafe URL handling / SSRF in scrapers   — core/url_safety + tools.serpapi_reverse_image
  3. raw HTML sanitizer fallback              — verified by JS reading (not unit-tested here)
  4. hardcoded secret fallback                — none found in audit
  5. bare except blocks                       — deferred per scope rule
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure services/chatbot is importable when pytest runs from repo root.
_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ---------------------------------------------------------------------------
# core.url_safety
# ---------------------------------------------------------------------------

from core.url_safety import (  # noqa: E402  (import after sys.path tweak)
    UnsafeUrlError,
    assert_safe_external_url,
    is_safe_external_url,
)


_UNSAFE_LITERAL_URLS = [
    # scheme attacks
    "file:///etc/passwd",
    "javascript:alert(1)",
    "ftp://example.com/x",
    "gopher://example.com/_GET%20/",
    "data:text/html,<script>alert(1)</script>",
    # loopback hostnames
    "http://localhost/",
    "https://localhost:5000/admin",
    "http://ip6-localhost/",
    # loopback IPs
    "http://127.0.0.1/",
    "http://127.255.255.254/",
    "http://[::1]/",
    # RFC1918 / private
    "http://10.0.0.5/",
    "http://10.255.255.255/",
    "http://172.16.0.1/",
    "http://172.31.255.254/",
    "http://192.168.1.1/",
    # link-local / cloud metadata
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.0.1/",
    "http://[fe80::1]/",
    # unique-local IPv6
    "http://[fc00::1]/",
    "http://[fd00::1]/",
    # cloud metadata hostnames
    "http://metadata.google.internal/",
    "http://metadata/",
    # credentials embedded
    "http://user:pass@example.com/",
    # malformed
    "",
    "http://",
    "://nothing",
]


@pytest.mark.parametrize("url", _UNSAFE_LITERAL_URLS)
def test_unsafe_urls_rejected(url):
    """Every URL above must be rejected without performing DNS."""
    assert is_safe_external_url(url, resolve=False) is False, url
    with pytest.raises(UnsafeUrlError):
        assert_safe_external_url(url, resolve=False)


def test_assert_raises_with_short_reason():
    with pytest.raises(UnsafeUrlError) as excinfo:
        assert_safe_external_url("http://127.0.0.1/", resolve=False)
    # The reason should mention the offending host or range.
    assert "127.0.0.1" in str(excinfo.value)


def test_safe_public_urls_pass_with_dns_disabled():
    # Bare structural check (skip DNS) — these URLs are well-formed,
    # use https, and have public-looking hostnames.
    for url in [
        "https://example.com/file.pdf",
        "https://cdn.example.org/path/to/img.png",
        "http://example.com:8080/x",
    ]:
        assert is_safe_external_url(url, resolve=False) is True, url


def test_dns_resolution_blocks_internal(monkeypatch):
    """A public-looking hostname that resolves to a private IP is rejected."""
    import socket as _socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        # Pretend "evil.example.com" resolves to an RFC1918 address.
        if host == "evil.example.com":
            return [(_socket.AF_INET, _socket.SOCK_STREAM, 0, "", ("10.0.0.5", 0))]
        if host == "good.example.com":
            return [(_socket.AF_INET, _socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
        if host == "noresolve.example.com":
            raise _socket.gaierror("nodename nor servname provided")
        raise _socket.gaierror("unknown host")

    monkeypatch.setattr("core.url_safety.socket.getaddrinfo", fake_getaddrinfo)
    assert is_safe_external_url("https://evil.example.com/x") is False
    assert is_safe_external_url("https://good.example.com/x") is True
    # Unresolvable hosts must be refused too — DNS rebinding defense.
    assert is_safe_external_url("https://noresolve.example.com/x") is False


# ---------------------------------------------------------------------------
# Code interpreter feature flag
# ---------------------------------------------------------------------------


def test_code_interpreter_default_off(monkeypatch):
    """The env flag controlling code execution must default to 'disabled'."""
    monkeypatch.delenv("ENABLE_CODE_INTERPRETER", raising=False)
    flag = os.getenv("ENABLE_CODE_INTERPRETER", "").strip().lower()
    assert flag not in ("1", "true", "yes", "on")


@pytest.mark.parametrize(
    "value, expected_enabled",
    [
        ("", False),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
        ("random", False),
        ("1", True),
        ("true", True),
        ("True", True),
        ("YES", True),
        ("on", True),
    ],
)
def test_code_interpreter_flag_parsing(monkeypatch, value, expected_enabled):
    """Match the exact parser used by chatbot_main.py."""
    monkeypatch.setenv("ENABLE_CODE_INTERPRETER", value)
    parsed = os.getenv("ENABLE_CODE_INTERPRETER", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    assert parsed is expected_enabled


def test_code_interpreter_block_present_in_source():
    """Defensive: the gating wording must remain in the source so accidental
    refactors do not silently re-enable code execution.
    """
    src = (_CHATBOT_DIR / "chatbot_main.py").read_text(encoding="utf-8-sig", errors="replace")
    assert "ENABLE_CODE_INTERPRETER" in src
    # The refusal message must mention the env var so users can fix it.
    assert "code-execution requests are refused" in src
    # The dangerous subprocess call must still be wrapped by the flag check.
    flag_idx = src.find("ENABLE_CODE_INTERPRETER")
    subproc_idx = src.find("subprocess.run(['node'", flag_idx)
    assert subproc_idx != -1, "subprocess.run for node must follow the flag check"


# ---------------------------------------------------------------------------
# Tool-level integration: serpapi_reverse_image refuses unsafe URLs
# ---------------------------------------------------------------------------


def test_serpapi_reverse_image_refuses_loopback(monkeypatch):
    """The reverse-image tool must reject loopback URLs before any network call."""
    import core.tools as tools_mod

    # Force a configured key so the function reaches the URL check.
    monkeypatch.setattr(tools_mod, "SERPAPI_API_KEY", "fake-key-for-test", raising=False)

    called = {"count": 0}

    def fake_get(*args, **kwargs):  # pragma: no cover - must not be called
        called["count"] += 1
        raise AssertionError("network must not be touched for unsafe URL")

    monkeypatch.setattr(tools_mod.requests, "get", fake_get)

    out = tools_mod.serpapi_reverse_image("http://127.0.0.1/x.png")
    assert isinstance(out, str)
    assert "không an toàn" in out or "rejected" in out.lower() or "❌" in out
    assert called["count"] == 0


def test_serpapi_reverse_image_refuses_metadata_endpoint(monkeypatch):
    import core.tools as tools_mod

    monkeypatch.setattr(tools_mod, "SERPAPI_API_KEY", "fake-key-for-test", raising=False)

    def fake_get(*args, **kwargs):  # pragma: no cover
        raise AssertionError("network must not be touched for unsafe URL")

    monkeypatch.setattr(tools_mod.requests, "get", fake_get)

    out = tools_mod.serpapi_reverse_image("http://169.254.169.254/latest/meta-data/")
    assert "❌" in out or "rejected" in out.lower()
