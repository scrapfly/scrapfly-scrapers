"""
This example run script shows how to run the goat.com scraper defined in ./goat.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import goat

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    goat.BASE_CONFIG["cache"] = True

    print("running Goat scrape and saving results to ./results directory")

    products_data = await goat.scrape_products(
        urls=[
            "https://www.goat.com/sneakers/air-jordan-3-retro-white-cement-reimagined-dn3707-100",
            "https://www.goat.com/sneakers/travis-scott-x-air-jordan-1-retro-high-og-cd4487-100",
            "https://www.goat.com/sneakers/travis-scott-x-wmns-air-jordan-1-low-og-olive-dz4137-106",
        ]
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)

    search_data = await goat.scrape_search("pumar dark", max_pages=3)
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
