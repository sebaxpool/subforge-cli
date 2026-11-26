from pathlib import Path

import pytest

from subforge import __version__
from subforge.cli import main

VALID_SRT = (
    "1\n"
    "00:00:01,000 --> 00:00:04,000\n"
    "Primera línea\n"
    "Segunda línea\n\n"
    "2\n"
    "00:00:05,000 --> 00:00:08,000\n"
    "Todo bien por acá.\n"
)


class TestCliHappyPath:
    def test_default_output_processes_and_shifts_cues(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "movie.srt"
        src.write_text(VALID_SRT, encoding="utf-8")

        exit_code = main([str(src), "--shift-ms", "500"])
        captured = capsys.readouterr()

        expected_out = tmp_path / "movie.forged.srt"
        assert exit_code == 0
        assert expected_out.exists()
        assert f"Wrote 2 cues to {expected_out}" in captured.out

        result = expected_out.read_text(encoding="utf-8")
        assert "00:00:01,500 --> 00:00:04,500" in result
        assert "Primera línea Segunda línea" in result

    def test_custom_output_and_no_reflow_preserves_line_breaks(
        self, tmp_path: Path
    ) -> None:
        src = tmp_path / "input.srt"
        dst = tmp_path / "custom.srt"
        src.write_text(VALID_SRT, encoding="utf-8")

        exit_code = main([str(src), "-o", str(dst), "--no-reflow"])

        assert exit_code == 0
        result = dst.read_text(encoding="utf-8")
        assert "Primera línea\nSegunda línea" in result

    def test_audit_only_returns_zero_when_clean(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "clean.srt"
        src.write_text(VALID_SRT, encoding="utf-8")

        exit_code = main([str(src), "--audit-only"])
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "OK: 2 cues checked, no readability issues found." in captured.out
        assert not (tmp_path / "clean.forged.srt").exists()

    def test_audit_only_returns_two_when_issues_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "fast.srt"
        src.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\n"
            "Esta línea es demasiado rápida para leerse en un solo segundo.\n",
            encoding="utf-8",
        )

        exit_code = main([str(src), "--audit-only", "--max-cps", "20", "--max-width", "42"])
        captured = capsys.readouterr()

        assert exit_code == 2
        assert "[Cue #1]" in captured.out
        assert "CPS" in captured.out
        assert "Line width" in captured.out

    def test_handles_utf8_bom_by_default_and_cp1252_with_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bom_file = tmp_path / "bom.srt"
        bom_file.write_bytes(VALID_SRT.encode("utf-8-sig"))
        assert main([str(bom_file), "--audit-only"]) == 0

        legacy_file = tmp_path / "legacy.srt"
        legacy_file.write_bytes(
            "1\n00:00:01,000 --> 00:00:04,000\n¡Mañana será un gran día!\n".encode("cp1252")
        )

        # Falla limpiamente con UTF-8 por defecto y sugiere --encoding
        assert main([str(legacy_file), "--audit-only"]) == 1
        err = capsys.readouterr().err
        assert "--encoding" in err

        # Funciona al indicar --encoding cp1252
        out_file = tmp_path / "legacy_utf8.srt"
        assert main([str(legacy_file), "--encoding", "cp1252", "-o", str(out_file)]) == 0
        assert "¡Mañana será un gran día!" in out_file.read_text(encoding="utf-8")

    def test_version_flag_prints_package_version(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert f"subforge {__version__}" in capsys.readouterr().out


class TestCliErrors:
    def test_missing_file_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "nope.srt"
        assert main([str(missing)]) == 1
        assert "not found" in capsys.readouterr().err

    def test_directory_as_input_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([str(tmp_path)]) == 1
        assert "is not a file" in capsys.readouterr().err

    def test_unknown_encoding_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "sample.srt"
        src.write_text(VALID_SRT, encoding="utf-8")

        assert main([str(src), "--encoding", "fake-encoding-xyz"]) == 1
        assert "Unknown text encoding" in capsys.readouterr().err

    def test_malformed_srt_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad = tmp_path / "broken.srt"
        bad.write_text("Esto definitivamente no es un archivo SRT\n", encoding="utf-8")

        assert main([str(bad)]) == 1
        assert "Invalid SRT content" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "extra_args",
        [
            ["--max-width", "0"],
            ["--audit-only", "--max-width", "0"],
            ["--audit-only", "--max-cps", "-5"],
        ],
    )
    def test_invalid_numeric_flags_return_one(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        extra_args: list[str],
    ) -> None:
        src = tmp_path / "sample.srt"
        src.write_text(VALID_SRT, encoding="utf-8")

        assert main([str(src), *extra_args]) == 1
        assert "Error:" in capsys.readouterr().err

    def test_unwritable_output_path_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "sample.srt"
        src.write_text(VALID_SRT, encoding="utf-8")
        impossible_out = tmp_path / "no_existe_esta_carpeta" / "out.srt"

        assert main([str(src), "-o", str(impossible_out)]) == 1
        assert "Could not write" in capsys.readouterr().err
