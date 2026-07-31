"""
This example run script shows how to run the App Store scraper defined in ./app_store.py
It scrapes app metadata and reviews and saves them to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path

import app_store

DEMO_APP_ID = "6448311069"
DEMO_COUNTRY = "us"

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    app_store.BASE_CONFIG["cache"] = True
    app_store.BASE_CONFIG["debug"] = True

    print("running App Store scrape and saving results to ./results directory")

    metadata = await app_store.scrape_app_metadata(DEMO_APP_ID, DEMO_COUNTRY)
    with open(output / "app_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    reviews = await app_store.scrape_reviews(DEMO_APP_ID, DEMO_COUNTRY, max_pages=1)
    with open(output / "reviews.json", "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
