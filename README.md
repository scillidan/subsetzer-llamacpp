# Subsetzer

![Version](https://img.shields.io/badge/version-0.1.4-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.9%2B-informational?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0--or--later-brightgreen?style=flat-square)

Local-first subtitle translation toolkit that talks to a local LLM via Ollama or llama.cpp server.  
This repository houses both the CLI package (`subsetzer`) and the Tk-based GUI wrapper (`subsetzer-gui`).  
Current version: **0.1.4**.

## Key Features
- Translate `.srt`, `.vtt`, and `.tsv` subtitle files via models served by **Ollama** or **llama.cpp server**.
- Preserve bracketed/timed markup and keep cue boundaries intact, even when a translation spans multiple lines.
- Plan work in configurable chunks to control request size and batching.
- Export to SRT, VTT (with NOTE block describing the run), or TSV with consistent naming templates.
- Choose between CLI automation or the desktop GUI, sharing the same core engine.

## Packages
| Package | Description | Entry Point |
|---------|-------------|-------------|
| `packages/subsetzer` | Core translation engine + CLI | `subsetzer` |
| `packages/subsetzer-gui` | Tk wrapper around the CLI workflow | `subsetzer-gui` |

Each package is built and released independently, but they live together so changes to the engine and GUI stay in sync.

## Installation

### From source (with uv)

```bash
git clone https://github.com/githabideri/subsetzer
cd subsetzer
uv venv --python 3.12
.venv/scripts/activate

# CLI only
uv pip install -e packages/subsetzer

# CLI + GUI
uv pip install -e packages/subsetzer -e packages/subsetzer-gui
```

Upgrade at any time with `pipx upgrade subsetzer subsetzer-gui`.

### From a local checkout (development builds)
When testing unpublished commits, build the wheels locally and install from disk:

```bash
# 1. Build wheels
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
python -m build packages/subsetzer
python -m build packages/subsetzer-gui

# 2. Install with pipx (adds commands to ~/.local/bin)
pipx install --force packages/subsetzer/dist/subsetzer-0.1.4-py3-none-any.whl
pipx install --force packages/subsetzer-gui/dist/subsetzer_gui-0.1.4-py3-none-any.whl \
  --pip-args="--no-index --find-links=$(pwd)/packages/subsetzer/dist --find-links=$(pwd)/packages/subsetzer-gui/dist"
```

### From a local checkout (with pip)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e packages/subsetzer
pip install -e packages/subsetzer-gui
```

## Quickstart
1. Copy `.env.example` to `.env` and adjust the provider, server URL, and model if needed.
2. Run a translation from the CLI:
   ```bash
   # Using Ollama (default)
   subsetzer --in path/to/source.vtt --out ./outputs --target "German"

   # Using llama.cpp server
   subsetzer --in path/to/source.vtt --out ./outputs --target "German" --provider llamacpp --server http://127.0.0.1:8080
   ```
3. Or launch the GUI:
   ```bash
   subsetzer-gui
   ```
   Pick the input file, output directory, adjust options, then click **Build/Update chunks** followed by **Translate ALL**.

Outputs are written to the chosen directory; VTT exports include a NOTE block capturing the model and timestamp.

![Subsetzer GUI screenshot](subsetzer-gui-1.png)

## Configuration
The CLI and GUI honour `SUBSETZER_*` environment variables. Populate `.env` and `source` it before running:

```
SUBSETZER_LLM_PROVIDER=ollama
SUBSETZER_LLM_SERVER=http://127.0.0.1:11434
SUBSETZER_LLM_MODEL=gemma3:12b
SUBSETZER_LLM_MODE=auto
SUBSETZER_STREAM=true
SUBSETZER_HTTP_TIMEOUT=60
SUBSETZER_CUES_PER_REQUEST=4
```

Set `SUBSETZER_LLM_PROVIDER` to `ollama` (default) or `llamacpp`. When using llama.cpp server, the default port is 8080 and the API endpoints follow the OpenAI-compatible format (`/v1/chat/completions`, `/v1/completions`).

Legacy `HOMEDOC_*` names are still accepted for compatibility.

### Provider notes
- **Ollama** — uses `/api/chat` and `/api/generate` endpoints. Default server: `http://127.0.0.1:11434`.
- **llama.cpp server** — uses `/v1/chat/completions` and `/v1/completions` (OpenAI-compatible). Default server: `http://127.0.0.1:8080`.

### Model notes
- Larger Ollama models (e.g. `gemma3:12b`) handled long-form VTTs reliably in end-to-end tests.
- Smaller checkpoints such as `gemma3:4b` frequently echoed the source text even after Subsetzer’s fallback retries; expect to babysit outputs or pick a more capable model if accurate translations are required.

## Usage Details
- **CLI**: batch translation flags (`--cues-per-request`, `--max-chars`), output templating, retries, logging, and environment variables are documented in [USAGE.md](USAGE.md#cli-subsetzer).
- **GUI**: step-by-step walkthrough, screenshot, and tips live in [USAGE.md](USAGE.md#gui-subsetzer-gui).
- **Outputs & troubleshooting**: see [USAGE.md](USAGE.md#outputs).

## Development
```bash
source .venv/bin/activate
# install dev dependencies
pip install -e packages/subsetzer -e packages/subsetzer-gui
pip install pytest
```

- Run CLI in-place: `PYTHONPATH=packages/subsetzer/src python -m subsetzer.cli …`
- Launch GUI in-place: `PYTHONPATH=packages/subsetzer/src:packages/subsetzer-gui/src python -m subsetzer_gui.app`
- Build wheels: `python -m build packages/subsetzer` and `python -m build packages/subsetzer-gui`

## Testing
```
source .venv/bin/activate
PYTHONPATH=packages/subsetzer/src python -m pytest packages/subsetzer/tests
PYTHONPATH=packages/subsetzer/src:packages/subsetzer-gui/src python -m pytest packages/subsetzer-gui/tests
```

## Releases
GitHub Actions publishes tagged releases to PyPI:
- Tag `subsetzer-vX.Y.Z` to publish the CLI package.
- Tag `subsetzer-gui-vX.Y.Z` to publish the GUI.

Ensure wheels are built and verified locally (`python -m build ...`) before tagging. See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Repository Layout
```
.
├── packages/
│   ├── subsetzer/        # Core CLI package (stdlib-only)
│   └── subsetzer-gui/    # Tk GUI wrapper
├── outputs/              # Sample translation runs (ignored by git)
├── local/                # Local sandbox assets (ignored)
├── .github/workflows/    # Release automation
└── README.md
```

## License
Both packages are licensed under the GPL-3.0-or-later; see `packages/subsetzer/LICENSE` and `packages/subsetzer-gui/LICENSE`.
