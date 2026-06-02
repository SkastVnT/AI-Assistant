"""Run the LOCAL anime pipeline asset preflight from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from image_pipeline.anime_pipeline.preflight import main

if __name__ == "__main__":
    raise SystemExit(main())

