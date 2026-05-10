"""
last30days-skill integration — subprocess wrapper.

Calls the last30days CLI engine via subprocess for social media/web research.
Returns markdown string matching the existing tool response contract.

Isolation boundary: last30days may require Python 3.12+ and Node.js,
so it runs in a separate process, not imported directly.
"""
import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

# Setup path (same pattern as core/tools.py)
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import (
    LAST30DAYS_ENABLED,
    LAST30DAYS_SCRIPT_PATH,
    LAST30DAYS_PYTHON_PATH,
    LAST30DAYS_TIMEOUT,
)

logger = logging.getLogger(__name__)

MAX_TOPIC_LENGTH = 500
ALLOWED_DEPTHS = frozenset({"quick", "default", "deep"})
ALLOWED_SOURCES_RE = re.compile(r'^[\w,]+$')

# ── Default script path (auto-detect from vendor dir) ────────────────────
_VENDOR_SCRIPT = CHATBOT_DIR / "vendor" / "last30days" / "repo" / "scripts" / "last30days.py"


def _resolve_script_path() -> str:
    """Return the absolute path to the last30days entry script."""
    if LAST30DAYS_SCRIPT_PATH:
        return LAST30DAYS_SCRIPT_PATH
    if _VENDOR_SCRIPT.exists():
        return str(_VENDOR_SCRIPT)
    return ""


def run_last30days_research(
    topic: str,
    *,
    query_type: str = "general",
    depth: str = "default",
    days: int = 30,
    sources: str | None = None,
) -> str:
    """Run last30days social-media research and return a markdown report.

    Parameters
    ----------
    topic : str
        Research topic / query string.
    query_type : str
        One of: general, sentiment, trend, deep.
    depth : str
        Research depth: quick, default, deep.
    days : int
        Lookback window in days (1-90).
    sources : str | None
        Comma-separated source list (e.g. "reddit,youtube,x").
        None = all available sources.

    Returns
    -------
    str
        Markdown-formatted research results (tool-response-contract compliant).
        On error, returns an "❌ ..." string.
    """
    _start = time.monotonic()

    # ── Gate: feature flag ───────────────────────────────────────────────
    if not LAST30DAYS_ENABLED:
        logger.debug("[LAST30DAYS] Tool disabled (LAST30DAYS_ENABLED=false)")
        return "❌ last30days research chưa được bật. Set LAST30DAYS_ENABLED=true trong env."

    script_path = _resolve_script_path()
    if not script_path:
        logger.warning("[LAST30DAYS] Script not found — vendor not cloned?")
        return (
            "❌ Không tìm thấy last30days engine. "
            "Chạy setup script: services/chatbot/vendor/last30days/setup.ps1"
        )

    python_exe = LAST30DAYS_PYTHON_PATH or "python"

    # ── Input validation & sanitization ──────────────────────────────────
    topic = (topic or "").strip()
    if not topic:
        return "❌ Thiếu topic cho last30days research."
    if len(topic) > MAX_TOPIC_LENGTH:
        return f"❌ Topic quá dài ({len(topic)} chars, tối đa {MAX_TOPIC_LENGTH})."

    if depth not in ALLOWED_DEPTHS:
        logger.debug("[LAST30DAYS] Invalid depth %r, falling back to 'default'", depth)
        depth = "default"

    days = max(1, min(90, int(days) if isinstance(days, (int, float)) else 30))

    if sources and not ALLOWED_SOURCES_RE.match(sources):
        logger.debug("[LAST30DAYS] Invalid sources %r, ignoring", sources)
        sources = None

    # ── Build command ────────────────────────────────────────────────────
    cmd = [
        python_exe,
        script_path,
        topic,
        "--emit=compact",
        "--agent",
        f"--days={days}",
    ]

    if depth == "quick":
        cmd.append("--quick")
    elif depth == "deep":
        cmd.append("--deep")

    if sources:
        cmd.extend(["--sources", sources])

    logger.info(
        "[LAST30DAYS] Starting research: topic=%r, depth=%s, days=%d",
        topic,
        depth,
        days,
    )

    # ── Execute subprocess ───────────────────────────────────────────────
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=LAST30DAYS_TIMEOUT,
            cwd=str(Path(script_path).parent),
        )
    except subprocess.TimeoutExpired:
        elapsed = round(time.monotonic() - _start, 2)
        logger.warning("[LAST30DAYS] Research timed out after %.1fs (limit=%ds)", elapsed, LAST30DAYS_TIMEOUT)
        return (
            f"❌ last30days research timeout ({LAST30DAYS_TIMEOUT}s). "
            f"Thử lại với depth=quick hoặc giảm days."
        )
    except FileNotFoundError:
        logger.error("[LAST30DAYS] Python executable not found: %s", python_exe)
        return (
            f"❌ Không tìm thấy Python executable: {python_exe}. "
            f"Set LAST30DAYS_PYTHON_PATH trong env."
        )
    except Exception as e:
        logger.error("[LAST30DAYS] Subprocess error: %s", e)
        return f"❌ last30days research failed: {e}"

    # ── Parse output ─────────────────────────────────────────────────────
    if result.returncode != 0:
        stderr_snippet = (result.stderr or "")[:500]
        elapsed = round(time.monotonic() - _start, 2)
        logger.warning(
            "[LAST30DAYS] Non-zero exit (%d) after %.1fs: %s",
            result.returncode, elapsed, stderr_snippet,
        )
        return f"❌ last30days exited with code {result.returncode}. {stderr_snippet}"

    raw_output = result.stdout.strip()
    if not raw_output:
        elapsed = round(time.monotonic() - _start, 2)
        logger.warning("[LAST30DAYS] Empty output after %.1fs", elapsed)
        return "❌ last30days trả về kết quả rỗng. Có thể thiếu API keys hoặc không có data."

    # Try to parse as JSON (--emit=compact produces JSON)
    report = _parse_compact_output(raw_output, topic)

    elapsed = round(time.monotonic() - _start, 2)
    logger.info(
        "[LAST30DAYS] Completed: topic=%r depth=%s elapsed=%.1fs report_len=%d",
        topic[:60], depth, elapsed, len(report),
    )
    return report


