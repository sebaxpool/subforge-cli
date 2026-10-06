from dataclasses import dataclass
import re

TIMECODE_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")

@dataclass(frozen=True, order=True)
class Timecode:
    total_ms: int

    @classmethod
    def from_srt(cls, raw: str) -> "Timecode":
        match = TIMECODE_PATTERN.match(raw.strip())
        if not match:
            raise ValueError(f"Invalid SRT timecode format: {raw}")
        hours, minutes, seconds, millis = map(int, match.groups())
        total = (((hours * 60 + minutes) * 60) + seconds) * 1000 + millis
        return cls(total_ms=total)

    def to_srt(self) -> str:
        clamped = max(0, self.total_ms)
        hours, rem = divmod(clamped, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    def shifted(self, offset_ms: int) -> "Timecode":
        return Timecode(max(0, self.total_ms + offset_ms))

@dataclass
class SubtitleCue:
    index: int
    start: Timecode
    end: Timecode
    text: str

    @property
    def duration_ms(self) -> int:
        return max(1, self.end.total_ms - self.start.total_ms)

    @property
    def clean_char_count(self) -> int:
        stripped = re.sub(r"<[^>]+>", "", self.text)
        return len(stripped.replace("\n", ""))

    @property
    def cps(self) -> float:
        return (self.clean_char_count * 1000.0) / self.duration_ms

    def to_srt_block(self) -> str:
        return f"{self.index}\n{self.start.to_srt()} --> {self.end.to_srt()}\n{self.text.strip()}\n"
