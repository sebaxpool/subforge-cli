import textwrap
from collections.abc import Sequence
from dataclasses import dataclass

from .models import HTML_TAG_PATTERN, SubtitleCue


@dataclass(frozen=True)
class AuditIssue:
    cue_index: int
    cps: float
    line_length: int
    reason: str


def _balance_single_block(text: str, max_width: int) -> str:
    flat = " ".join(text.split())
    if len(flat) <= max_width or " " not in flat:
        return flat

    best_split = -1
    min_diff = len(flat) + 1
    for idx, char in enumerate(flat):
        if char != " ":
            continue
        left_len = idx
        right_len = len(flat) - idx - 1
        if left_len <= max_width and right_len <= max_width:
            diff = abs(left_len - right_len)
            if diff < min_diff:
                min_diff = diff
                best_split = idx

    if best_split != -1:
        return f"{flat[:best_split]}\n{flat[best_split + 1 :]}"

    return "\n".join(
        textwrap.wrap(
            flat,
            width=max_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def balance_lines(text: str, max_width: int = 42) -> str:
    if max_width < 1:
        raise ValueError(f"max_width must be >= 1, got {max_width}")

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not raw_lines:
        return ""

    is_dialogue = len(raw_lines) >= 2 and any(line.startswith("-") for line in raw_lines[1:])
    if is_dialogue:
        turns: list[list[str]] = []
        for line in raw_lines:
            if line.startswith("-") or not turns:
                turns.append([line])
            else:
                turns[-1].append(line)
        return "\n".join(_balance_single_block(" ".join(turn), max_width) for turn in turns)

    return _balance_single_block(" ".join(raw_lines), max_width)


def process_cues(
    cues: Sequence[SubtitleCue],
    shift_ms: int = 0,
    max_width: int = 42,
    reflow: bool = True,
) -> list[SubtitleCue]:
    if max_width < 1:
        raise ValueError(f"max_width must be >= 1, got {max_width}")

    processed: list[SubtitleCue] = []
    for cue in cues:
        if cue.end.total_ms + shift_ms <= 0:
            continue
        new_start = cue.start.shifted(shift_ms)
        new_end = cue.end.shifted(shift_ms)
        new_text = balance_lines(cue.text, max_width=max_width) if reflow else cue.text
        processed.append(
            SubtitleCue(
                index=len(processed) + 1,
                start=new_start,
                end=new_end,
                text=new_text,
            )
        )
    return processed


def audit_readability(
    cues: Sequence[SubtitleCue],
    max_cps: float = 20.0,
    max_width: int = 42,
) -> list[AuditIssue]:
    if max_cps <= 0:
        raise ValueError(f"max_cps must be > 0, got {max_cps}")
    if max_width < 1:
        raise ValueError(f"max_width must be >= 1, got {max_width}")

    issues: list[AuditIssue] = []
    for cue in cues:
        longest = max(
            (len(HTML_TAG_PATTERN.sub("", line)) for line in cue.text.splitlines()),
            default=0,
        )
        cps_value = round(cue.cps, 2)
        reasons: list[str] = []
        if cps_value > max_cps:
            reasons.append(f"CPS {cps_value:.2f} exceeds limit {max_cps:.2f}")
        if longest > max_width:
            reasons.append(f"Line width {longest} exceeds {max_width} chars")
        if reasons:
            issues.append(
                AuditIssue(
                    cue_index=cue.index,
                    cps=cps_value,
                    line_length=longest,
                    reason="; ".join(reasons),
                )
            )
    return issues
