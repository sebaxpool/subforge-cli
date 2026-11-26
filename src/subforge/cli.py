import argparse
from pathlib import Path
import sys

from . import __version__
from .parser import parse_srt, serialize_srt
from .processor import audit_readability, process_cues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subforge",
        description="Deterministic SRT timing optimizer.",
    )
    parser.add_argument("input", type=Path, help="Path to source .srt file")
    parser.add_argument("-o", "--output", type=Path, help="Path to output .srt file")
    parser.add_argument(
        "--shift-ms", type=int, default=0, help="Millisecond offset (+/-)"
    )
    parser.add_argument(
        "--max-width", type=int, default=42, help="Max characters per line"
    )
    parser.add_argument(
        "--max-cps", type=float, default=20.0, help="Max characters per second"
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Input file text encoding (default: utf-8-sig)",
    )
    parser.add_argument(
        "--no-reflow",
        action="store_true",
        help="Disable automatic line balancing",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Run CPS and width checks without writing",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        return 1
    if not args.input.is_file():
        print(f"Error: Input path '{args.input}' is not a file.", file=sys.stderr)
        return 1

    try:
        raw_content = args.input.read_text(encoding=args.encoding)
    except LookupError:
        print(f"Error: Unknown text encoding '{args.encoding}'.", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print(
            f"Error: Could not decode '{args.input}' using encoding '{args.encoding}'. "
            "Try specifying --encoding (e.g. cp1252).",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"Error: Could not read '{args.input}': {exc}", file=sys.stderr)
        return 1

    try:
        cues = parse_srt(raw_content)
    except ValueError as exc:
        print(f"Error: Invalid SRT content in '{args.input}': {exc}", file=sys.stderr)
        return 1

    if args.audit_only:
        try:
            issues = audit_readability(
                cues, max_cps=args.max_cps, max_width=args.max_width
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if not issues:
            print(f"OK: {len(cues)} cues checked, no readability issues found.")
            return 0

        for issue in issues:
            print(f"[Cue #{issue.cue_index}] {issue.reason}")
        return 2

    try:
        updated = process_cues(
            cues,
            shift_ms=args.shift_ms,
            max_width=args.max_width,
            reflow=not args.no_reflow,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    target = args.output or args.input.with_name(f"{args.input.stem}.forged.srt")
    try:
        target.write_text(serialize_srt(updated), encoding="utf-8")
    except OSError as exc:
        print(f"Error: Could not write '{target}': {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(updated)} cues to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
