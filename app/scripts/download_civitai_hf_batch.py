"""Bulk-download Civitai + HuggingFace assets listed in private/new_download2.txt
into LORA/new_2/<category>/.

Civitai: GET https://civitai.com/api/v1/models/{id} → modelVersions[0].files[0].downloadUrl
         then GET that URL with Authorization: Bearer <CIVITAI_API_KEY>
HuggingFace: list repo files via /api/models/<repo>, download .safetensors / .pt / .onnx
             via https://huggingface.co/<repo>/resolve/main/<filename>

Notes:
- civitai.com / civitai.red / civitai.green / civitai.work all share the same model-id space.
- Set DRY_RUN=1 to only print what would be downloaded.
- Resumes via HTTP Range when a partial file already exists.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

ROOT = Path(__file__).resolve().parents[2]
DEST_ROOT = ROOT / "LORA" / "new_2"
ENV_FILE = ROOT / "private" / ".env"


# --- Load CIVITAI_API_KEY ---
def _load_env_key(name: str) -> str | None:
    if name in os.environ:
        return os.environ[name]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return None


CIVITAI_API_KEY = _load_env_key("CIVITAI_API_KEY")
HF_TOKEN = _load_env_key("HUGGINGFACE_API_KEY") or _load_env_key("HUGGINGFACE_TOKEN")
DRY_RUN = os.environ.get("DRY_RUN") == "1"

# --- Inventory: (category, source, identifier) ---
# source: "civitai" → identifier is model-id
# source: "hf"      → identifier is repo path
INVENTORY: list[tuple[str, str, str]] = [
    # Character LoRA / packs
    ("character", "civitai", "434763"),  # all-characters-honkai-star-rail
    ("character", "civitai", "2043415"),  # 2025 all-characters HSR
    ("character", "civitai", "1866697"),  # all-characters Amphoreus v36 HSR
    ("character", "civitai", "357976"),  # pony all-characters Genshin 124
    ("character", "civitai", "450738"),  # all-characters Genshin 100
    ("character", "civitai", "471854"),  # all-characters ZZZ
    ("character", "civitai", "796742"),  # all-characters Wuthering Waves
    # Eye / face / detail
    ("eyes", "civitai", "596221"),  # eyes-for-pony perfect-anime-eyes
    ("eyes", "civitai", "1719571"),  # illustriousxl-eye-focus
    ("eyes", "civitai", "1690241"),  # sdxl white eyelashes helper
    # Style / detail polish
    ("style", "civitai", "1145743"),  # smooth-detailer-booster
    ("style", "civitai", "345962"),  # fine-anime-screencap-xl
    ("style", "civitai", "269772"),  # memaxl flat-anime-style
    ("style", "civitai", "1059388"),  # flux-illustrious-anime-style
    # Expression
    ("expression", "civitai", "140423"),  # sleepy-eyes
    ("expression", "civitai", "1297732"),  # sleeping-with-eyes-open
    ("expression", "civitai", "158012"),  # rolling-eyes
    ("expression", "civitai", "174836"),  # a-better-crying
    # PixAI mirror collections
    ("pixai_mirror", "civitai", "1756576"),  # PIXAI style collection
    # Checkpoint / base model
    ("checkpoint", "civitai", "827184"),  # WAI illustrious SDXL
    # ADetailer / detection (Civitai)
    ("detection", "civitai", "178518"),  # eyeful robust eye detection
    # ADetailer / detection (HuggingFace)
    ("detection", "hf", "deepghs/anime_head_detection"),
    ("detection", "hf", "Fuyucchi/yolov8_animeface"),
    ("detection", "hf", "deepghs/anime_hand_detection"),
    ("detection", "hf", "poptoz/yolo26-hand-pose-face-detection"),
    ("detection", "hf", "deepghs/AnimeText_yolo"),
    ("detection", "hf", "Kiuyha/Manga-Bubble-YOLO"),
    ("detection", "hf", "karma1jp/yolo26n-anime-segmentation"),
]

CIVITAI_API = "https://civitai.com/api/v1/models/{}"
HF_API = "https://huggingface.co/api/models/{}"

DOWNLOAD_EXTS = (".safetensors", ".pt", ".pth", ".onnx", ".ckpt", ".bin")


def _safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:140]


def _download(url: str, dest: Path, headers: dict | None = None) -> bool:
    """Stream-download with resume. Returns True on success."""
    headers = dict(headers or {})
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Fast path: dest already complete -> clean any stale .part and skip.
    if dest.exists() and dest.stat().st_size > 0:
        stale = dest.with_suffix(dest.suffix + ".part")
        if stale.exists():
            try:
                stale.unlink()
            except OSError:
                pass
        print(f"      already exists: {dest.name}")
        return True
    tmp = dest.with_suffix(dest.suffix + ".part")
    pos = tmp.stat().st_size if tmp.exists() else 0
    if pos:
        headers["Range"] = f"bytes={pos}-"
        print(f"      resume from {pos:,} bytes")
    try:
        with requests.get(
            url, headers=headers, stream=True, timeout=60, allow_redirects=True
        ) as r:
            if r.status_code == 416:  # already complete
                os.replace(tmp, dest)
                return True
            if r.status_code not in (200, 206):
                print(f"      HTTP {r.status_code}: {r.text[:200]}")
                return False
            mode = "ab" if pos and r.status_code == 206 else "wb"
            total = int(r.headers.get("content-length", 0)) + (
                pos if r.status_code == 206 else 0
            )
            done = pos if r.status_code == 206 else 0
            last_print = time.time()
            with open(tmp, mode) as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if time.time() - last_print > 2:
                        pct = (done / total * 100) if total else 0
                        print(
                            f"      {done / 1e6:.1f} MB / {total / 1e6:.1f} MB ({pct:.1f}%)"
                        )
                        last_print = time.time()
        os.replace(tmp, dest)  # atomic overwrite; handles existing dest on Windows
        size_mb = dest.stat().st_size / 1e6
        print(f"      OK -> {dest.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"      EXC: {e}")
        return False


def _filename_from_response_or_url(url: str, fallback: str) -> str:
    # try the URL path
    name = unquote(Path(urlparse(url).path).name)
    if name and "." in name:
        return name
    return fallback


def fetch_civitai(model_id: str, category: str) -> None:
    print(f"[civitai {model_id}] {category}")
    if DRY_RUN:
        print("   (dry-run)")
        return
    headers = {"Authorization": f"Bearer {CIVITAI_API_KEY}"} if CIVITAI_API_KEY else {}
    try:
        r = requests.get(CIVITAI_API.format(model_id), headers=headers, timeout=30)
    except Exception as e:
        print(f"   API error: {e}")
        return
    if r.status_code != 200:
        print(f"   API HTTP {r.status_code}: {r.text[:200]}")
        return
    data = r.json()
    versions = data.get("modelVersions") or []
    if not versions:
        print("   no versions")
        return
    v = versions[0]
    files = v.get("files") or []
    if not files:
        print("   no files in version")
        return
    # prefer primary, then largest .safetensors
    primary = next((f for f in files if f.get("primary")), None) or max(
        files, key=lambda f: f.get("sizeKB") or 0
    )
    fname = _safe_name(primary.get("name") or f"{model_id}.safetensors")
    url = primary.get("downloadUrl")
    if not url:
        print("   no downloadUrl")
        return
    dest = DEST_ROOT / category / fname
    if dest.exists():
        print(f"   already exists: {dest.name}")
        return
    print(f"   {data.get('name', '?')} :: {fname}")
    _download(url, dest, headers=headers)


def fetch_hf(repo: str, category: str) -> None:
    print(f"[hf {repo}] {category}")
    if DRY_RUN:
        print("   (dry-run)")
        return
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    try:
        r = requests.get(HF_API.format(repo), headers=headers, timeout=30)
    except Exception as e:
        print(f"   API error: {e}")
        return
    if r.status_code != 200:
        print(f"   API HTTP {r.status_code}: {r.text[:200]}")
        return
    siblings = r.json().get("siblings") or []
    targets = [
        s["rfilename"]
        for s in siblings
        if s.get("rfilename", "").lower().endswith(DOWNLOAD_EXTS)
    ]
    if not targets:
        print(f"   no model files in repo (siblings={len(siblings)})")
        return
    repo_safe = repo.replace("/", "__")
    sub = DEST_ROOT / category / repo_safe
    for fname in targets:
        url = f"https://huggingface.co/{repo}/resolve/main/{fname}"
        dest = sub / fname.replace("/", "__")
        if dest.exists():
            print(f"   already exists: {dest.name}")
            continue
        print(f"   -> {fname}")
        _download(url, dest, headers=headers)


def main() -> int:
    if not CIVITAI_API_KEY:
        print(
            "WARNING: CIVITAI_API_KEY not found in env; Civitai downloads will likely fail (login required)."
        )
    print(f"DEST_ROOT={DEST_ROOT}")
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    for category, source, ident in INVENTORY:
        if source == "civitai":
            fetch_civitai(ident, category)
        elif source == "hf":
            fetch_hf(ident, category)
        else:
            print(f"unknown source: {source}")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
