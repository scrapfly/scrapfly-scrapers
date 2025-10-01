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
    # aliexpress.BASE_CONFIG["cache"] = True # session can't be combined with cache
    aliexpress.BASE_CONFIG["debug"] = True

    print("running Aliexpress scrape and saving results to ./results directory")
    # note: aliexpress search has a bug where wholsepages show no results without `SearchText` parameter for some reason
    url = "https://www.aliexpress.com/w/wholesale-drills.html?catId=0&SearchText=drills"
    search_results = await aliexpress.scrape_search(url, max_pages=2)
    output.joinpath("search.json", ).write_text(json.dumps(search_results, indent=2, ensure_ascii=False), encoding="utf-8")

    url = "https://www.aliexpress.com/item/2255800741121659.html"
    product_results = await aliexpress.scrape_product(url)
    output.joinpath("product.json").write_text(json.dumps(product_results, indent=2, ensure_ascii=False), encoding="utf-8")

    review_results = await aliexpress.scrape_product_reviews("1005006717259012", max_scrape_pages=3)
    output.joinpath("reviews.json").write_text(json.dumps(review_results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run())
