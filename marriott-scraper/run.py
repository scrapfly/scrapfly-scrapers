"""
This example run script shows how to run the marriott.com scraper defined in ./marriott.py
It scrapes search and hotel data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import marriott

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


async def run():
    print("running Marriott scrape and saving results to ./results directory")

    search_results = await marriott.scrape_search(
        city="New York, NY, USA",
        from_date=TODAY,
        to_date=WEEK_FROM_NOW,
    )
    output.joinpath("search.json").write_text(
        json.dumps(search_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    property_ids = [p["marriott_id"] for p in search_results[:3]]
    hotel_results = await marriott.scrape_hotels(property_ids)
    output.joinpath("hotel.json").write_text(
        json.dumps(hotel_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(run())
