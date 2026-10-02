"""Command line entry point. Connects the parser, analyzer and report.

Example:
    python -m loganalyzer.cli sample_logs/app.log --window 5 --top 5
"""

import argparse
import sys

from loganalyzer.analyzer import analyze
from loganalyzer.parser import VALID_LEVELS, parse_lines
from loganalyzer.report import build_report


def build_arg_parser():
    """Describe the command line options."""
    parser = argparse.ArgumentParser(
        prog="loganalyzer",
        description="Summarise an application log: top errors, counts and spikes.",
    )
    parser.add_argument("logfile", help="path to the log file to analyse")
    parser.add_argument(
        "--window", type=int, default=5,
        help="size of each time window in minutes (default: 5)",
    )
    parser.add_argument(
        "--top", type=int, default=5,
        help="how many top messages to show (default: 5)",
    )
    parser.add_argument(
        "--spike-threshold", type=float, default=2.0,
        help="a window is a spike when its count is above this many times "
             "the average per window (default: 2.0)",
    )
    parser.add_argument(
        "--level", type=str.upper, choices=VALID_LEVELS, default="ERROR",
        help="which level to analyse (default: ERROR)",
    )
    parser.add_argument(
        "--output", help="also write the report to this text file",
    )
    return parser


def main(argv=None):
    """Run the tool. Returns the exit code (0 means success)."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Reject values that make no sense. parser.error prints a usage message and exits.
    if args.window < 1:
        parser.error("--window must be at least 1 minute")
    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.spike_threshold <= 0:
        parser.error("--spike-threshold must be greater than 0")

    # Read the file one line at a time. errors="replace" stops odd bytes from crashing us.
    try:
        with open(args.logfile, "r", encoding="utf-8", errors="replace") as log_file:
            records, skipped = parse_lines(log_file)
    except FileNotFoundError:
        print(f"Error: file not found: {args.logfile}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Error: could not read {args.logfile}: {error.strerror}", file=sys.stderr)
        return 1

    analysis = analyze(
        records,
        skipped_lines=skipped,
        window_minutes=args.window,
        top_n=args.top,
        level=args.level,
        spike_multiplier=args.spike_threshold,
    )
    report = build_report(analysis)
    print(report)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as out_file:
                out_file.write(report + "\n")
        except OSError as error:
            print(f"Error: could not write {args.output}: {error.strerror}", file=sys.stderr)
            return 1
        print(f"\nReport written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
