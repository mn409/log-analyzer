"""Counting, grouping, message normalization and spike detection."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from loganalyzer.parser import VALID_LEVELS

# Patterns used to turn variable parts of a message into placeholders.
# The order matters: UUIDs first, then IPs, then long hex ids, then plain numbers.
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
IP_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
# 8 or more hex characters with at least one digit, like "8f3a9c21b7"
HEX_ID_PATTERN = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{8,}\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\d+")

# Windows are lined up from this fixed starting point (midnight).
EPOCH = datetime(2000, 1, 1)


@dataclass
class ErrorGroup:
    """All log lines that share the same component and normalized message."""

    component: str
    message: str  # the normalized message
    count: int
    first_seen: datetime
    last_seen: datetime


@dataclass
class Analysis:
    """Everything the report needs, in one place."""

    total_lines: int
    skipped_lines: int
    level_counts: dict
    level: str              # the level that was analysed (ERROR by default)
    window_minutes: int
    top_errors: list        # list of ErrorGroup, most frequent first
    window_counts: dict     # window start time -> number of lines
    busiest_window: tuple   # (window start, count) or None
    average_per_window: float
    spike_limit: float
    spikes: list            # list of (window start, count)


def normalize_message(message):
    """Replace the changing parts of a message with placeholders.

    "Connection timeout to db-01"   ->  "Connection timeout to db-<N>"
    "Refused by 10.0.4.17:25"       ->  "Refused by <IP>:<N>"
    """
    message = UUID_PATTERN.sub("<ID>", message)
    message = IP_PATTERN.sub("<IP>", message)
    message = HEX_ID_PATTERN.sub("<ID>", message)
    message = NUMBER_PATTERN.sub("<N>", message)
    return message


def count_levels(records):
    """Count how many records there are for each level."""
    counts = {level: 0 for level in VALID_LEVELS}
    for record in records:
        counts[record.level] += 1
    return counts


def group_by_type(records, level):
    """Group records of one level by (component, normalized message).

    Returns a list of ErrorGroup, most frequent first. Ties go to whichever
    appeared earlier.
    """
    groups = {}

    for record in records:
        if record.level != level:
            continue

        key = (record.component, normalize_message(record.message))

        if key not in groups:
            groups[key] = ErrorGroup(
                component=record.component,
                message=key[1],
                count=1,
                first_seen=record.timestamp,
                last_seen=record.timestamp,
            )
        else:
            group = groups[key]
            group.count += 1
            group.first_seen = min(group.first_seen, record.timestamp)
            group.last_seen = max(group.last_seen, record.timestamp)

    return sorted(groups.values(), key=lambda g: (-g.count, g.first_seen))


def window_start(timestamp, window_minutes):
    """Round a timestamp down to the start of its time window.

    With 5 minute windows, 10:23:45 belongs to the window starting at 10:20:00.
    """
    window_seconds = window_minutes * 60
    seconds = int((timestamp - EPOCH).total_seconds())
    rounded = seconds - (seconds % window_seconds)
    return EPOCH + timedelta(seconds=rounded)


def count_by_window(records, level, window_minutes):
    """Count records of one level in each time window.

    Only windows that contain at least one such record appear in the result.
    """
    counts = {}
    for record in records:
        if record.level != level:
            continue
        start = window_start(record.timestamp, window_minutes)
        counts[start] = counts.get(start, 0) + 1
    return counts


def find_spikes(window_counts, multiplier):
    """Find windows with more lines than (average * multiplier).

    Returns (average, limit, spikes) where spikes is a list of
    (window start, count) sorted by time.
    """
    if not window_counts:
        return 0.0, 0.0, []

    average = sum(window_counts.values()) / len(window_counts)
    limit = average * multiplier
    spikes = [
        (start, count)
        for start, count in sorted(window_counts.items())
        if count > limit
    ]
    return average, limit, spikes


def analyze(records, skipped_lines=0, window_minutes=5, top_n=5,
            level="ERROR", spike_multiplier=2.0):
    """Run every step of the analysis and return an Analysis object."""
    window_counts = count_by_window(records, level, window_minutes)
    average, limit, spikes = find_spikes(window_counts, spike_multiplier)

    # Busiest window: highest count. Items are sorted by time, and max() keeps
    # the first one it finds, so a tie goes to the earlier window.
    busiest = None
    if window_counts:
        busiest = max(sorted(window_counts.items()), key=lambda item: item[1])

    return Analysis(
        total_lines=len(records) + skipped_lines,
        skipped_lines=skipped_lines,
        level_counts=count_levels(records),
        level=level,
        window_minutes=window_minutes,
        top_errors=group_by_type(records, level)[:top_n],
        window_counts=window_counts,
        busiest_window=busiest,
        average_per_window=average,
        spike_limit=limit,
        spikes=spikes,
    )
