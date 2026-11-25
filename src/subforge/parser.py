import re
from typing import List
from .models import SubtitleCue, Timecode

BLOCK_SPLIT_REGEX = re.compile(r"\n\s*\n")
HEADER_REGEX = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")

def parse_srt(content: str) -> List[SubtitleCue]:
    normalized = content.replace("\r\n", "\n").lstrip("\ufeff").strip()
    if not normalized:
        return []
    raw_blocks = BLOCK_SPLIT_REGEX.split(normalized)
    cues: List[SubtitleCue] = []
    for fallback_idx, block in enumerate(raw_blocks, start=1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue
        header_line_idx = 1 if lines[0].isdigit() else 0
        if header_line_idx >= len(lines):
            continue
        match = HEADER_REGEX.match(lines[header_line_idx])
        if not match:
            raise ValueError(f"Malformed timing header in block {fallback_idx}")
        start_tc = Timecode.from_srt(match.group(1))
        end_tc = Timecode.from_srt(match.group(2))
        payload = "\n".join(lines[header_line_idx + 1 :])
        cues.append(SubtitleCue(index=len(cues) + 1, start=start_tc, end=end_tc, text=payload))
    return cues

def serialize_srt(cues: List[SubtitleCue]) -> str:
    reindexed = [SubtitleCue(index=i, start=c.start, end=c.end, text=c.text) for i, c in enumerate(cues, start=1)]
    return "\n".join(cue.to_srt_block() for cue in reindexed)
