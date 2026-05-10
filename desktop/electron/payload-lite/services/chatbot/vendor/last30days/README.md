# last30days-skill vendor directory

This directory hosts the cloned [last30days-skill](https://github.com/mvanhorn/last30days-skill) engine for subprocess-based integration with AI-Assistant chatbot.

## Setup

```powershell
# Windows
.\setup.ps1

# Linux/macOS
bash setup.sh
```

The setup script clones the repo into `repo/`. That directory is git-ignored so it won't be committed.

## Requirements

- **Git** (for cloning)
- **Python 3.12+** (last30days requirement)
- **Node.js** (optional — needed for X/Twitter via vendored Bird client)

## Configuration

last30days reads its own API keys from `~/.config/last30days/.env`. See the [last30days docs](https://github.com/mvanhorn/last30days-skill#configuration) for details on per-source API keys.

The chatbot wrapper (`core/last30days_tool.py`) only needs:

| Env var | Purpose | Default |
|---|---|---|
| `LAST30DAYS_ENABLED` | Feature flag | `false` |
| `LAST30DAYS_SCRIPT_PATH` | Path to `scripts/last30days.py` | Auto-detected from vendor dir |
| `LAST30DAYS_PYTHON_PATH` | Python 3.12+ executable | `python` |
| `LAST30DAYS_TIMEOUT` | Max execution time (seconds) | `180` |

## Update

```powershell
.\setup.ps1 -Force
```
