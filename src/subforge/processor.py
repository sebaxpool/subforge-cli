from dataclasses import dataclass
from typing import List
from .models import SubtitleCue

@dataclass(frozen=True)
class AuditIssue:
    cue_index: int
    cps: float
    line_length: int
    reason: str

def balance_lines(text: str, max_width: int = 42) -> str:
    flat = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(flat) <= max_width or " " not in flat:
        return flat
    midpoint = len(flat) // 2
    best_split = -1
    min_distance = len(flat)
    for idx, char in enumerate(flat):
        if char == " ":
            distance = abs(idx - midpoint)
            if distance < min_distance:
                min_distance = distance
                best_split = idx
    if best_split == -1:
        return flat
    return f"{flat[:best_split].strip()}\n{flat[best_split + 1 :].strip()}"

def process_cues(cues: List[SubtitleCue], shift_ms: int = 0, max_width: int = 42, reflow: bool = True) -> List[SubtitleCue]:
    processed: List[SubtitleCue] = []
    for cue in cues:
        new_start = cue.start.shifted(shift_ms)
        new_end = cue.end.shifted(shift_ms)
        if new_end.total_ms <= new_start.total_ms:
            new_end = new_start.shifted(500)
        new_text = balance_lines(cue.text, max_width=max_width) if reflow else cue.text
        processed.append(SubtitleCue(index=cue.index, start=new_start, end=new_end, text=new_text))
    return processed

def audit_readability(cues: List[SubtitleCue], max_cps: float = 20.0, max_width: int = 42) -> List[AuditIssue]:
    issues: List[AuditIssue] = []
    for cue in cues:
        longest = max((len(line) for line in cue.text.splitlines()), default=0)
        reasons = []
        if cue.cps > max_cps:
            reasons.append(f"CPS {cue.cps:.1f} exceeds limit {max_cps:.1f}")
        if longest > max_width:
            reasons.append(f"Line width {longest} exceeds {max_width} chars")
        if reasons:
            issues.append(AuditIssue(cue_index=cue.index, cps=round(cue.cps, 2), line_length=longest, reason="; ".join(reasons)))
    return issues
