from datetime import datetime
from pathlib import Path

from loganalyzer.analyzer import analyze, normalize_message, window_start
from loganalyzer.parser import parse_lines

SAMPLES = Path(__file__).resolve().parent.parent / "sample_logs"


def analyze_file(name, **options):
    """Parse a sample log file and analyze it."""
    with open(SAMPLES / name) as log_file:
        records, skipped = parse_lines(log_file)
    return analyze(records, skipped, **options)


def analyze_lines(lines, **options):
    """Parse a list of inline log lines and analyze them."""
    records, skipped = parse_lines(lines)
    return analyze(records, skipped, **options)


def error_lines(minute, how_many):
    """Make how_many ERROR lines that all fall inside 10:<minute>."""
    return [
        f"2025-01-15 10:{minute:02d}:{second:02d} ERROR [App] Something broke"
        for second in range(how_many)
    ]


def test_level_counts():
    result = analyze_file("clean_small.log")

    assert result.total_lines == 8
    assert result.level_counts == {"DEBUG": 1, "INFO": 3, "WARN": 1, "ERROR": 3}


def test_normalization_groups_similar_messages():
    assert normalize_message("Connection timeout to db-01") == "Connection timeout to db-<N>"
    assert normalize_message("Connection timeout to db-01") == normalize_message("Connection timeout to db-02")
    assert normalize_message("Refused by 10.0.4.17:25") == "Refused by <IP>:<N>"
    assert normalize_message("Job 3f2a9c1b7d failed") == "Job <ID> failed"


def test_similar_errors_end_up_in_one_group():
    result = analyze_file("clean_small.log")

    top = result.top_errors[0]
    assert top.component == "PaymentService"
    assert top.message == "Connection timeout to db-<N>"
    assert top.count == 2
    assert top.first_seen == datetime(2025, 1, 15, 12, 1, 10)
    assert top.last_seen == datetime(2025, 1, 15, 12, 3, 30)


def test_window_start_rounds_down():
    time = datetime(2025, 1, 15, 10, 23, 45)

    assert window_start(time, 5) == datetime(2025, 1, 15, 10, 20, 0)
    assert window_start(time, 10) == datetime(2025, 1, 15, 10, 20, 0)
    assert window_start(time, 15) == datetime(2025, 1, 15, 10, 15, 0)


def test_errors_are_grouped_by_window():
    result = analyze_file("clean_small.log", window_minutes=5)

    # Two errors in 12:00-12:05, one in 12:05-12:10
    assert result.window_counts[datetime(2025, 1, 15, 12, 0)] == 2
    assert result.window_counts[datetime(2025, 1, 15, 12, 5)] == 1
    assert result.busiest_window == (datetime(2025, 1, 15, 12, 0), 2)


def test_spike_is_detected():
    # Window counts are 1, 1, 1 and 10. Average 3.25, limit 6.5, so 10 is a spike.
    lines = error_lines(0, 1) + error_lines(5, 1) + error_lines(10, 1) + error_lines(15, 10)

    result = analyze_lines(lines)

    assert result.spikes == [(datetime(2025, 1, 15, 10, 15), 10)]


def test_no_spike_when_errors_are_evenly_spread():
    lines = error_lines(0, 3) + error_lines(5, 3) + error_lines(10, 3) + error_lines(15, 3)

    result = analyze_lines(lines)

    assert result.spikes == []


def test_spike_in_sample_app_log():
    result = analyze_file("app.log")

    assert result.spikes == [(datetime(2025, 1, 15, 10, 20), 10)]
    assert result.busiest_window == (datetime(2025, 1, 15, 10, 20), 10)


def test_empty_file():
    result = analyze_lines([])

    assert result.total_lines == 0
    assert result.top_errors == []
    assert result.busiest_window is None
    assert result.spikes == []


def test_level_option_changes_what_is_analysed():
    result = analyze_file("clean_small.log", level="WARN")

    assert result.level == "WARN"
    assert len(result.top_errors) == 1
    assert result.top_errors[0].component == "Cache"
