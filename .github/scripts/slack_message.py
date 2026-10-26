#!/usr/bin/env python3
"""Compose the Slack message of one failed "Scraper Tests" job.

    python3 .github/scripts/slack_message.py --repo owner/name --run-id <id> --sha <commit> --dir <scraper dir> \
        --test <test function> --pytest-log <scraper dir>/pytest.log >> "$GITHUB_OUTPUT"

Prints two step outputs for the Slack step of .github/workflows/test_scrapers.yaml:
- text      Slack mrkdwn: the scraper linked to this job's log (opened at the failed step, at pytest's FAILED line),
            the test linked to its function in test.py, and how the test did on the previous nights (history.json of
            the ci-status branch); on a second line pytest's error
- fallback  the first line as plain text (Slack shows it in notifications)

Every lookup has a fallback, so a message is sent even when the job list, the log or the history cannot be read.
"""
import argparse
import json
import re
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Lines GitHub prints at the top of the "Run test" step's log before pytest's own output: "Run cd <dir>" (the group
# header), the 3 lines of the step's script, "shell:", "env:", the 3 variables (pythonLocation and LD_LIBRARY_PATH
# from setup-python, SCRAPFLY_KEY) and "##[endgroup]". Update it when that step or its env changes.
STEP_HEADER_LINES = 10
SUMMARY = re.compile(r"^(FAILED|ERROR) \S")  # pytest's "short test summary info" lines (not "ERROR    logger:...")
ERROR_LENGTH = 200  # characters of the error shown in the message


def read_lines(log: Path) -> list:
    try:
        return log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def failed_line(log: Path) -> int:
    """1-based line of pytest's first FAILED/ERROR summary line in its output, 0 when there is none"""
    lines = read_lines(log)
    # captured log output above the summary can start with "ERROR" too
    start = next((n for n, line in enumerate(lines, 1) if "short test summary info" in line), 0)
    return next((n for n, line in enumerate(lines, 1) if n > start and SUMMARY.match(line)), 0)


def error_text(log: Path) -> str:
    """the error of pytest's FAILED line ("" without one); for a schema check the fields that failed instead of the
    start of the item"""
    lines = read_lines(log)
    n = failed_line(log)
    if not n:
        return ""
    error = lines[n - 1].split(" - ", 1)[1] if " - " in lines[n - 1] else ""
    if error.startswith("Failed: Validation failed"):
        fields = next((m.group(1) for m in map(re.compile(r"^E\s+Errors: (.+)").match, lines) if m), None)
        error = f"Validation failed: {fields}" if fields else error
    return error if len(error) <= ERROR_LENGTH else error[: ERROR_LENGTH - 1] + "…"


def mrkdwn(text: str) -> str:
    """plain text safe inside a Slack code span"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "'")


def job_url(repo: str, run_id: int, scraper: str, test: str, pytest_log: Path) -> str:
    """this job's log page (matrix jobs are named "test (<dir>, <test>)"), opened at its failed step and, when that
    step is the test run, at pytest's FAILED line; the run when the job cannot be found"""
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100", "--paginate", "--jq", ".jobs[]"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        for line in out.splitlines():
            job = json.loads(line)
            if job["name"] != f"test ({scraper}, {test})":
                continue
            failed = [s for s in job.get("steps", []) if s.get("conclusion") == "failure"]
            if not failed:
                return job["html_url"]
            url = f"{job['html_url']}#step:{failed[0]['number']}"
            n = failed_line(pytest_log) if failed[0].get("name") == "Run test" else 0
            return f"{url}:{STEP_HEADER_LINES + n}" if n else url
    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
        pass
    return f"https://github.com/{repo}/actions/runs/{run_id}"


def test_url(repo: str, sha: str, scraper: str, test: str) -> str:
    """the test function in test.py at the commit that ran (the file without an anchor when the line is not found)"""
    url = f"https://github.com/{repo}/blob/{sha}/{scraper}/test.py"
    try:
        for number, line in enumerate(ROOT.joinpath(scraper, "test.py").read_text(encoding="utf-8").splitlines(), 1):
            if re.match(rf"^(async )?def {re.escape(test)}\(", line):
                return f"{url}#L{number}"
    except OSError:
        pass
    return url


def previous_nights(repo: str, run_id: int, scraper: str, test: str) -> str:
    """how the test did on the previous nights, from history.json on the ci-status branch ("" without a history)"""
    try:
        url = f"https://raw.githubusercontent.com/{repo}/ci-status/history.json"
        with urllib.request.urlopen(url, timeout=15) as r:
            history = json.load(r)
    except (OSError, ValueError):
        return ""
    # the status job writes tonight's result after the test jobs, so the entries end with the previous night
    entries = [e for e in history.get(f"{scraper}/{test}", []) if e.get("run") != run_id]
    if not entries:
        return ""
    streak = 0  # nights in a row without a pass, counted from the last one
    for entry in reversed(entries):
        if entry.get("conclusion") == "success":
            break
        streak += 1
    if streak == 0:
        last = entries[-1].get("date", "?")
        last_night = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()  # the runs start at 00:00 UTC
        return "passed last night" if last == last_night else f"passed on {last}"
    last_pass = next((e.get("date", "?") for e in reversed(entries) if e.get("conclusion") == "success"), None)
    text = f"also failed the last {streak} night{'s' if streak != 1 else ''}"
    return text + (f" (last pass {last_pass})" if last_pass else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="owner/name of the repository the run belongs to")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--sha", required=True, help="the commit the run tested")
    parser.add_argument("--dir", required=True, help="the scraper directory of the matrix job, e.g. ebay-scraper")
    parser.add_argument("--test", required=True, help="the test function of the matrix job")
    parser.add_argument("--pytest-log", type=Path, required=True, help="pytest's output, saved by the Run test step")
    args = parser.parse_args()

    log = job_url(args.repo, args.run_id, args.dir, args.test, args.pytest_log)
    code = test_url(args.repo, args.sha, args.dir, args.test)
    nights = previous_nights(args.repo, args.run_id, args.dir, args.test)
    tail = f"  -  {nights}" if nights else ""
    error = error_text(args.pytest_log)
    text = f":red_circle: <{log}|{args.dir}> › <{code}|{args.test}>{tail}" + (f"\n`{mrkdwn(error)}`" if error else "")
    print(f"text<<SLACK_TEXT_END\n{text}\nSLACK_TEXT_END")  # GITHUB_OUTPUT's form for a value of several lines
    print(f"fallback={args.dir} › {args.test}{tail}")


if __name__ == "__main__":
    main()
