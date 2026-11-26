import re
from collections.abc import Sequence

from .models import SubtitleCue, Timecode

BLOCK_SPLIT_REGEX = re.compile(r"\n(?:[ \t]*\n)+")
HEADER_REGEX = re.compile(r"^(\d{2,}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2,}:\d{2}:\d{2},\d{3})$")


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _sanitize_cue_text(text: str) -> str:
    normalized = _normalize_newlines(text)
    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    return "\n".join(lines)


def parse_srt(content: str) -> list[SubtitleCue]:
    normalized = _normalize_newlines(content).lstrip("\ufeff").strip()
    if not normalized:
        return []

    raw_blocks = BLOCK_SPLIT_REGEX.split(normalized)
    cues: list[SubtitleCue] = []

    for fallback_idx, block in enumerate(raw_blocks, start=1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        header_line_idx = 1 if lines[0].isdigit() else 0
        if header_line_idx >= len(lines):
            raise ValueError(f"Malformed SRT block {fallback_idx}: missing timing header")

        header_line = lines[header_line_idx]
        match = HEADER_REGEX.match(header_line)
        if not match:
            raise ValueError(f"Malformed timing header in block {fallback_idx}: {header_line!r}")

        start_tc = Timecode.from_srt(match.group(1))
        end_tc = Timecode.from_srt(match.group(2))
        if end_tc <= start_tc:
            raise ValueError(
                f"Cue end ({end_tc.to_srt()}) must be after start ({start_tc.to_srt()}) "
                f"in block {fallback_idx}"
            )

        payload_lines = lines[header_line_idx + 1 :]
        if not payload_lines:
            continue

        payload = "\n".join(payload_lines)
        cues.append(
            SubtitleCue(
                index=len(cues) + 1,
                start=start_tc,
                end=end_tc,
                text=payload,
            )
        )

    return cues


def serialize_srt(cues: Sequence[SubtitleCue]) -> str:
    reindexed: list[SubtitleCue] = []
    for cue in cues:
        clean_text = _sanitize_cue_text(cue.text)
        if not clean_text:
            continue
        reindexed.append(
            SubtitleCue(
                index=len(reindexed) + 1,
                start=cue.start,
                end=cue.end,
                text=clean_text,
            )
        )
    return "\n".join(cue.to_srt_block() for cue in reindexed)
