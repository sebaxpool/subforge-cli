# SubForge CLI - Deterministic SRT Timing and Readability Processor

SubForge is a zero-dependency Python command-line utility engineered to lint, time-shift, and re-balance .srt subtitle files for video post-production workflows.

## Key Engineering Features

* **Millisecond-Accurate Timecode Arithmetic:** Custom Timecode data structure avoids floating-point drift during batch offset operations.
* **Readability Linting (CPS):** Flags subtitle cues that exceed ergonomic reading speeds (default 20.0 CPS).
* **Balanced Line Reflow:** Splits overlong single-line cues into balanced two-line blocks using word-boundary heuristics.
* **Zero External Dependencies:** Built strictly on the Python 3.10+ standard library (dataclasses, re, argparse, pathlib).

## Terminal Usage

    python -m subforge.cli input.srt -o output.srt --shift-ms 450 --max-width 42
    python -m subforge.cli input.srt --audit-only --max-cps 18.5

## Roadmap

- [ ] Add WebVTT (.vtt) and ASS (.ass) bidirectional conversion.
- [ ] Implement gap-closing pass between consecutive cues (<120ms).
- [ ] Add JSON report export for automated media pipelines.
