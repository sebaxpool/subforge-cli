from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given
from hypothesis import strategies as st

from subforge.models import SubtitleCue, Timecode


class TestTimecode:
    @pytest.mark.parametrize("invalid_ms", [-1, -5000])
    def test_rejects_negative_milliseconds(self, invalid_ms: int) -> None:
        with pytest.raises(ValueError, match="negative"):
            Timecode(invalid_ms)

    @pytest.mark.parametrize("invalid_value", [True, False, "1000", 12.5, None])
    def test_rejects_non_int_and_bool(self, invalid_value: object) -> None:
        with pytest.raises(TypeError, match="must be an int"):
            Timecode(invalid_value)  # type: ignore[arg-type]

    def test_is_immutable(self) -> None:
        tc = Timecode(1000)
        with pytest.raises(FrozenInstanceError):
            tc.total_ms = 2000  # type: ignore[misc]

    @pytest.mark.parametrize(
        ("raw", "expected_ms"),
        [
            ("00:00:00,000", 0),
            ("00:01:02,345", 62_345),
            ("  01:59:59,999  ", 7_199_999),
            ("120:00:00,000", 432_000_000),
        ],
    )
    def test_from_srt_valid(self, raw: str, expected_ms: int) -> None:
        assert Timecode.from_srt(raw) == Timecode(expected_ms)

    @pytest.mark.parametrize(
        "raw",
        [
            "00:60:00,000",
            "00:99:99,000",
            "00:00:60,000",
            "00:00:00.000",
            "1:02:03,456",
            "-00:00:01,000",
            "not-a-timecode",
        ],
    )
    def test_from_srt_rejects_invalid_format_or_range(self, raw: str) -> None:
        with pytest.raises(ValueError):
            Timecode.from_srt(raw)

    def test_shifted_clamps_at_zero(self) -> None:
        tc = Timecode(1500)
        assert tc.shifted(-5000) == Timecode(0)
        assert tc.shifted(500) == Timecode(2000)


class TestSubtitleCue:
    @pytest.mark.parametrize("invalid_index", [0, -1, -10])
    def test_rejects_invalid_index(self, invalid_index: int) -> None:
        with pytest.raises(ValueError, match="index"):
            SubtitleCue(invalid_index, Timecode(0), Timecode(1000), "Hola")

    @pytest.mark.parametrize(
        ("start_ms", "end_ms"),
        [
            (5000, 2000),  # end < start
            (3000, 3000),  # end == start (duración 0 ms)
        ],
    )
    def test_rejects_non_positive_duration(self, start_ms: int, end_ms: int) -> None:
        with pytest.raises(ValueError, match="must be after start"):
            SubtitleCue(1, Timecode(start_ms), Timecode(end_ms), "Hola")

    def test_clean_char_count_strips_html_and_crlf_but_keeps_math(self) -> None:
        cue_html = SubtitleCue(
            1,
            Timecode(0),
            Timecode(2000),
            '<i>Hola</i>\r\n<font color="#fff">Mundo</font>',
        )
        assert cue_html.clean_char_count == len("HolaMundo")

        cue_math = SubtitleCue(
            2,
            Timecode(0),
            Timecode(2000),
            "2 < 5 y 8 > 3",
        )
        assert cue_math.clean_char_count == len("2 < 5 y 8 > 3")

    def test_duration_and_cps(self) -> None:
        cue = SubtitleCue(1, Timecode(1000), Timecode(3000), "Hola mundo")
        assert cue.duration_ms == 2000
        assert cue.cps == pytest.approx(5.0)


class TestModelsProperties:
    @given(ms=st.integers(min_value=0, max_value=1_000_000_000))
    def test_timecode_srt_roundtrip(self, ms: int) -> None:
        tc = Timecode(ms)
        assert Timecode.from_srt(tc.to_srt()) == tc

    @given(
        ms=st.integers(min_value=0, max_value=1_000_000_000),
        offset=st.integers(min_value=-1_000_000_000, max_value=1_000_000_000),
    )
    def test_timecode_shifted_never_negative(self, ms: int, offset: int) -> None:
        shifted = Timecode(ms).shifted(offset)
        assert shifted.total_ms == max(0, ms + offset)
        assert shifted.total_ms >= 0

    @given(
        start_ms=st.integers(min_value=0, max_value=100_000_000),
        duration_ms=st.integers(min_value=1, max_value=600_000),
        text=st.text(max_size=200),
    )
    def test_subtitle_cue_invariants(self, start_ms: int, duration_ms: int, text: str) -> None:
        cue = SubtitleCue(
            index=1,
            start=Timecode(start_ms),
            end=Timecode(start_ms + duration_ms),
            text=text,
        )
        assert cue.duration_ms == duration_ms
        assert 0 <= cue.clean_char_count <= len(text)
        assert cue.cps >= 0.0
