# Subsetzer-llamacpp

![Version](https://img.shields.io/badge/version-0.2.0-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.9%2B-informational?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0--or--later-brightgreen?style=flat-square)

CLI tool to translate `.srt`, `.vtt`, and `.tsv` subtitle files using a local [llama.cpp server](https://github.com/ggml-org/llama.cpp). Stdlib-only core, no external dependencies.

## Key Features

- Translate subtitles via a local llama.cpp server (OpenAI-compatible API)
- Preserve bracketed markup (`[MUSIC]`, stage directions) and cue boundaries
- Configurable chunk planning and batching for large files
- Export to SRT, VTT, or TSV with consistent naming templates
- Automatic per-cue retry with neighbouring context when batch translations fail

## Install

```bash
git clone https://github.com/githabideri/subsetzer.git
cd subsetzer
uv venv --python 3.12
.venv/scripts/activate
uv pip install -e .
```

## Quickstart

```bash
subsetzer-llamacpp --in movie.vtt --out ./results --target "German"
```

- `--in` — input subtitle file (`.srt` / `.vtt` / `.tsv`)
- `--out` — output directory; creates a timestamped subfolder unless `--flat` is given
- `--target` — target language (`--source` defaults to `auto`)

## Usage Details

### Server & Model

```bash
subsetzer-llamacpp \
  --in movie.srt \
  --out ./translations \
  --server http://127.0.0.1:8080 \
  --model my-model \
  --target "German"
```

### Format & Output

- `--outfmt auto|srt|vtt|tsv` — force output format (default: matches input)
- `--outfile "{basename}.{dst}.{model}.{fmt}"` — output file name template with placeholders: `{basename}`, `{src}`, `{dst}`, `{fmt}`, `{ts}`, `{model}`
- `--flat` — write directly into `--out` instead of a timestamped folder

### Chunking & Batching

- `--max-chars N` — max characters per chunk (default `4000`)
- `--cues-per-request N` — cues per LLM request (default `1`)

### Options

- `--no-translate-bracketed` — preserve `[MUSIC]` and similar tags
- `--stream` / `--no-stream` — toggle streaming (default: on)
- `--timeout SECS` — HTTP timeout (default `60`)
- `--no-llm` — dry-run, reuse source text as output
- `--debug` — verbose logging + capture raw LLM payloads
- `--capture-raw` — save raw LLM payloads to `llm_raw.txt`
- `--llm-mode auto|chat|generate` — API endpoint mode

### Model Notes

Larger models (12B+ parameters) produce more reliable translations. Smaller checkpoints often echo source text despite automatic retries.
