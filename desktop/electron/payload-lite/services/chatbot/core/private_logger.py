"""
Private Data Logger — Local storage for all chatbot interactions.

Saves chat sessions, generated images, and interaction logs to the
private/ directory structure. Uses Ollama qwen2.5:0.5b for lightweight
summarisation and title generation before persisting data.

Directory layout:
    private/
        data/           — Chat logs (JSON per session)
        image_genarated/ — Copies of generated images
        session_chat/   — Full conversation session dumps
"""

import json
import os
import re
import shutil
import threading
import time
import base64
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

PRIVATE_DIR = Path(__file__).parent.parent / 'private'
DATA_DIR = PRIVATE_DIR / 'data'
IMAGE_DIR = PRIVATE_DIR / 'image_genarated'
SESSION_DIR = PRIVATE_DIR / 'session_chat'

# ── Helpers ──────────────────────────────────────────────────────────────────


def _ensure_dirs():
    """Create private directory tree if it doesn't exist."""
    for d in (DATA_DIR, IMAGE_DIR, SESSION_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _remove_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics and convert to ASCII-safe slug."""
    import unicodedata
    # Normalise to decomposed form then strip combining marks
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Replace non-alphanum with underscores, collapse multiples
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', ascii_text).strip('_')
    return slug[:80] if slug else 'untitled'


def _timestamp_str() -> str:
    """Return a filename-safe timestamp: YYYY-MM-DD_HH-MM-SS"""
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def _timestamp_display() -> str:
    """Return a human readable timestamp: YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _generate_title_ollama(text: str, language: str = 'vi') -> str:
    """Generate a short title via Ollama qwen2.5:0.5b.  Returns plain ASCII."""
    import requests as _req
    text = (text or '').strip()[:200]
    if not text:
        return 'untitled'

    if language == 'en':
        prompt = (
            'Generate a concise 3-5 word English title for this text. '
            'Return ONLY the title, no quotes:\n' + text
        )
    else:
        prompt = (
            'Tạo tiêu đề ngắn gọn 3-5 từ cho đoạn văn này. '
            'Chỉ trả về tiêu đề, không giải thích:\n' + text
        )

    try:
        resp = _req.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:0.5b',
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.7, 'num_predict': 20},
            },
            timeout=8,
        )
        resp.raise_for_status()
        title = resp.json().get('response', '').strip().strip('"').strip("'")
        if title:
            return _remove_diacritics(title)
    except Exception as e:
        logger.debug(f'[PrivateLog] Ollama title gen skipped: {e}')

    # Fallback: first 40 chars
    return _remove_diacritics(text[:40])


def _summarise_ollama(text: str) -> str:
    """Quick 1-2 sentence summary via qwen2.5:0.5b.  Best effort."""
    import requests as _req
    text = (text or '').strip()[:500]
    if not text:
        return ''

    prompt = (
        'Summarise the following in 1-2 short sentences. '
        'Return only the summary:\n' + text
    )
    try:
        resp = _req.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:0.5b',
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.5, 'num_predict': 60},
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get('response', '').strip()
    except Exception:
        return ''


# ── Public API ───────────────────────────────────────────────────────────────


