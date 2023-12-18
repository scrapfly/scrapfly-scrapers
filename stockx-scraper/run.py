"""
This example run script shows how to run the StockX.com scraper defined in ./stockx.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import stockx

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    stockx.BASE_CONFIG["cache"] = True

    print("running StockX scrape and saving results to ./results directory")

    product = await stockx.scrape_product("https://stockx.com/nike-x-stussy-bucket-hat-black")
    with open(output.joinpath("product.json"), "w", encoding="utf-8") as file:
        json.dump(product, file, indent=2, ensure_ascii=False)

    search = await stockx.scrape_search("https://stockx.com/search?s=nike", max_pages=2)
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search, file, indent=2, ensure_ascii=False)   


if __name__ == "__main__":
    asyncio.run(run())
