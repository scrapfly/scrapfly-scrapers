"""
This example run script shows how to run the Google Flights scraper defined in ./google_flights.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import google_flights

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

TODAY = datetime.now().strftime('%Y-%m-%d')
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')


async def run():
    google_flights.BASE_CONFIG["cache"] = True
    google_flights.BASE_CONFIG["debug"] = True

    print("running Google Flights scrape and saving results to ./results directory")

    roundtrip = await google_flights.scrape_flights(
        origin="JFK",
        destination="CDG",
        depart=TODAY,
        ret=WEEK_FROM_NOW,
        currency="USD", 
    )
    with open(output / "roundtrip.json", "w", encoding="utf-8") as f:
        json.dump(roundtrip, f, indent=2, ensure_ascii=False)

    oneway = await google_flights.scrape_flights(
        origin="JFK",
        destination="LHR",
        depart=TODAY,
        currency="USD",
    )
    with open(output / "oneway.json", "w", encoding="utf-8") as f:
        json.dump(oneway, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
