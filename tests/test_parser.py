import pytest
from hypothesis import given
from hypothesis import strategies as st

from subforge.models import SubtitleCue, Timecode
from subforge.parser import parse_srt, serialize_srt


class TestParseSrt:
    @pytest.mark.parametrize("raw", ["", "   \n\t\r\n  ", "\ufeff   "])
    def test_empty_or_whitespace_returns_empty_list(self, raw: str) -> None:
        assert parse_srt(raw) == []

    def test_handles_bom_crlf_and_legacy_cr(self) -> None:
        raw = (
            "\ufeff1\r\n"
            "00:00:01,000 --> 00:00:02,500\r\n"
            "Primera línea\r\n"
            "Segunda línea\r\n\r\n"
            "2\r"
            "00:00:03,000 --> 00:00:04,000\r"
            "Con CR antiguo"
        )
        cues = parse_srt(raw)
        assert len(cues) == 2
        assert cues[0] == SubtitleCue(
            1, Timecode(1000), Timecode(2500), "Primera línea\nSegunda línea"
        )
        assert cues[1] == SubtitleCue(2, Timecode(3000), Timecode(4000), "Con CR antiguo")

    def test_skips_blocks_without_dialogue_and_reindexes(self) -> None:
        raw = (
            "10\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Hola\n\n"
            "11\n"
            "00:00:03,000 --> 00:00:04,000\n\n"
            "99\n"
            "00:00:05,000 --> 00:00:06,000\n"
            "Chao\n"
        )
        cues = parse_srt(raw)
        assert len(cues) == 2
        assert [c.index for c in cues] == [1, 2]
        assert [c.text for c in cues] == ["Hola", "Chao"]

    def test_accepts_blocks_without_numeric_index_and_over_100_hours(self) -> None:
        raw = "120:00:00,000 --> 120:00:02,000\nMaratón larga"
        cues = parse_srt(raw)
        assert cues == [
            SubtitleCue(1, Timecode(432_000_000), Timecode(432_002_000), "Maratón larga")
        ]

    @pytest.mark.parametrize(
        "bad_srt",
        [
            "Hola, esto no es un SRT",
            "1",
            "1\n00:00:01,000 --> 00:00:02,000999\nMilisegundos extra",
            "1\n00:00:01,000 --> 00:00:02,000 X1:40\nTexto extra en header",
            "1\n00:00:01.000 --> 00:00:02.000\nPuntos en vez de comas",
            "1\n00:99:00,000 --> 00:99:01,000\nMinutos imposibles",
            "1\n00:00:05,000 --> 00:00:02,000\nFin antes de inicio",
            "1\n00:00:05,000 --> 00:00:05,000\nDuración cero",
        ],
    )
    def test_rejects_malformed_srt(self, bad_srt: str) -> None:
        with pytest.raises(ValueError):
            parse_srt(bad_srt)


class TestSerializeSrt:
    def test_reindexes_sanitizes_blank_lines_and_skips_empty_cues(self) -> None:
        cues = [
            SubtitleCue(5, Timecode(0), Timecode(1000), "  Hola \r\n\r\n Mundo  "),
            SubtitleCue(8, Timecode(2000), Timecode(3000), "   \n\t  "),
            SubtitleCue(12, Timecode(4000), Timecode(5000), "Final"),
        ]
        serialized = serialize_srt(cues)
        reparsed = parse_srt(serialized)
        assert reparsed == [
            SubtitleCue(1, Timecode(0), Timecode(1000), "Hola\nMundo"),
            SubtitleCue(2, Timecode(4000), Timecode(5000), "Final"),
        ]

    def test_serialize_empty_returns_empty_string(self) -> None:
        assert serialize_srt([]) == ""


_clean_line = (
    st.text(
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
        min_size=1,
        max_size=40,
    )
    .map(str.strip)
    .filter(bool)
)

_cue_strategy = st.builds(
    lambda start_ms, duration_ms, lines: SubtitleCue(
        index=1,
        start=Timecode(start_ms),
        end=Timecode(start_ms + duration_ms),
        text="\n".join(lines),
    ),
    start_ms=st.integers(min_value=0, max_value=500_000_000),
    duration_ms=st.integers(min_value=1, max_value=60_000),
    lines=st.lists(_clean_line, min_size=1, max_size=3),
)


class TestParserProperties:
    @given(cues=st.lists(_cue_strategy, max_size=15))
    def test_serialize_parse_roundtrip_preserves_cues(self, cues: list[SubtitleCue]) -> None:
        serialized = serialize_srt(cues)
        reparsed = parse_srt(serialized)
        expected = [
            SubtitleCue(index=i, start=c.start, end=c.end, text=c.text)
            for i, c in enumerate(cues, start=1)
        ]
        assert reparsed == expected
        assert serialize_srt(reparsed) == serialized
