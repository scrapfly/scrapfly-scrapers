"""
This example run script shows how to run the Aliexpress.com scraper defined in ./aliexpress.py
It scrapes product data and product search and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import aliexpress

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    # enable scrapfly cache for basic use
    aliexpress.BASE_CONFIG["cache"] = True
    aliexpress.BASE_CONFIG["country"] = "US"

    print("running Aliexpress scrape and saving results to ./results directory")
    url = "https://www.aliexpress.com/wholesale?SearchText=drills"
    search_results = await aliexpress.scrape_search(url, max_pages=2)
    output.joinpath("search.json").write_text(json.dumps(search_results, indent=2))

    url = "https://www.aliexpress.com/item/4000927436411.html"
    product_results = await aliexpress.scrape_product(url)
    output.joinpath("product.json").write_text(json.dumps(product_results, indent=2))

    review_results = await aliexpress.scrape_product_reviews("120565", "4000927436411", max_pages=2)
    output.joinpath("reviews.json").write_text(json.dumps(review_results, indent=2))





if __name__ == "__main__":
    asyncio.run(run())
