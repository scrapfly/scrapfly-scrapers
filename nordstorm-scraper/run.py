"""
This example run script shows how to run the nordstorm.com scraper defined in ./nordstorm.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import nordstorm

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache
    nordstorm.BASE_CONFIG["cache"] = True

    print("running Normstorm scrape and saving results to ./results directory")

    products_data = await nordstorm.scrape_products(
        urls=[
            "https://www.nordstrom.com/s/nike-air-max-90-sneaker-men/6549520",
            "https://www.nordstrom.com/s/hank-kent-performance-twill-dress-shirt-regular-big/7783670",
            "https://www.nordstrom.com/s/bp-fleece-hoodie/7786657",
        ]
    )
    with open(output.joinpath("products.json"), "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)

    search_data = await nordstorm.scrape_search(
        url="https://www.nordstrom.com/sr?origin=keywordsearch&keyword=indigo", max_pages=2
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