def log_chat(session_id: str, user_message: str, assistant_response: str,
             model: str = '', context: str = '', language: str = 'vi',
             tools: list = None, latency_ms: float = 0,
             thinking_process: str = None):
    """
    Log a complete chat turn (input + output) to private/data/.

    Runs in a background thread so it never blocks the HTTP response.
    """
    def _worker():
        try:
            _ensure_dirs()

            ts = _timestamp_str()
            title = _generate_title_ollama(user_message, language)
            summary = _summarise_ollama(
                f'User: {user_message[:200]}\nAssistant: {assistant_response[:300]}'
            )

            filename = f'{title}_{ts}.json'
            filepath = DATA_DIR / filename

            record = {
                'timestamp': _timestamp_display(),
                'session_id': session_id,
                'title': title,
                'summary': summary,
                'model': model,
                'context': context,
                'language': language,
                'tools': tools or [],
                'latency_ms': latency_ms,
                'user_message': user_message,
                'assistant_response': assistant_response,
                'thinking_process': thinking_process,
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            logger.info(f'[PrivateLog] Chat saved → {filename}')
        except Exception as e:
            logger.error(f'[PrivateLog] Error saving chat: {e}')

    threading.Thread(target=_worker, daemon=True).start()


def log_image_generation(prompt: str, provider: str = '', model: str = '',
                         image_data: str = None, image_url: str = None,
                         image_path: str = None, session_id: str = '',
                         mode: str = 'txt2img', extra: dict = None):
    """
    Save a generated image to private/image_genarated/ with metadata sidecar.

    Accepts one of: base64 `image_data`, a local `image_path`, or `image_url`.
    Runs in a background thread.
    """
    def _worker():
        try:
            _ensure_dirs()

            ts = _timestamp_str()
            title = _generate_title_ollama(prompt, 'en')
            base_name = f'{title}_{ts}'

            saved_image_path = None

            # Save image bytes
            if image_data:
                raw = image_data
                if ',' in raw:
                    raw = raw.split(',', 1)[1]
                img_bytes = base64.b64decode(raw)
                img_file = IMAGE_DIR / f'{base_name}.png'
                with open(img_file, 'wb') as f:
                    f.write(img_bytes)
                saved_image_path = str(img_file)
            elif image_path and Path(image_path).exists():
                ext = Path(image_path).suffix or '.png'
                dest = IMAGE_DIR / f'{base_name}{ext}'
                shutil.copy2(image_path, dest)
                saved_image_path = str(dest)
            elif image_url:
                import requests as _req
                try:
                    resp = _req.get(image_url, timeout=15)
                    resp.raise_for_status()
                    ct = resp.headers.get('content-type', '')
                    ext = '.jpg' if 'jpeg' in ct else '.png'
                    dest = IMAGE_DIR / f'{base_name}{ext}'
                    with open(dest, 'wb') as f:
                        f.write(resp.content)
                    saved_image_path = str(dest)
                except Exception as dl_err:
                    logger.warning(f'[PrivateLog] Image download failed: {dl_err}')

            # Save metadata sidecar
            meta = {
                'timestamp': _timestamp_display(),
                'session_id': session_id,
                'title': title,
                'mode': mode,
                'prompt': prompt,
                'provider': provider,
                'model': model,
                'image_file': saved_image_path,
                **(extra or {}),
            }
            meta_file = IMAGE_DIR / f'{base_name}.json'
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            logger.info(f'[PrivateLog] Image saved → {base_name}')
        except Exception as e:
            logger.error(f'[PrivateLog] Error saving image: {e}')

    threading.Thread(target=_worker, daemon=True).start()


def log_session_dump(session_id: str, messages_html: list,
                     title: str = '', language: str = 'vi'):
    """
    Dump a full conversation session to private/session_chat/.
    Called periodically or on session switch.
    """
    def _worker():
        try:
            _ensure_dirs()

            ts = _timestamp_str()
            safe_title = _remove_diacritics(title) if title else 'session'
            filename = f'{safe_title}_{ts}.json'

            record = {
                'timestamp': _timestamp_display(),
                'session_id': session_id,
                'title': title,
                'message_count': len(messages_html),
                'messages_html': messages_html,
            }

            with open(SESSION_DIR / filename, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            logger.info(f'[PrivateLog] Session dump → {filename}')
        except Exception as e:
            logger.error(f'[PrivateLog] Error saving session: {e}')

    threading.Thread(target=_worker, daemon=True).start()


def log_interaction(event_type: str, data: dict, session_id: str = ''):
    """
    Log miscellaneous interactions (tool calls, errors, MCP usage, etc.)
    to private/data/ with an 'interaction_' prefix.
    """
    def _worker():
        try:
            _ensure_dirs()
            ts = _timestamp_str()
            filename = f'interaction_{event_type}_{ts}.json'

            record = {
                'timestamp': _timestamp_display(),
                'session_id': session_id,
                'event_type': event_type,
                **data,
            }

            with open(DATA_DIR / filename, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            logger.debug(f'[PrivateLog] Interaction → {filename}')
        except Exception as e:
            logger.error(f'[PrivateLog] Error saving interaction: {e}')

    threading.Thread(target=_worker, daemon=True).start()
