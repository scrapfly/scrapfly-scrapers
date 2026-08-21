"""
This example run script shows how to run the loopnet.com scraper defined in ./loopnet.py
It scrapes data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import loopnet

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    loopnet.BASE_CONFIG["cache"] = True
    loopnet.BASE_CONFIG["debug"] = True

    print("running LoopNet scrape and saving results to ./results directory")

    listings = await loopnet.scrape_listings(
        urls=[
            "https://www.loopnet.com/Listing/611-W-Oglethorpe-Ave-Savannah-GA/39001150/",
            "https://www.loopnet.com/Listing/1410-Dean-Forest-Rd-Savannah-GA/41166496/",
        ]
    )
    with open(output / "listings.json", "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)

    search_results = await loopnet.scrape_search(
        search_url="https://www.loopnet.com/search/commercial-real-estate/savannah-ga/for-sale/", max_pages=2
    )
    with open(output / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
