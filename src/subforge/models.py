import re
from dataclasses import dataclass

TIMECODE_PATTERN = re.compile(r"^(\d{2,}):(\d{2}):(\d{2}),(\d{3})$")
HTML_TAG_PATTERN = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^<>]*)?/?>")


@dataclass(frozen=True, order=True)
class Timecode:
    total_ms: int

    def __post_init__(self) -> None:
        if isinstance(self.total_ms, bool) or not isinstance(self.total_ms, int):
            raise TypeError("total_ms must be an int")
        if self.total_ms < 0:
            raise ValueError(f"Timecode cannot be negative: {self.total_ms}")

    @classmethod
    def from_srt(cls, raw: str) -> "Timecode":
        match = TIMECODE_PATTERN.match(raw.strip())
        if not match:
            raise ValueError(f"Invalid SRT timecode format: {raw}")
        hours, minutes, seconds, millis = map(int, match.groups())
        if minutes >= 60 or seconds >= 60:
            raise ValueError(f"Minutes and seconds must be between 00 and 59: {raw}")
        total = (((hours * 60 + minutes) * 60) + seconds) * 1000 + millis
        return cls(total_ms=total)

    def to_srt(self) -> str:
        hours, rem = divmod(self.total_ms, 3_600_000)
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

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError(f"Cue index must be >= 1, got {self.index}")
        if self.end <= self.start:
            raise ValueError(
                f"Cue end ({self.end.to_srt()}) must be after start ({self.start.to_srt()})"
            )

    @property
    def duration_ms(self) -> int:
        return self.end.total_ms - self.start.total_ms

    @property
    def clean_char_count(self) -> int:
        stripped = HTML_TAG_PATTERN.sub("", self.text)
        return len(stripped.replace("\r", "").replace("\n", ""))

    @property
    def cps(self) -> float:
        return (self.clean_char_count * 1000.0) / self.duration_ms

    def to_srt_block(self) -> str:
        return f"{self.index}\n{self.start.to_srt()} --> {self.end.to_srt()}\n{self.text.strip()}\n"
