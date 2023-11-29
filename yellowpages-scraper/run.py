"""
This example run script shows how to run the yellowpages.com scraper defined in ./yellowpages.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import yellowpages

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    yellowpages.BASE_CONFIG["cache"] = False

    print("running Yellowpages scrape and saving results to ./results directory")

    search_data = await yellowpages.scrape_search(
        query="chinese restaurants", location="San Francisco, CA", max_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)

    business_data = await yellowpages.scrape_pages(
        urls=[
            "https://www.yellowpages.com/los-angeles-ca/mip/casa-bianca-pizza-pie-13519",
            "https://www.yellowpages.com/los-angeles-ca/mip/dulan-soul-food-kitchen-531675984",
            "https://www.yellowpages.com/los-angeles-ca/mip/oyabun-seafood-555210849",
        ]
    )
    with open(output.joinpath("business_pages.json"), "w", encoding="utf-8") as file:
        json.dump(business_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
