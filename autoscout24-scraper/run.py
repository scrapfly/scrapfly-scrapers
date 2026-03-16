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
autoscout24.BASE_CONFIG["cache"] = True


async def run():

    log.info("running AutoScout24 scrape and saving results to ./results directory")

    # Scrape car listings from category page
    url = "https://www.autoscout24.com/lst/c/compact"
    listings = await autoscout24.scrape_listings(url, max_pages=3)
    output.joinpath("listings.json").write_text(json.dumps(listings, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Scraped {len(listings)} car listings")
    
    # Scrape  car details
    log.info("Scraping car details")
    urls = [
        "https://www.autoscout24.com/offers/bmw-116-116i-gasoline-black-23ff7f14-f5df-4bbc-a12f-b8d07bf9b870",
        "https://www.autoscout24.com/offers/fiat-500-1-2-sport-pano-gasoline-red-516f93af-fbcc-4614-a69e-3369f3334ad1",
        "https://www.autoscout24.com/offers/mercedes-benz-a-160-blueefficiency-classic-gasoline-grey-527717a0-2f01-4264-b9a5-bd7a69a27993",
    ]
    
    car_details = await autoscout24.scrape_car_details(urls)
    output.joinpath("car_details.json").write_text(json.dumps(car_details, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Scraped {len(car_details)} car details")

if __name__ == "__main__":
    asyncio.run(run())

