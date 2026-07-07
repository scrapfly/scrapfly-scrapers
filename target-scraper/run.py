"""
This example run script shows how to run the Target.com scraper defined in ./target.py
It scrapes product data and saves it to ./results/

To run this script set the env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import asyncio
import json
from pathlib import Path
import target

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


async def run():
    
    print("running Target scrape and saving results to ./results directory")

    # scrape a single product detail page by URL
    product_data = await target.scrape_product(
        "https://www.target.com/p/women-s-lace-godet-tank-top-wild-fable/-/A-95213693"
    )
    with open(output.joinpath("product.json"), "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)

    # # scrape availability/fulfillment for a set of TCINs at a given store and zip
    availability_data = await target.scrape_availability(
        tcins=["89231676"],
        store_id="1771",
        zip_code="52404",
    )
    with open(output.joinpath("availability.json"), "w", encoding="utf-8") as file:
        json.dump(availability_data, file, indent=2, ensure_ascii=False)
        
    # scrape store location URLs from the Target store sitemap
    store_locations_data = await target.scrape_store_locations_sitemap(
        url="https://www.target.com/sl/sitemap_0001.xml.gz",
    )
    with open(output.joinpath("store_locations.json"), "w", encoding="utf-8") as file:
        json.dump(store_locations_data, file, indent=2, ensure_ascii=False)

    # scrape store location details by store ID
    store_data = await target.scrape_store_locations(
        store_ids=["3", "4", "5"],
    )
    with open(output.joinpath("stores.json"), "w", encoding="utf-8") as file:
        json.dump(store_data, file, indent=2, ensure_ascii=False)

    # scrape search results for a keyword (returns TCINs and listing metadata)
    search_data = await target.scrape_search(
        keyword="laptop",
        max_pages=3,
    )
    with open(output.joinpath("search.json"), "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(run())
