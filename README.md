# SubForge CLI

[![CI](https://github.com/sebaxpool/subforge-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/sebaxpool/subforge-cli/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

Deterministic, zero-dependency Python CLI tool to audit, time-shift, and re-balance `.srt` subtitle files for video post-production workflows.

## Key Features

- **Millisecond-Accurate Timecodes:** Immutable integer-millisecond `Timecode` model eliminates floating-point drift during batch offsets and supports durations beyond 99 hours.
- **Strict Fail-Fast SRT Parsing:** Rejects malformed timing headers, invalid ranges (`end <= start`), and corrupted files while gracefully handling UTF-8 BOM, `\r\n`/legacy `\r` endings, and empty-dialogue blocks.
- **HTML-Aware Readability Audit:** Measures visible characters per second (CPS) and line width after stripping markup tags (such as `<i>` or `<font>`), avoiding false positives.
- **Dialogue-Aware Balanced Reflow:** Preserves hyphen-prefixed dialogue turns (`- `), picks balanced two-line splits within `max_width`, and wraps longer cues cleanly with `textwrap`.
- **Clean Negative Shifts:** Drops cues ending at or before `00:00:00,000`, clamps partially overlapping cues to zero, and reindexes sequentially from `1`.
- **Zero Runtime Dependencies:** Built strictly on the Python 3.10+ standard library (`dataclasses`, `re`, `textwrap`, `argparse`, `pathlib`).

## Installation

```bash
git clone [https://github.com/sebaxpool/subforge-cli.git](https://github.com/sebaxpool/subforge-cli.git)
cd subforge-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For local development (includes `pytest`, `hypothesis`, and `ruff`):

```bash
pip install -e ".[dev]"
```

## Usage

Shift timing by `+450 ms` and re-balance lines to 42 characters max:

```bash
subforge movie.srt -o movie.synced.srt --shift-ms 450 --max-width 42
```

Run a non-destructive readability audit (default limits: `20.0` CPS, `42` chars/line):

```bash
subforge movie.srt --audit-only --max-cps 18.5 --max-width 42
```

Shift timing without modifying existing line breaks:

```bash
subforge movie.srt --shift-ms -2500 --no-reflow
```

Process legacy non-UTF-8 subtitle files (e.g., Windows `cp1252`):

```bash
subforge legacy.srt --encoding cp1252 -o legacy.utf8.srt
```

Check the installed version:

```bash
subforge --version
```

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Success (file written cleanly, or `--audit-only` found zero issues). |
| `1` | Input, encoding, parsing, parameter, or file-write error (details printed to `stderr`). |
| `2` | `--audit-only` detected one or more CPS or line-width violations. |

## Architecture

The package uses a decoupled `src/` layout separating domain invariants, I/O, transformations, and CLI orchestration:

```text
src/subforge/
├── models.py      # Immutable Timecode and SubtitleCue invariants & HTML-stripped metrics
├── parser.py      # Strict SRT parsing (BOM/CRLF/CR normalization) and safe serialization
├── processor.py   # Dialogue-aware line balancing, time shifting, and readability audits
└── cli.py         # Argument parsing, encoding/I/O error handling, and exit codes
```

## Testing & Code Quality

The test suite combines unit tests, end-to-end CLI tests (`tmp_path` + `capsys`), and property-based invariants using `hypothesis` (86 tests verified across Python 3.10, 3.12, and 3.14 in GitHub Actions).

```bash
pytest -v
ruff check .
ruff format --check .
```

## Roadmap

- **`v0.4.0` — Advanced Audits & Sync:** Overlap/minimum-gap detection between consecutive cues, linear framerate conversion (e.g., `23.976` to `25 fps`), and optional SDH tag stripping (`[music]`, `(laughs)`).
- **`v0.5.0` — Multi-Format & Batch Pipelines:** WebVTT (`.vtt`) and JSON export backed by the existing domain layer, directory batch processing, and bilingual SRT merging.
- **`v0.6.0` — Production Packaging:** Strict `mypy` type checking and `pytest-cov` reporting in CI, project-level config files, and PyPI package publishing.

## License

MIT — see [LICENSE](LICENSE) for details.
