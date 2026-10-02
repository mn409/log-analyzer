import subprocess
import sys
from pathlib import Path

import pytest

from loganalyzer.cli import main

ROOT = Path(__file__).resolve().parent.parent
APP_LOG = str(ROOT / "sample_logs" / "app.log")
SMALL_LOG = str(ROOT / "sample_logs" / "clean_small.log")


def test_runs_on_sample_log_and_exits_cleanly(capsys):
    exit_code = main([APP_LOG])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Log Analysis Report" in output
    assert "Connection timeout to db-<N>" in output


def test_missing_file_gives_friendly_error(capsys):
    exit_code = main(["does_not_exist.log"])

    error_text = capsys.readouterr().err
    assert exit_code == 1
    assert "file not found" in error_text


def test_output_flag_writes_report_to_file(tmp_path, capsys):
    report_path = tmp_path / "report.txt"

    exit_code = main([SMALL_LOG, "--output", str(report_path)])

    assert exit_code == 0
    assert "Log Analysis Report" in report_path.read_text()


def test_level_flag_changes_the_report(capsys):
    main([SMALL_LOG, "--level", "warn"])

    output = capsys.readouterr().out
    assert "Top 1 WARN message" in output


def test_invalid_window_is_rejected():
    with pytest.raises(SystemExit) as error:
        main([SMALL_LOG, "--window", "0"])

    assert error.value.code == 2


def test_module_entry_point_works():
    # Runs the exact command from the README in a real subprocess.
    result = subprocess.run(
        [sys.executable, "-m", "loganalyzer.cli", APP_LOG],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0
    assert "Busiest 5 minute window" in result.stdout
