# Log Analyzer

A small command line tool written in Python that reads an application log file and tells you which errors are repeating, when they started, and whether there was a burst of errors in any short period of time.

## The problem it solves

When something breaks in production, the first questions are always the same. Which error keeps coming up? When did it start? Did it get worse suddenly, or has it been slowly building?

Answering that by scrolling through thousands of log lines is slow and easy to get wrong. This tool does that first pass for you. Point it at a log file and within a second you get the top repeating failures, how many times each one happened, when each one first and last appeared, and any time window where errors jumped well above normal.

## Features

- Reads a plain text log file given as a command line argument
- Counts total lines and lines per level (DEBUG, INFO, WARN, ERROR)
- Skips malformed lines without crashing and reports how many were skipped
- Groups similar errors together by replacing numbers, IP addresses and IDs with placeholders, so "timeout to db-01" and "timeout to db-02" count as the same problem
- Shows the top N errors with count, first seen and last seen
- Groups errors into time windows (5 minutes by default, configurable)
- Finds the busiest window and warns about spikes
- Can analyse a different level instead of ERROR (for example WARN)
- Can save the report to a text file
- Uses only the Python standard library (pytest is needed only to run the tests)

## Project structure

```
log-analyzer/
  loganalyzer/
    __init__.py        marks the folder as a Python package
    parser.py          turns one log line into a record, skips bad lines
    analyzer.py        counting, grouping, message normalization, spike detection
    report.py          formats the analysis into readable text
    cli.py             argparse entry point that ties everything together
  sample_logs/
    app.log            about 75 realistic lines with one clear error spike
    with_bad_lines.log small file containing malformed lines
    clean_small.log    tiny file that is easy to check by hand
  tests/
    test_parser.py     tests for line parsing and bad input
    test_analyzer.py   tests for counting, grouping, windows and spikes
    test_report.py     tests for the report text
    test_cli.py        tests for the command line behaviour
  pytest.ini           tells pytest where to find the package
  requirements.txt     pytest only
  README.md
  .gitignore
```

## Install and run

You need Python 3.10 or newer.

```bash
# 1. Get the code and move into the folder
cd log-analyzer

# 2. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

# 3. Install pytest (only needed for the tests)
pip install -r requirements.txt

# 4. Run the tool from the project folder
python -m loganalyzer.cli sample_logs/app.log --window 5 --top 5 --output report.txt
```

### Options

| Option | Default | What it does |
| --- | --- | --- |
| `logfile` | required | Path to the log file |
| `--window` | 5 | Size of each time window in minutes |
| `--top` | 5 | How many top messages to show |
| `--spike-threshold` | 2.0 | A window is a spike when its count is above this many times the average per window |
| `--level` | ERROR | Which level to analyse: DEBUG, INFO, WARN or ERROR |
| `--output` | none | Also write the report to this file |

If the log file does not exist, the tool prints a short error message and exits with code 1.

## Example run

```bash
python -m loganalyzer.cli sample_logs/app.log
```

```
Log Analysis Report
===================
Total lines: 75
0 lines skipped

Level counts
  DEBUG : 3
  INFO  : 44
  WARN  : 9
  ERROR : 19

Top 5 ERROR messages
  1. [PaymentService] Connection timeout to db-<N>
     count: 8 | first seen: 2025-01-15 10:13:58 | last seen: 2025-01-15 10:25:40
  2. [PaymentService] Failed to process payment for order <N>
     count: 4 | first seen: 2025-01-15 10:21:33 | last seen: 2025-01-15 10:27:22
  3. [AuthService] Invalid token for user <N>
     count: 3 | first seen: 2025-01-15 10:03:47 | last seen: 2025-01-15 10:38:09
  4. [NotificationService] SMTP connection refused to <IP>:<N>
     count: 2 | first seen: 2025-01-15 10:08:21 | last seen: 2025-01-15 10:33:02
  5. [OrderService] Order <N> not found
     count: 2 | first seen: 2025-01-15 10:10:50 | last seen: 2025-01-15 10:22:41

Busiest 5 minute window: 2025-01-15 10:20 to 2025-01-15 10:25 (10 ERROR lines)

Spike warnings (more than 4.75 ERROR lines in a window, average is 2.38)
  WARNING: 2025-01-15 10:20 to 2025-01-15 10:25 had 10 ERROR lines
```

A file with bad lines reports them instead of failing:

```bash
python -m loganalyzer.cli sample_logs/with_bad_lines.log
```

```
Log Analysis Report
===================
Total lines: 11
5 lines skipped
...
```

## How it helps with root-cause analysis

Using the example above:

- The top error is a database connection timeout from the payment service. That points at the database connection as the likely cause, not the payment code.
- That error was first seen at 10:13:58, a full six minutes before the spike. The earliest warning sign is often the best clue about what changed.
- The spike warning narrows the incident to 10:20 to 10:25, so you know exactly which part of the log to read in detail.
- The "Failed to process payment" errors start only after the timeouts, which suggests they are a symptom and not the cause.

The tool does not find the root cause by itself. It shows you where to look first.

## How it works in short

1. `cli.py` opens the file and reads it line by line.
2. `parser.py` turns each line into a record or marks it as skipped.
3. `analyzer.py` counts levels, groups errors, builds time windows and finds spikes.
4. `report.py` formats the result as text.
5. `cli.py` prints it and optionally saves it.

Some choices worth knowing about:

- **Error type** is the component name plus the normalized message. Numbers become `<N>`, IP addresses become `<IP>`, and UUIDs or long hex strings become `<ID>`.
- **Spike** means a window whose count is greater than the average count per window multiplied by `--spike-threshold`. The average is taken over windows that contain at least one line of the analysed level.
- **Windows** are lined up from midnight, so 5 minute windows start at :00, :05, :10 and so on.
- **Blank lines** are ignored. They are not counted as lines and not counted as skipped.
- **Lines with an unknown level or no component** count as malformed and are skipped.
- **Total lines** means every non-blank line, including the skipped ones.
- **Level counts** always cover the whole file. `--level` only changes which level is used for the top messages, windows and spikes.

## Running the tests

```bash
python -m pytest
```

or, with more detail:

```bash
python -m pytest -v
```

The tests use the files in `sample_logs/` and a few small inline strings.

## Limitations

- Only one log format is supported: `YYYY-MM-DD HH:MM:SS LEVEL [Component] message`
- It analyses a finished file. There is no real-time tailing.
- Timestamps are treated as plain local times, with no time zone handling.
- Multi-line entries such as stack traces are not joined. Continuation lines are counted as skipped.
- Records are kept in memory, so very large files will use a lot of RAM.
- Message normalization is based on simple patterns and will not catch every kind of ID.

## Possible future improvements

- Stream the file and keep only running counts, so memory use stays small on huge logs
- Support more than one log format, or a configurable pattern
- Join stack trace lines to the error above them
- Filter by component or by a time range
- Export to JSON or CSV
- Tail a live file and alert when a spike starts
