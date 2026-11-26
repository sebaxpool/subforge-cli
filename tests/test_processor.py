import pytest
from hypothesis import given, strategies as st

from subforge.models import SubtitleCue, Timecode
from subforge.processor import (
    AuditIssue,
    audit_readability,
    balance_lines,
    process_cues,
)


class TestBalanceLines:
    @pytest.mark.parametrize("raw", ["", "   \n\t  "])
    def test_empty_or_whitespace_returns_empty(self, raw: str) -> None:
        assert balance_lines(raw) == ""

    def test_short_text_collapses_whitespace_into_single_line(self) -> None:
        assert balance_lines("  Hola   \n  mundo  ", max_width=42) == "Hola mundo"

    def test_single_long_word_is_not_split(self) -> None:
        word = "supercalifragilisticoespialidoso"
        assert balance_lines(word, max_width=10) == word

    def test_balances_two_lines_within_max_width(self) -> None:
        raw = (
            "This subtitle line is definitely longer than "
            "forty two characters in total."
        )
        lines = balance_lines(raw, max_width=42).splitlines()
        assert len(lines) == 2
        assert all(len(line) <= 42 for line in lines)

    def test_wraps_very_long_text_into_multiple_lines(self) -> None:
        raw = (
            "Esta es una frase sumamente extensa pensada para superar con creces "
            "el doble del ancho maximo permitido en un subtitulo estandar."
        )
        lines = balance_lines(raw, max_width=42).splitlines()
        assert len(lines) >= 3
        assert all(len(line) <= 42 for line in lines)
        assert " ".join(lines) == " ".join(raw.split())

    def test_preserves_dialogue_turns_with_hyphens(self) -> None:
        dialogue = "- Hola.\n- ¿Cómo estás?"
        assert balance_lines(dialogue, max_width=42) == "- Hola.\n- ¿Cómo estás?"

        multiline_dialogue = "- Hola,\n¿todo bien por allá?\n- Todo excelente."
        assert (
            balance_lines(multiline_dialogue, max_width=42)
            == "- Hola, ¿todo bien por allá?\n- Todo excelente."
        )

    @pytest.mark.parametrize("invalid_width", [0, -1, -42])
    def test_rejects_invalid_max_width(self, invalid_width: int) -> None:
        with pytest.raises(ValueError, match="max_width"):
            balance_lines("Hola mundo", max_width=invalid_width)


class TestProcessCues:
    def test_positive_shift_and_reflow_toggle(self) -> None:
        cue = SubtitleCue(
            index=5,
            start=Timecode(1000),
            end=Timecode(3000),
            text="Primera línea\nSegunda línea",
        )
        shifted_reflow = process_cues([cue], shift_ms=500, max_width=42, reflow=True)
        assert shifted_reflow == [
            SubtitleCue(
                index=1,
                start=Timecode(1500),
                end=Timecode(3500),
                text="Primera línea Segunda línea",
            )
        ]

        shifted_raw = process_cues([cue], shift_ms=500, max_width=42, reflow=False)
        assert shifted_raw[0].text == "Primera línea\nSegunda línea"

    def test_negative_shift_drops_past_cues_clamps_partial_and_reindexes(self) -> None:
        cues = [
            SubtitleCue(1, Timecode(1000), Timecode(4000), "Se descarta"),
            SubtitleCue(2, Timecode(4000), Timecode(5000), "Límite exacto"),
            SubtitleCue(3, Timecode(4000), Timecode(8000), "Se recorta al inicio"),
            SubtitleCue(4, Timecode(9000), Timecode(12000), "Intacto"),
        ]
        result = process_cues(cues, shift_ms=-5000, reflow=False)
        assert result == [
            SubtitleCue(1, Timecode(0), Timecode(3000), "Se recorta al inicio"),
            SubtitleCue(2, Timecode(4000), Timecode(7000), "Intacto"),
        ]

    def test_empty_input_returns_empty_list(self) -> None:
        assert process_cues([], shift_ms=1000) == []

    @pytest.mark.parametrize("invalid_width", [0, -10])
    def test_rejects_invalid_max_width(self, invalid_width: int) -> None:
        with pytest.raises(ValueError, match="max_width"):
            process_cues([], max_width=invalid_width)


