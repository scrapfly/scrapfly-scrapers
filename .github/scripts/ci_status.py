#!/usr/bin/env python3
"""Write the per-scraper status files of one "Scraper Tests" run for the ci-status branch.

    python3 .github/scripts/ci_status.py --repo owner/name --run-id <id> --out <checkout of the ci-status branch>

Reads the run's jobs through `gh api` (GH_TOKEN) and writes, in --out:
- badges/<scraper dir>.svg    one badge image per scraper, embedded by the README status column:
                              "passing" (every test of the scraper passed), "failing", "N/M passing", or
                              "not run" for a scraper that has no job in the run. Self-contained, no third party.
- status.json                 every test job of the run with its conclusion, plus the run id and date.
- history.json                the last 60 results of every test (older entries are dropped).
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOB_NAME = re.compile(r"^test \((?P<dir>[^,]+), (?P<test>[^)]+)\)$")
KEEP = 60
COLORS = {"brightgreen": "#4c1", "red": "#e05d44", "orange": "#fe7d37", "lightgrey": "#9f9f9f"}


def run_jobs(repo: str, run_id: int) -> list:
    out = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100",
            "--paginate",
            "--jq",
            ".jobs[] | {name, conclusion}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    jobs = []
    for line in out.splitlines():
        job = json.loads(line)
        match = JOB_NAME.match(job["name"])
        if match:
            jobs.append({"dir": match["dir"], "test": match["test"], "conclusion": job["conclusion"]})
    return jobs


def status(results: list) -> tuple:
    """(message, color) of a scraper from the conclusions of its test jobs"""
    if not results:
        return "not run", "lightgrey"
    passed = sum(1 for r in results if r == "success")
    if passed == len(results):
        return "passing", "brightgreen"
    if passed == 0:
        return "failing", "red"
    return f"{passed}/{len(results)} passing", "orange"


def badge_svg(label: str, message: str, color: str) -> str:
    """a flat two-part badge in the usual shields.io style (11px Verdana, widths estimated per character)"""
    lw, mw = int(len(label) * 6.5) + 10, int(len(message) * 6.5) + 10
    w = lw + mw
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="{label}: {message}">'
        f"<title>{label}: {message}</title>"
        '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#555"/>'
        f'<rect x="{lw}" width="{mw}" height="20" fill="{COLORS[color]}"/>'
        f'<rect width="{w}" height="20" fill="url(#s)"/></g>'
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{lw / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>'
        f'<text x="{lw / 2}" y="14">{label}</text>'
        f'<text x="{lw + mw / 2}" y="15" fill="#010101" fill-opacity=".3">{message}</text>'
        f'<text x="{lw + mw / 2}" y="14">{message}</text>'
        "</g></svg>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    jobs = run_jobs(args.repo, args.run_id)
    if not jobs:
        raise SystemExit("ci_status.py: the run has no test jobs")
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scrapers = sorted(p.name for p in ROOT.glob("*-scraper") if (p / "test.py").exists())

    badges = args.out / "badges"
    badges.mkdir(parents=True, exist_ok=True)
    for old in badges.iterdir():  # the directory is owned by this script: no stale files from earlier runs
        old.unlink()
    for scraper in scrapers:
        message, color = status([j["conclusion"] for j in jobs if j["dir"] == scraper])
        (badges / f"{scraper}.svg").write_text(badge_svg(scraper.removesuffix("-scraper"), message, color))

    (args.out / "status.json").write_text(
        json.dumps(
            {"run": args.run_id, "date": date, "tests": sorted(jobs, key=lambda j: (j["dir"], j["test"]))}, indent=1
        )
        + "\n"
    )

    history_file = args.out / "history.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else {}
    for job in jobs:
        entries = history.setdefault(f"{job['dir']}/{job['test']}", [])
        entries.append({"date": date, "run": args.run_id, "conclusion": job["conclusion"]})
        del entries[:-KEEP]
    history_file.write_text(json.dumps(history, indent=1) + "\n")

    failed = sum(1 for j in jobs if j["conclusion"] != "success")
    print(f"{len(jobs)} test jobs, {failed} not successful; {len(scrapers)} badges written to {badges}")


if __name__ == "__main__":
    main()
