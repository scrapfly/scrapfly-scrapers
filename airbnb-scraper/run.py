"""
This example run script shows how to run the airbnb.com scraper defined in ./airbnb.py
It scrapes search and listing data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
from scrapfly import ScrapeConfig

import airbnb

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEK_FROM_NOW = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


async def run():
    print("running Airbnb scrape and saving results to ./results directory")

    search_results = await airbnb.scrape_listings(
        query="Panama City Beach, Florida",
        check_in=TODAY,
        check_out=WEEK_FROM_NOW,
        adults=1,
        max_pages=3,
    )
    output.joinpath("search.json").write_text(
        json.dumps(search_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    urls = [item["url"] for item in search_results if item.get("url")][:3]
    property_results = await airbnb.scrape_properties(urls=urls)
    output.joinpath("property.json").write_text(
        json.dumps(property_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(run())
