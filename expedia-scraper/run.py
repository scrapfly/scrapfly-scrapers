"""
This example run script shows how to run the expedia.com scraper defined in ./expedia.py
It scrapes hotel search results and saves them to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import expedia

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


async def run():
    expedia.BASE_CONFIG["debug"] = True
    print("running Expedia scrape and saving results to ./results directory")

    hotels = await expedia.scrape_hotel_search(
        destination="New York",
        check_in=TODAY,
        check_out=WEEK_FROM_NOW,
        max_pages=3,
    )
    output.joinpath("hotels.json").write_text(
        json.dumps(hotels, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"saved {len(hotels)} hotels to results/hotels.json")


    flight_results = await expedia.scrape_flight_search(
        origin="JFK",
        destination="LAX",
        departure_date=TODAY,
        return_date=WEEK_FROM_NOW,
    )
    output.joinpath("flights.json").write_text(
        json.dumps(flight_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

if __name__ == "__main__":
    asyncio.run(run())
