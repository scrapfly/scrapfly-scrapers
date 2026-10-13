#!/usr/bin/env python3
"""Build the test matrix of the "Scraper Tests" workflow from the repository.

Every `test_*` function in every `*-scraper/test.py` becomes one matrix entry (one CI job per test),
unless the scraper or the test is listed in .github/test_matrix_exclude.txt.

    python3 .github/scripts/test_matrix.py                              # include=[...] for $GITHUB_OUTPUT
    python3 .github/scripts/test_matrix.py --scrapers airbnb,expedia    # only these scrapers
    python3 .github/scripts/test_matrix.py --tests test_search_scraping # only these test functions
    python3 .github/scripts/test_matrix.py --list                       # one "<dir> <test>" per line
"""
import argparse
import ast
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_FILE = ROOT / ".github" / "test_matrix_exclude.txt"


def excluded() -> set:
    """lines of the exclude file: "<dir>" (whole scraper) or "<dir>/<test>", comments start with #"""
    lines = EXCLUDE_FILE.read_text().splitlines() if EXCLUDE_FILE.exists() else []
    return {line.split("#")[0].strip() for line in lines if line.split("#")[0].strip()}


def discover() -> list:
    """(project_dir, test) for every test function, sorted; a test.py that does not parse fails the build"""
    entries = []
    for test_file in sorted(ROOT.glob("*-scraper/test.py")):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # e.g. "\d" in a regex string is only a warning
            tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                entries.append((test_file.parent.name, node.name))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scrapers", default="", help="comma-separated, with or without the -scraper suffix")
    parser.add_argument("--tests", default="", help="comma-separated test function names")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    scrapers = {s.strip().removesuffix("-scraper") for s in args.scrapers.split(",") if s.strip()}
    tests = {t.strip() for t in args.tests.split(",") if t.strip()}
    skip = excluded()
    matrix = [
        {"project_dir": project_dir, "test": test}
        for project_dir, test in discover()
        if project_dir not in skip
        and f"{project_dir}/{test}" not in skip
        and (not scrapers or project_dir.removesuffix("-scraper") in scrapers)
        and (not tests or test in tests)
    ]
    if not matrix:
        sys.exit("test_matrix.py: no test selected")
    if args.list:
        print("\n".join(f"{m['project_dir']} {m['test']}" for m in matrix))
    else:
        print("include=" + json.dumps(matrix, separators=(",", ":")))


if __name__ == "__main__":
    main()
