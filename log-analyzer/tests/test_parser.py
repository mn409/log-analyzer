from pathlib import Path

from loganalyzer.parser import parse_line, parse_lines

SAMPLES = Path(__file__).resolve().parent.parent / "sample_logs"


def test_valid_line_is_parsed():
    record = parse_line("2025-01-15 10:23:45 ERROR [PaymentService] Connection timeout to db-01")

    assert record is not None
    assert record.timestamp.year == 2025
    assert record.timestamp.minute == 23
    assert record.level == "ERROR"
    assert record.component == "PaymentService"
    assert record.message == "Connection timeout to db-01"


def test_malformed_line_returns_none():
    assert parse_line("this is not a log line") is None


def test_missing_component_returns_none():
    assert parse_line("2025-01-15 10:23:45 ERROR Connection timeout") is None


def test_unknown_level_returns_none():
    assert parse_line("2025-01-15 10:23:45 FATAL [App] Something odd") is None


def test_impossible_date_returns_none():
    assert parse_line("2025-13-45 10:23:45 INFO [App] Bad date") is None


def test_parse_lines_skips_bad_lines_and_ignores_blank_ones():
    lines = [
        "2025-01-15 10:00:00 INFO [App] Started",
        "garbage",
        "",
        "2025-01-15 10:01:00 ERROR [App] Boom",
    ]

    records, skipped = parse_lines(lines)

    assert len(records) == 2
    assert skipped == 1


def test_bad_lines_sample_file():
    with open(SAMPLES / "with_bad_lines.log") as log_file:
        records, skipped = parse_lines(log_file)

    assert len(records) == 6
    assert skipped == 5
