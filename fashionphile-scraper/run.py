"""
This example run script shows how to run the fashionphile.com scraper defined in ./fashionphile.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import fashionphile

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    fashionphile.BASE_CONFIG["cache"] = True

    print("running Fashionphile scrape and saving results to ./results directory")

    products_data = await fashionphile.scrape_products(
        urls=[
            "https://www.fashionphile.com/p/bottega-veneta-nappa-twisted-padded-intrecciato-curve-slide-sandals-36-black-1048096",
            "https://www.fashionphile.com/p/louis-vuitton-ostrich-lizard-majestueux-tote-mm-navy-1247825",
            "https://www.fashionphile.com/p/louis-vuitton-monogram-multicolor-lodge-gm-black-1242632",
        ]
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)

    search_data = await fashionphile.scrape_search(
        url="https://www.fashionphile.com/shop/discounted/all", max_pages=3
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
