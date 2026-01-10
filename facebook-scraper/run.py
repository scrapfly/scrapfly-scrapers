"""
This example run script shows how to run the Facebook.com scraper defined in ./facebook.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import facebook

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

facebook.BASE_CONFIG["cache"] = False


async def run():

    print("running Facebook scrape and saving results to ./results directory")

    # Scrape Marketplace
    marketplace_data = await facebook.scrape_marketplace_listings(
        location="New York, NY",
    )
    with open(output.joinpath("marketplace.json"), "w", encoding="utf-8") as file:
        json.dump(marketplace_data, file, indent=2, ensure_ascii=False)

    # Scrape Events
    events_data = await facebook.scrape_facebook_events(location="New York, NY")
    with open(output.joinpath("events.json"), "w", encoding="utf-8") as file:
        json.dump(events_data, file, indent=2, ensure_ascii=False)

    print("Scraping completed! Check ./results directory for output files")


if __name__ == "__main__":
    asyncio.run(run())