class TestAuditReadability:
    def test_clean_cue_reports_no_issues(self) -> None:
        cue = SubtitleCue(1, Timecode(0), Timecode(3000), "Hola mundo.")
        assert audit_readability([cue], max_cps=20.0, max_width=42) == []

    def test_ignores_html_tags_for_line_length_and_cps(self) -> None:
        cue = SubtitleCue(
            1,
            Timecode(0),
            Timecode(3000),
            '<font color="#ffff00"><i>Hola mundo, todo bien.</i></font>',
        )
        assert audit_readability([cue], max_cps=20.0, max_width=42) == []

    def test_detects_cps_width_and_combined_issues(self) -> None:
        fast_and_wide = SubtitleCue(
            index=3,
            start=Timecode(0),
            end=Timecode(1000),
            text="An extremely fast line spoken in just one second.",
        )
        issues = audit_readability([fast_and_wide], max_cps=20.0, max_width=42)
        assert len(issues) == 1
        issue = issues[0]
        assert isinstance(issue, AuditIssue)
        assert issue.cue_index == 3
        assert issue.line_length == len(fast_and_wide.text)
        assert issue.cps == pytest.approx(49.0)
        assert "CPS 49.00 exceeds limit 20.00" in issue.reason
        assert "Line width 49 exceeds 42 chars" in issue.reason

    def test_cps_rounding_avoids_contradictory_boundary_message(self) -> None:
        # 200 / 9.998 = 20.004... -> redondea a 20.00 (no supera 20.00)
        at_limit = SubtitleCue(1, Timecode(0), Timecode(9998), "a" * 200)
        assert audit_readability([at_limit], max_cps=20.0, max_width=300) == []

        # 200 / 9.995 = 20.010... -> redondea a 20.01 (sí supera 20.00)
        above_limit = SubtitleCue(2, Timecode(0), Timecode(9995), "a" * 200)
        issues = audit_readability([above_limit], max_cps=20.0, max_width=300)
        assert len(issues) == 1
        assert "CPS 20.01 exceeds limit 20.00" in issues[0].reason

    @pytest.mark.parametrize("invalid_cps", [0.0, -5.0])
    def test_rejects_invalid_max_cps(self, invalid_cps: float) -> None:
        with pytest.raises(ValueError, match="max_cps"):
            audit_readability([], max_cps=invalid_cps)

    @pytest.mark.parametrize("invalid_width", [0, -1])
    def test_rejects_invalid_max_width(self, invalid_width: int) -> None:
        with pytest.raises(ValueError, match="max_width"):
            audit_readability([], max_width=invalid_width)


_word = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
    min_size=1,
    max_size=12,
)

_cue_strategy = st.builds(
    lambda start_ms, duration_ms, text: SubtitleCue(
        index=1,
        start=Timecode(start_ms),
        end=Timecode(start_ms + duration_ms),
        text=text,
    ),
    start_ms=st.integers(min_value=0, max_value=100_000),
    duration_ms=st.integers(min_value=1, max_value=10_000),
    text=st.lists(_word, min_size=1, max_size=10).map(" ".join),
)


class TestProcessorProperties:
    @given(
        words=st.lists(_word, min_size=1, max_size=25),
        max_width=st.integers(min_value=12, max_value=60),
    )
    def test_balance_lines_preserves_words_and_respects_width(
        self, words: list[str], max_width: int
    ) -> None:
        raw = " ".join(words)
        balanced = balance_lines(raw, max_width=max_width)
        assert balanced.split() == words
        assert all(len(line) <= max_width for line in balanced.splitlines())

    @given(
        cues=st.lists(_cue_strategy, max_size=15),
        shift_ms=st.integers(min_value=-120_000, max_value=120_000),
        max_width=st.integers(min_value=12, max_value=60),
    )
    def test_process_cues_invariants(
        self, cues: list[SubtitleCue], shift_ms: int, max_width: int
    ) -> None:
        processed = process_cues(cues, shift_ms=shift_ms, max_width=max_width)
        expected_count = sum(1 for c in cues if c.end.total_ms + shift_ms > 0)
        assert len(processed) == expected_count
        assert [c.index for c in processed] == list(range(1, expected_count + 1))
        for cue in processed:
            assert cue.start.total_ms >= 0
            assert cue.end > cue.start