def _parse_compact_output(raw: str, topic: str) -> str:
    """Parse last30days compact JSON output into markdown report."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: treat as raw markdown/text
        return _format_raw_report(raw, topic)

    # Compact JSON structure: {"topic", "summary", "sources": [...], "insights", ...}
    parts = [f"## 🔍 Social Research: {topic}\n"]

    if summary := data.get("summary"):
        parts.append(f"### Tổng quan\n{summary}\n")

    if insights := data.get("insights"):
        if isinstance(insights, list):
            parts.append("### Key Insights")
            for i, insight in enumerate(insights, 1):
                if isinstance(insight, dict):
                    parts.append(f"**{i}.** {insight.get('text', insight)}")
                else:
                    parts.append(f"**{i}.** {insight}")
            parts.append("")
        elif isinstance(insights, str):
            parts.append(f"### Key Insights\n{insights}\n")

    if sources_data := data.get("sources"):
        parts.append("### Sources")
        for src in sources_data:
            if isinstance(src, dict):
                name = src.get("name", src.get("source", "Unknown"))
                count = src.get("count", src.get("results", ""))
                score = src.get("score", "")
                line = f"- **{name}**"
                if count:
                    line += f" ({count} results)"
                if score:
                    line += f" — score: {score}"
                parts.append(line)
            else:
                parts.append(f"- {src}")
        parts.append("")

    if sentiment := data.get("sentiment"):
        parts.append(f"### Sentiment\n{sentiment}\n")

    if trends := data.get("trends"):
        if isinstance(trends, list):
            parts.append("### Trends")
            for t in trends:
                parts.append(f"- {t}")
            parts.append("")
        elif isinstance(trends, str):
            parts.append(f"### Trends\n{trends}\n")

    # If we only got the topic and nothing else parsed, fallback to raw
    if len(parts) <= 1:
        return _format_raw_report(raw, topic)

    return "\n".join(parts)


def _format_raw_report(raw: str, topic: str) -> str:
    """Wrap raw text output in a markdown report structure."""
    # Truncate if excessively long (keep under ~4000 chars for context window)
    if len(raw) > 4000:
        raw = raw[:3900] + "\n\n... (truncated)"
    return f"## 🔍 Social Research: {topic}\n\n{raw}"


# ── Inline‑command parameter parser (used by stream.py) ─────────────────

_DAYS_RE = re.compile(r'--days=(\d+)')
_SOURCES_RE = re.compile(r'--sources?=([\w,]+)')


def parse_research_params(raw_text: str) -> dict:
    """Parse inline ``--deep``, ``--quick``, ``--days=N``, ``--sources=x`` flags.

    Returns dict with keys: topic, depth, days, sources.
    """
    text = raw_text
    depth = "default"
    days = 30
    sources = None

    if " --deep" in text:
        depth = "deep"
        text = text.replace(" --deep", "", 1)
    elif " --quick" in text:
        depth = "quick"
        text = text.replace(" --quick", "", 1)

    m = _DAYS_RE.search(text)
    if m:
        days = max(1, min(90, int(m.group(1))))
        text = text[:m.start()] + text[m.end():]

    m = _SOURCES_RE.search(text)
    if m:
        sources = m.group(1)
        text = text[:m.start()] + text[m.end():]

    return {"topic": text.strip(), "depth": depth, "days": days, "sources": sources}
