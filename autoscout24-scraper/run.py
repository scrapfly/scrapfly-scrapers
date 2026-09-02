"""
This example run script shows how to run the AutoScout24.com scraper defined in ./autoscout24.py
It scrapes car listings and car details and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import autoscout24
from loguru import logger as log

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)
autoscout24.BASE_CONFIG["cache"] = False


async def run():

    log.info("running AutoScout24 scrape and saving results to ./results directory")

    # car listings from category page
    url = "https://www.autoscout24.com/lst/c/compact"
    listings = await autoscout24.scrape_listings(url, max_pages=3)
    output.joinpath("listings.json").write_text(json.dumps(listings, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # car detail pages, taken from the listings above because offers expire
    urls = [
        "https://www.autoscout24.com" + listing["url"]
        for listing in listings
        if listing.get("url")
    ][:3]
    
    car_details = await autoscout24.scrape_car_details(urls)
    output.joinpath("car_details.json").write_text(json.dumps(car_details, indent=2, ensure_ascii=False), encoding="utf-8")
    log.success(f"scraped {len(car_details)} car details")

if __name__ == "__main__":
    asyncio.run(run())

