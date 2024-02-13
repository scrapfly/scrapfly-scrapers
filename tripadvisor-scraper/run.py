"""
This example run script shows how to run the tripadvisor scraper defined in ./tripadvisor.py
It scrapes hotel data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import tripadvisor

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    tripadvisor.BASE_CONFIG["cache"] = False

    print("running Tripadvisor scrape and saving results to ./results directory")
    result_location = await tripadvisor.scrape_location_data(query="Malta")
    output.joinpath("location.json").write_text(json.dumps(result_location, indent=2, ensure_ascii=False))

    result_search = await tripadvisor.scrape_search(query="Malta", max_pages=2)
    output.joinpath("search.json").write_text(json.dumps(result_search, indent=2, ensure_ascii=False))

    result_hotel = await tripadvisor.scrape_hotel(
        "https://www.tripadvisor.com/Hotel_Review-g190327-d264936-Reviews-1926_Hotel_Spa-Sliema_Island_of_Malta.html",
        max_review_pages=3,
    )
    output.joinpath("hotels.json").write_text(json.dumps(result_hotel, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run())
