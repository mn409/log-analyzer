from pathlib import Path

from loganalyzer.analyzer import analyze
from loganalyzer.parser import parse_lines
from loganalyzer.report import build_report

SAMPLES = Path(__file__).resolve().parent.parent / "sample_logs"


def report_for(name):
    with open(SAMPLES / name) as log_file:
        records, skipped = parse_lines(log_file)
    return build_report(analyze(records, skipped))


def test_report_contains_top_errors():
    report = report_for("clean_small.log")

    assert "[PaymentService] Connection timeout to db-<N>" in report
    assert "count: 2" in report
    assert "first seen: 2025-01-15 12:01:10" in report


def test_report_contains_skipped_lines_count():
    report = report_for("with_bad_lines.log")

    assert "5 lines skipped" in report


def test_report_shows_spike_warning():
    report = report_for("app.log")

    assert "WARNING: 2025-01-15 10:20 to 2025-01-15 10:25 had 10 ERROR lines" in report


def test_report_says_when_there_is_no_spike():
    report = report_for("clean_small.log")

    assert "Spike warnings: none detected" in report
