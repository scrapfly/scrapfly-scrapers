"""
This example run script shows how to run the Amazon.com scraper defined in ./amazon.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import amazon

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    amazon.BASE_CONFIG["cache"] = True
    amazon.BASE_CONFIG["country"] = "US"

    print("running Amazon scrape and saving results to ./results directory")

    url = "https://www.amazon.com/s?k=kindle"
    search = await amazon.scrape_search(url, max_pages=2)
    output.joinpath("search.json").write_text(json.dumps(search, indent=2, ensure_ascii=False), encoding="utf-8")

    url = "https://www.amazon.com/PlayStation-5-Console-CFI-1215A01X/dp/B0BCNKKZ91/"
    product = await amazon.scrape_product(url)
    output.joinpath("product.json").write_text(json.dumps(product, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run())
