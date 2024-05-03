"""
This example run script shows how to run the Walmart.com scraper defined in ./walmart.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import walmart

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    walmart.BASE_CONFIG["cache"] = False

    print("running Walmart scrape and saving results to ./results directory")

    products_data = await walmart.scrape_products(
        urls=[
            "https://www.walmart.com/ip/1736740710",
            "https://www.walmart.com/ip/715596133",
            "https://www.walmart.com/ip/496918359",
        ]
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)

    search_data = await walmart.scrape_search(
        query="laptop", sort="best_seller", max_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
