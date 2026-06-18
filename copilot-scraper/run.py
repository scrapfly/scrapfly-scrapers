"""
This example run script shows how to run the copilot.microsoft.com scraper defined in ./copilot.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
from pathlib import Path
import copilot

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def run():
    print("running Copilot scrape and saving results to ./results directory")

    result = copilot.scrape_copilot(
        query="what is the best web scraping tool for 2026? list the top 10 tools",
        mode="search",
    )

    with open(output / "copilot.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    run()
