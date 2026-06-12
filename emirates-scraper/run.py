"""
This example run script shows how to run the emirates.com scraper defined in ./emirates.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import emirates

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


async def run():
    emirates.BASE_CONFIG["cache"] = False
    emirates.BASE_CONFIG["debug"] = True

    print("running Emirates scrape and saving results to ./results directory")

    result = await emirates.scrape_flights(
        origin="JFK",
        destination="DXB",
        departure_date=TODAY,
        return_date=WEEK_FROM_NOW,
        locale="us/english",
    )
    with open(output / "roundtrip.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"saved {len(result['flights'])} flight offers to results/roundtrip.json")
    
    result = await emirates.scrape_flights(
        origin="JFK",
        destination="DXB",
        departure_date=TODAY,
        locale="us/english",
    )
    with open(output / "oneway.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"saved {len(result['flights'])} flight offers to results/oneway.json")


if __name__ == "__main__":
    asyncio.run(run())
