"""CLI entry point for subsetzer-llamacpp."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import List, Optional

from .chunking import make_chunks
from .engine import DEFAULT_API_URL, translate_range
from .io import build_output_as, read_transcript
from .langs import normalise_lang
from .logging_utils import Logger
from .version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate subtitle files using a local llama.cpp server.",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        required=True,
        help="Input subtitle file (.srt/.vtt/.tsv)",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="Output file path (default: same dir as input, auto-named). "
             "Absolute path: used directly. Relative: from working directory. "
             "Existing directory: auto-named inside it.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file without prompting",
    )
    parser.add_argument(
        "--source",
        default="auto",
        help="Source language: ISO code (en, zh-cn), English name (Chinese), or 'auto' (default)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target language: ISO code (zh-cn), English name (Chinese), etc.",
    )
    parser.add_argument(
        "--format",
        choices=["srt", "vtt", "tsv"],
        default="srt",
        help="Output format (default: srt)",
    )
    parser.add_argument(
        "--cues-per-request",
        "--batch-per-chunk",
        dest="cues_per_request",
        type=int,
        default=1,
        help="Number of subtitle cues per LLM request (default: 1)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Maximum characters per chunk (default: 4000)",
    )
    parser.add_argument(
        "--no-translate-bracketed",
        dest="translate_bracketed",
        action="store_false",
        default=True,
        help="Preserve bracketed tags like [MUSIC] without translation",
    )
    parser.add_argument(
        "--host",
        dest="api_url",
        default=DEFAULT_API_URL,
        help=f"llama.cpp server URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="LLM model tag (e.g. gemma-3-12b-it)",
    )
    parser.add_argument(
        "--llm-mode",
        choices=["auto", "generate", "chat"],
        default="auto",
        help="LLM mode (default: auto)",
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
        help="HTTP timeout in seconds (default: 60)",
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
        help="Persist raw LLM payloads to {output}_raw.txt",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_output_path(args: argparse.Namespace, input_path: Path, ext: str) -> Path:
    src_iso = normalise_lang(args.source)
    dst_iso = normalise_lang(args.target)
    default_name = f"{input_path.stem}.{src_iso}2{dst_iso}.{ext}"
    cmd_out: Optional[str] = args.output_path

    if cmd_out is None:
        return input_path.with_name(default_name)

    raw = Path(cmd_out).expanduser()
    out = raw if raw.is_absolute() else Path.cwd() / raw

    if out.is_dir() or cmd_out.endswith(("/", "\\")):
        target_dir = out if out.is_dir() else out.parent
        return target_dir / default_name

    if not out.suffix or out.suffix.lstrip(".").lower() not in ("srt", "vtt", "tsv"):
        out = out.with_suffix(f".{ext}")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input_path).expanduser()
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

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

    src_iso = normalise_lang(args.source)
    dst_iso = normalise_lang(args.target)
    output_ext = args.format
    output_path = _resolve_output_path(args, input_path, output_ext)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not args.force:
        answer = input(f"Overwrite {output_path}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.", file=sys.stderr)
            return 1
    elif output_path.exists() and args.force:
        print(f"Overwriting {output_path}")

    log_path = output_path.with_suffix(".log")
    logger = Logger(file_path=log_path, verbose=args.debug)
    raw_lines: List[str] = []
    collect_raw = bool(args.capture_raw or args.debug)

    total_cues = len(transcript.cues)
    logger.log(f"Loaded transcript with {total_cues} cues in {transcript.fmt.upper()} format")
    logger.log(f"Planned {len(chunks)} chunk(s) with max {args.max_chars} chars")
    logger.log(f"Translate {src_iso} -> {dst_iso} via {args.api_url} model={args.model}")

    def raw_handler(payload: str) -> None:
        if collect_raw:
            raw_lines.append(payload)

    def show_progress(done: int, total: int) -> None:
        pct = done * 100 // total
        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
        print(f"\r  [{bar}] {pct:3d}%  {done}/{total} cues", end="", flush=True)

    show_progress(0, total_cues)

    try:
        translate_range(
            transcript,
            chunks,
            api_url=args.api_url,
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
            progress=show_progress,
        )
    except Exception as exc:
        print()
        logger.log(f"Translation failed: {exc}")
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    show_progress(total_cues, total_cues)
    print()

    timestamp = dt.datetime.now(dt.timezone.utc).astimezone()
    vtt_note = f"translated-with model={args.model} time={timestamp.isoformat()}"
    try:
        result = build_output_as(
            transcript,
            output_ext,
            vtt_note=vtt_note if output_ext == "vtt" else None,
        )
    except Exception as exc:
        logger.log(f"Failed to render output: {exc}")
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        output_path.write_text(result, encoding="utf-8")
    except OSError as exc:
        logger.log(str(exc))
        logger.close()
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    logger.log(f"Wrote {output_ext.upper()} output to {output_path}")

    if collect_raw:
        raw_path = output_path.with_name(output_path.stem + "_raw.txt")
        try:
            raw_path.write_text("\n".join(raw_lines), encoding="utf-8")
            logger.log(f"Captured raw LLM payloads in {raw_path}")
        except OSError:
            logger.log("Unable to write raw payloads")

    logger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
