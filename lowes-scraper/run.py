"""
This example run script shows how to run the lowes.com scraper defined in ./lowes.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
from pathlib import Path
import lowes

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

PRODUCT_URLS = [
    "https://www.lowes.com/pd/DEWALT-20-volt-Max-Brushless-Drill-1-Battery-Included-Charger-Included-and-Soft-Bag-included/5014148635",
    "https://www.lowes.com/pd/CRAFTSMAN-V20-20-volt-Max-1-2-in-Cordless-Drill-1-Battery-Included-and-Charger-Included/5004861567",
]


async def run():
    lowes.BASE_CONFIG["debug"] = True
    lowes.BASE_CONFIG["cache"] = True

    print("running Lowes scrape and saving results to ./results directory")

    products = await lowes.scrape_products(urls=PRODUCT_URLS)
    with open(output / "products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    search_results = await lowes.scrape_search(query="cordless drill", max_pages=2)
    with open(output / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_results, f, indent=2, ensure_ascii=False)
        
    
    store_locations = await lowes.scrape_store_locations(zip_code="28202")
    with open(output / "store_locations.json", "w", encoding="utf-8") as f:
        json.dump(store_locations, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
