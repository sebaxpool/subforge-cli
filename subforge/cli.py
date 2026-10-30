import argparse
from pathlib import Path
import sys
from .parser import parse_srt, serialize_srt
from .processor import audit_readability, process_cues

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subforge", description="Deterministic SRT timing optimizer.")
    parser.add_argument("input", type=Path, help="Path to source .srt file")
    parser.add_argument("-o", "--output", type=Path, help="Path to output .srt file")
    parser.add_argument("--shift-ms", type=int, default=0, help="Millisecond offset (+/-)")
    parser.add_argument("--max-width", type=int, default=42, help="Max characters per line")
    parser.add_argument("--max-cps", type=float, default=20.0, help="Max characters per second")
    parser.add_argument("--no-reflow", action="store_true", help="Disable automatic line balancing")
    parser.add_argument("--audit-only", action="store_true", help="Run CPS and width checks without writing")
    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.", file=sys.stderr)
        return 1
    cues = parse_srt(args.input.read_text(encoding="utf-8"))
    if args.audit_only:
        issues = audit_readability(cues, max_cps=args.max_cps, max_width=args.max_width)
        for issue in issues:
            print(f"[Cue #{issue.cue_index}] {issue.reason}")
        return 2 if issues else 0
    updated = process_cues(cues, shift_ms=args.shift_ms, max_width=args.max_width, reflow=not args.no_reflow)
    target = args.output or args.input.with_name(f"{args.input.stem}.forged.srt")
    target.write_text(serialize_srt(updated), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
