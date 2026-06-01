"""Local registry for repeatable character identity packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from image_pipeline.paths import CONFIGS_DIR

_DEFAULT_PATH = CONFIGS_DIR / "character_packs.yaml"


def _norm(value: str) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True)
class CharacterPack:
    key: str
    display_name: str = ""
    series: str = ""
    aliases: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()
    prompt_alias: str = ""
    base_model: str = ""
    trigger_words: tuple[str, ...] = ()
    loras: tuple[dict[str, Any], ...] = ()
    adult_verified: bool = False
    checksums: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CharacterPack":
        return cls(
            key=str(raw.get("key", "")),
            display_name=str(raw.get("display_name", "")),
            series=str(raw.get("series", "")),
            aliases=tuple(str(v) for v in raw.get("aliases", []) if v),
            refs=tuple(str(v) for v in raw.get("refs", []) if v),
            prompt_alias=str(raw.get("prompt_alias", "")),
            base_model=str(raw.get("base_model", "")),
            trigger_words=tuple(str(v) for v in raw.get("trigger_words", []) if v),
            loras=tuple(v for v in raw.get("loras", []) if isinstance(v, dict)),
            adult_verified=bool(raw.get("adult_verified", False)),
            checksums={
                str(k): str(v)
                for k, v in (raw.get("checksums", {}) or {}).items()
                if k and v
            },
        )


def load_character_packs(path: str | Path | None = None) -> dict[str, CharacterPack]:
    registry_path = Path(path) if path else _DEFAULT_PATH
    if not registry_path.exists():
        return {}
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    packs = raw.get("packs", []) if isinstance(raw, dict) else []
    result: dict[str, CharacterPack] = {}
    for item in packs:
        if not isinstance(item, dict) or not item.get("key"):
            continue
        pack = CharacterPack.from_dict(item)
        for alias in (pack.key, pack.display_name, *pack.aliases):
            if alias:
                result[_norm(alias)] = pack
    return result


def get_character_pack(
    character_key: str, path: str | Path | None = None
) -> CharacterPack | None:
    return load_character_packs(path).get(_norm(character_key))


def character_is_adult_verified(
    character_key: str, path: str | Path | None = None
) -> bool:
    pack = get_character_pack(character_key, path)
    return bool(pack and pack.adult_verified)

