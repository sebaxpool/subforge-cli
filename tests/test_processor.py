import unittest
from subforge.models import SubtitleCue, Timecode
from subforge.processor import audit_readability, balance_lines

class TestSubForgeProcessor(unittest.TestCase):
    def test_timecode_roundtrip_and_shift(self) -> None:
        tc = Timecode.from_srt("00:01:15,250")
        self.assertEqual(tc.shifted(-300).to_srt(), "00:01:14,950")

    def test_balanced_line_wrapping(self) -> None:
        raw = "This subtitle line is definitely longer than forty two characters in total."
        lines = balance_lines(raw, max_width=42).splitlines()
        self.assertEqual(len(lines), 2)

    def test_cps_audit_detection(self) -> None:
        fast_cue = SubtitleCue(index=1, start=Timecode(0), end=Timecode(1000), text="An extremely fast line spoken in one second.")
        self.assertEqual(len(audit_readability([fast_cue], max_cps=20.0)), 1)

if __name__ == "__main__":
    unittest.main()
