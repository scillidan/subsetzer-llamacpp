"""CLI entry point for subsetzer-llamacpp."""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import List, Optional

from .chunking import make_chunks
from .engine import DEFAULT_SERVER, translate_range
from .io import build_output_as, read_transcript, resolve_outfile
from .logging_utils import Logger
from .version import __version__

DEFAULT_OUTFILE_TEMPLATE = "{basename}.{dst}.{model}.{fmt}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate subtitle files using a local llama.cpp server.",
    )
    parser.add_argument("--in", dest="input_path", required=True, help="Input subtitle file (.srt/.vtt/.tsv)")
    parser.add_argument("--out", dest="output_dir", required=True, help="Output directory for generated files")
    parser.add_argument(
        "--flat",
        action="store_true",
        default=False,
        help="Write outputs directly into --out (default: timestamped folder)",
    )
    parser.add_argument("--source", default="auto", help="Source language (default: %(default)s)")
    parser.add_argument("--target", default="English", help="Target language (default: %(default)s)")
    parser.add_argument(
        "--outfmt",
        choices=["auto", "srt", "vtt", "tsv"],
        default="auto",
        help="Output format (default: %(default)s matches input)",
    )
    parser.add_argument(
        "--outfile",
        help="Output file template. Placeholders: {basename}, {src}, {dst}, {fmt}, {ts}, {model}.",
    )
    parser.add_argument(
        "--cues-per-request",
        "--batch-per-chunk",
        dest="cues_per_request",
        type=int,
        default=1,
        help="Number of subtitle cues per LLM request (default: %(default)s)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Maximum characters per chunk when planning (default: %(default)s)",
    )
    parser.add_argument(
        "--no-translate-bracketed",
        dest="translate_bracketed",
        action="store_false",
        default=True,
        help="Preserve bracketed tags like [MUSIC] without translation",
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"LLM server URL (default: {DEFAULT_SERVER})",
    )
    parser.add_argument(
        "--model",
        default="gemma3:12b",
        help="LLM model tag (default: %(default)s)",
    )
    parser.add_argument(
        "--llm-mode",
        choices=["auto", "generate", "chat"],
        default="auto",
        help="LLM mode (default: %(default)s)",
    )
    stream_group = parser.add_mutually_exclusive_group()
    stream_group.add_argument(
        "--stream",
        dest="stream",
        action="store_true",
        default=True,
        help="Enable streaming responses (default)",
    )
    stream_group.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Disable streaming responses",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM calls and reuse original text",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging and capture raw LLM responses",
    )
    parser.add_argument(
        "--capture-raw",
        action="store_true",
        help="Persist raw LLM payloads to llm_raw.txt (default: disabled)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_output_directory(base: Path, flat: bool) -> Path:
    if flat:
        base.mkdir(parents=True, exist_ok=True)
        return base
    now = dt.datetime.now()
    folder_name = now.strftime("%Y%m%d-%H%M%S")
    target = base / folder_name
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_file(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to write {path.name}: {exc}") from exc


def _language_token(label: str, fallback: str) -> str:
    cleaned = re.sub(r"[\s]+", "_", label.strip())
    cleaned = re.sub(r"[^0-9A-Za-z._-]", "-", cleaned)
    cleaned = re.sub(r"[-_]{2,}", "_", cleaned)
    result = cleaned.strip("_-.")
    return result.lower() or fallback


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input_path).expanduser()
    output_dir = Path(args.output_dir).expanduser()

    try:
        transcript = read_transcript(str(input_path))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        chunks = make_chunks(transcript.cues, args.max_chars)
    except Exception as exc:
        print(f"Error preparing chunks: {exc}", file=sys.stderr)
        return 1

    target_dir = _resolve_output_directory(output_dir, args.flat)
    log_path = target_dir / "subsetzer.log"
    logger = Logger(file_path=log_path, verbose=args.debug)
    raw_lines: List[str] = []
    collect_raw = bool(args.capture_raw or args.debug)

    logger.log(f"Loaded transcript with {len(transcript.cues)} cues in {transcript.fmt.upper()} format")
    logger.log(f"Planned {len(chunks)} chunk(s) with max {args.max_chars} characters")

    def raw_handler(payload: str) -> None:
        if collect_raw:
            raw_lines.append(payload)

    try:
        translate_range(
            transcript,
            chunks,
            server=args.server,
            model=args.model,
            source=args.source,
            target=args.target,
            batch_n=args.cues_per_request,
            translate_bracketed=args.translate_bracketed,
            llm_mode=args.llm_mode,
            stream=args.stream,
            timeout=args.timeout,
            no_llm=args.no_llm,
            logger=logger.log,
            raw_handler=raw_handler if collect_raw else None,
            verbose=args.debug,
        )
    except Exception as exc:
        logger.log(f"Translation failed: {exc}")
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    timestamp = dt.datetime.now(dt.timezone.utc).astimezone()
    vtt_note = f"translated-with model={args.model} time={timestamp.isoformat()}"
    target_fmt = args.outfmt if args.outfmt != "auto" else transcript.fmt
    try:
        result = build_output_as(
            transcript,
            target_fmt,
            vtt_note=vtt_note if target_fmt == "vtt" else None,
        )
    except Exception as exc:
        logger.log(f"Failed to render output: {exc}")
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    outfile_template = args.outfile if args.outfile else DEFAULT_OUTFILE_TEMPLATE
    template_path: str
    if outfile_template.startswith("~") or Path(outfile_template).is_absolute():
        template_path = outfile_template
    else:
        template_path = str(target_dir / outfile_template)

    try:
        output_path = resolve_outfile(
            template_path,
            input_path,
            _language_token(args.source or "auto", "auto"),
            _language_token(args.target or "unknown", "unknown"),
            target_fmt,
            model=args.model,
        )
    except Exception as exc:
        logger.log(f"Failed to resolve output path: {exc}")
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        _write_file(output_path, result)
    except Exception as exc:
        logger.log(str(exc))
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    logger.log(f"Wrote {target_fmt.upper()} output to {output_path}")

    if collect_raw:
        raw_path = target_dir / "llm_raw.txt"
        try:
            raw_path.write_text("\n".join(raw_lines), encoding="utf-8")
            logger.log(f"Captured raw LLM payloads in {raw_path}")
        except OSError:
            logger.log("Unable to write llm_raw.txt")

    logger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
