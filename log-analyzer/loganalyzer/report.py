"""Turns an Analysis into plain text. No analysis happens here."""

from datetime import timedelta

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
WINDOW_FORMAT = "%Y-%m-%d %H:%M"


def format_window(start, window_minutes):
    """Show a window as 'start to end'."""
    end = start + timedelta(minutes=window_minutes)
    return f"{start.strftime(WINDOW_FORMAT)} to {end.strftime(WINDOW_FORMAT)}"


def build_report(analysis):
    """Build the full summary and return it as one string."""
    level = analysis.level
    lines = []

    lines.append("Log Analysis Report")
    lines.append("===================")
    lines.append(f"Total lines: {analysis.total_lines}")

    noun = "line" if analysis.skipped_lines == 1 else "lines"
    lines.append(f"{analysis.skipped_lines} {noun} skipped")

    lines.append("")
    lines.append("Level counts")
    for name, count in analysis.level_counts.items():
        lines.append(f"  {name:<5} : {count}")

    lines.append("")
    if not analysis.top_errors:
        lines.append(f"Top {level} messages")
        lines.append(f"  No {level} lines found.")
    else:
        shown = len(analysis.top_errors)
        word = "message" if shown == 1 else "messages"
        lines.append(f"Top {shown} {level} {word}")
        for number, group in enumerate(analysis.top_errors, start=1):
            lines.append(f"  {number}. [{group.component}] {group.message}")
            lines.append(
                f"     count: {group.count} | "
                f"first seen: {group.first_seen.strftime(TIME_FORMAT)} | "
                f"last seen: {group.last_seen.strftime(TIME_FORMAT)}"
            )

    lines.append("")
    if analysis.busiest_window is None:
        lines.append("Busiest window: none")
    else:
        start, count = analysis.busiest_window
        lines.append(
            f"Busiest {analysis.window_minutes} minute window: "
            f"{format_window(start, analysis.window_minutes)} ({count} {level} lines)"
        )

    lines.append("")
    if analysis.spikes:
        lines.append(
            f"Spike warnings (more than {analysis.spike_limit:.2f} {level} lines "
            f"in a window, average is {analysis.average_per_window:.2f})"
        )
        for start, count in analysis.spikes:
            lines.append(
                f"  WARNING: {format_window(start, analysis.window_minutes)} "
                f"had {count} {level} lines"
            )
    else:
        lines.append("Spike warnings: none detected")

    return "\n".join(lines)
