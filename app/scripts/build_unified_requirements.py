from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from packaging.requirements import InvalidRequirement, Requirement
import tomllib


ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "requirements" / "requirements_unified_3119.txt"


@dataclass(frozen=True)
class DepEntry:
    key: str
    requirement: str
    source: str
    priority: int


def normalize_key(req: str) -> str:
    try:
        parsed = Requirement(req)
        name = parsed.name
    except InvalidRequirement:
        name = req.split(";")[0].strip()
        if "[" in name:
            name = name.split("[", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", "!=", "===", "<", ">"):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
                break
    return re.sub(r"[-_.]+", "-", name).lower()


def looks_like_requirement(line: str) -> bool:
    if not line:
        return False
    if line.startswith("#"):
        return False
    if line.startswith(("-r", "--requirement", "-c", "--constraint", "--")):
        return False
    if "://" in line:
        return True
    return any(ch.isalpha() for ch in line)


def parse_requirements_file(path: Path) -> Iterable[str]:
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].strip()
        if not looks_like_requirement(line):
            continue
        yield line


def parse_pyproject(path: Path) -> Iterable[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))
    project = data.get("project", {})
    for dep in project.get("dependencies", []) or []:
        dep = str(dep).strip()
        if dep:
            yield dep
    optional = project.get("optional-dependencies", {}) or {}
    for dep_list in optional.values():
        for dep in dep_list or []:
            dep = str(dep).strip()
            if dep:
                yield dep


def parse_environment_yaml(path: Path) -> Iterable[str]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_pip = False
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- pip:"):
            in_pip = True
            continue
        if in_pip and line.startswith("  - "):
            dep = stripped[2:].strip()
            if dep:
                yield dep
            continue
        if in_pip and not line.startswith("  "):
            in_pip = False


def discover_venv_dirs() -> list[Path]:
    venvs: list[Path] = []
    for cfg in ROOT.rglob("pyvenv.cfg"):
        p = cfg.parent
        parts = {part.lower() for part in p.parts}
        if "site-packages" in parts:
            continue
        venvs.append(p)
    deduped = sorted(set(venvs), key=lambda x: str(x).lower())
    return deduped


def pip_freeze_from_venv(venv_dir: Path) -> Iterable[str]:
    py = venv_dir / "Scripts" / "python.exe"
    if not py.exists():
        return []
    try:
        result = subprocess.run(
            [str(py), "-m", "pip", "freeze"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> None:
    entries: dict[str, DepEntry] = {}
    passthrough: set[str] = set()

    def add_dep(req: str, source: str, priority: int) -> None:
        req = req.strip()
        if not req:
            return
        if req.startswith(("git+", "http://", "https://")):
            passthrough.add(req)
            return
        key = normalize_key(req)
        existing = entries.get(key)
        if existing is None or priority < existing.priority:
            entries[key] = DepEntry(key=key, requirement=req, source=source, priority=priority)

    req_files = [
        p
        for p in ROOT.rglob("*.txt")
        if "requirement" in p.name.lower()
        and not any(part.lower() in {".venv", "venv", "env", "site-packages", "node_modules", "__pycache__"} for part in p.parts)
    ]
    for path in sorted(req_files, key=lambda x: str(x).lower()):
        rel = path.relative_to(ROOT)
        for dep in parse_requirements_file(path):
            add_dep(dep, source=f"requirements:{rel}", priority=3)

    for path in sorted(ROOT.rglob("pyproject.toml"), key=lambda x: str(x).lower()):
        if any(part.lower() in {".venv", "venv", "env", "site-packages", "node_modules", "__pycache__"} for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        for dep in parse_pyproject(path):
            add_dep(dep, source=f"pyproject:{rel}", priority=4)

    for path in sorted(ROOT.rglob("environment*.y*ml"), key=lambda x: str(x).lower()):
        if any(part.lower() in {".venv", "venv", "env", "site-packages", "node_modules", "__pycache__"} for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        for dep in parse_environment_yaml(path):
            add_dep(dep, source=f"env-yaml:{rel}", priority=5)

    for venv in discover_venv_dirs():
        rel = venv.relative_to(ROOT)
        for dep in pip_freeze_from_venv(venv):
            add_dep(dep, source=f"venv:{rel}", priority=1)

    lines = [
        "# Auto-generated unified requirements for Python 3.11.9",
        "# Source precedence: existing venv freeze > requirements files > pyproject > environment yaml",
        "",
    ]
    for req in sorted(passthrough):
        lines.append(req)
    if passthrough:
        lines.append("")
    for entry in sorted(entries.values(), key=lambda e: e.key):
        lines.append(entry.requirement)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"Total unique dependencies: {len(entries) + len(passthrough)}")


if __name__ == "__main__":
    main()
