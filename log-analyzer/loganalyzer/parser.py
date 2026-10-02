"""Turns raw log lines into structured records.

A valid line looks like this:
    2025-01-15 10:23:45 ERROR [PaymentService] Connection timeout to db-01
"""

import re
from dataclasses import dataclass
from datetime import datetime

# The levels we know about. A line with any other level counts as a bad line.
VALID_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")

# Splits a line into four parts: timestamp, level, [component], message.
LINE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "  # timestamp
    r"([A-Za-z]+) "                              # level
    r"\[([^\]]+)\] "                             # component in square brackets
    r"(.+)$"                                     # the rest is the message
)


@dataclass
class LogRecord:
    """One successfully parsed log line."""

    timestamp: datetime
    level: str
    component: str
    message: str


def parse_line(line):
    """Parse a single line. Returns a LogRecord, or None if the line is bad."""
    match = LINE_PATTERN.match(line.strip())
    if match is None:
        return None

    timestamp_text, level, component, message = match.groups()

    level = level.upper()
    if level not in VALID_LEVELS:
        return None

    # The pattern only checks the shape of the date. This checks it is a real one
    # (for example it rejects month 13).
    try:
        timestamp = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    return LogRecord(timestamp, level, component, message)


def parse_lines(lines):
    """Parse many lines.

    Returns (records, skipped_count). Blank lines are ignored completely.
    Bad lines are skipped and counted, they never raise an error.
    """
    records = []
    skipped = 0

    for line in lines:
        if not line.strip():
            continue  # blank line, nothing to parse or report

        record = parse_line(line)
        if record is None:
            skipped += 1
        else:
            records.append(record)

    return records, skipped
