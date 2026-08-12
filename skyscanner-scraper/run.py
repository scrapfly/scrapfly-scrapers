"""
This example run script shows how to run the skyscanner.com scraper defined in ./skyscanner.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import skyscanner

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


async def run():
    skyscanner.BASE_CONFIG["cache"] = False
    skyscanner.BASE_CONFIG["debug"] = True

    print("running Skyscanner scrape and saving results to ./results directory")

    roundtrip = await skyscanner.scrape_flights(
        origin="JFK",
        destination="LHR",
        departure_date=TODAY,
        return_date=WEEK_FROM_NOW,
    )
    with open(output / "roundtrip.json", "w", encoding="utf-8") as f:
        json.dump(roundtrip, f, indent=2, ensure_ascii=False)
    print(f"saved {roundtrip['flight_count']} flights to results/roundtrip.json")

    oneway = await skyscanner.scrape_flights(
        origin="JFK",
        destination="CDG",
        departure_date=TODAY,
    )
    with open(output / "oneway.json", "w", encoding="utf-8") as f:
        json.dump(oneway, f, indent=2, ensure_ascii=False)
    print(f"saved {oneway['flight_count']} flights to results/oneway.json")


if __name__ == "__main__":
    asyncio.run(run())
